"""Explicit M1 composition and IPv4 loopback runner, never an installed service.

Startup consumes an already migrated, quiescent Task 3 SQLite file; there is no
implicit DDL, provider discovery, global environment read or profile access.
The CLI is a foundation lifecycle seam. DEP/M01/P01 installed policy is pending.
"""

import argparse
import asyncio
import json
import signal
import socket
import tomllib
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import partial
from pathlib import Path

import uvicorn
from agentmonitor.adapters.identity_access.argon2_password import Argon2PasswordV1
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqliteDatabaseHandleV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    InspectSchemaCompatibilityV1,
    RequireWritableSchemaV1,
    application_schema_range,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.api_tokens import (
    SqliteIdentityAccessApiTokenRepositoryV1,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.repository import (
    SqliteIdentityAccessRepositoryV1,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.sessions import (
    SqliteIdentityAccessSessionRepositoryV1,
)
from agentmonitor.api.app import create_application
from agentmonitor.api.v1.dependencies import IamApiPortsV1
from agentmonitor.contracts.configuration_v1 import (
    BootstrapConfigurationV1,
    ConfigurationRegistryV1,
)
from agentmonitor.contracts.foundation_v1 import BuildMetadataV1
from agentmonitor.foundation.application import (
    ApplicationLifecycleError,
    ComponentFactorySetV1,
    LifecycleHooksV1,
)
from agentmonitor.foundation.configuration import (
    BootstrapCliOptionsV1,
    BootstrapConfigurationError,
    load_bootstrap_configuration,
)
from agentmonitor.modules.identity_access.application.api_tokens import (
    CreateApiTokenV1,
    ListApiTokensV1,
    ListIamSecurityEventsV1,
    ResolveBearerTokenV1,
    RevokeApiTokenV1,
    RotateApiTokenV1,
)
from agentmonitor.modules.identity_access.application.authorization import (
    AuthorizePrincipalV1,
)
from agentmonitor.modules.identity_access.application.bootstrap import (
    GetIamInitializationStateV1,
)
from agentmonitor.modules.identity_access.application.sessions import (
    AuthenticateAdministratorV1,
    ChangeAdministratorPasswordV1,
    ListSessionsV1,
    LogoutSessionV1,
    ResolveBrowserSessionV1,
    RevokeAllSessionsV1,
    RevokeSessionV1,
    VerifyCsrfV1,
)
from fastapi import FastAPI


class LoopbackServerError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def build_metadata() -> BuildMetadataV1:
    """Read only repository build inputs, with no timestamps or local-path output."""
    manifest = Path(__file__).resolve().parents[3] / "pyproject.toml"
    with manifest.open("rb") as stream:
        version = tomllib.load(stream)["project"]["version"]
    if not isinstance(version, str):
        raise ApplicationLifecycleError("build_version_invalid")
    return BuildMetadataV1(
        version,
        None,
        None,
        "omitted_for_reproducibility",
        application_schema_range(),
        None,
        None,
        None,
        (),
    )


def _open_database(
    ref: DatabaseRefV1, build: BuildMetadataV1
) -> SqliteDatabaseHandleV1:
    view = InspectSchemaCompatibilityV1(ref, build.schema_range, "runtime_read_write")
    if view.state != "compatible":
        raise ApplicationLifecycleError("database_" + view.state)
    RequireWritableSchemaV1(view)
    return open_sqlite_database(ref, "runtime_read_write")


def create_foundation_application(
    config_path: Path, data_root: Path, *, lifecycle: LifecycleHooksV1
) -> FastAPI:
    settings = load_bootstrap_configuration(
        config_path, {}, BootstrapCliOptionsV1(ConfigurationRegistryV1(()))
    )
    build = build_metadata()
    ref = DatabaseRefV1(data_root / "agentmonitor.db", data_root)
    return create_application(
        settings,
        ComponentFactorySetV1(partial(_open_database, ref, build)),
        build,
        lifecycle,
    )


def _iam_ports(reference: DatabaseRefV1) -> IamApiPortsV1:
    bootstrap_repository = SqliteIdentityAccessRepositoryV1(reference)
    sessions_repository = SqliteIdentityAccessSessionRepositoryV1(reference)
    token_repository = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    hasher = Argon2PasswordV1()
    return IamApiPortsV1(
        GetIamInitializationStateV1(bootstrap_repository),
        AuthenticateAdministratorV1(sessions_repository, hasher),
        ResolveBrowserSessionV1(sessions_repository),
        VerifyCsrfV1(sessions_repository),
        AuthorizePrincipalV1(),
        LogoutSessionV1(sessions_repository),
        ChangeAdministratorPasswordV1(sessions_repository, hasher),
        ListSessionsV1(sessions_repository),
        RevokeSessionV1(sessions_repository),
        RevokeAllSessionsV1(sessions_repository),
        ResolveBearerTokenV1(token_repository),
        ListApiTokensV1(token_repository),
        CreateApiTokenV1(token_repository),
        RotateApiTokenV1(token_repository),
        RevokeApiTokenV1(token_repository),
        ListIamSecurityEventsV1(token_repository),
    )


def create_iam_application(
    config_path: Path, data_root: Path, *, lifecycle: LifecycleHooksV1
) -> FastAPI:
    """M2 production IAM mode over a pre-migrated real installation."""
    settings = load_bootstrap_configuration(
        config_path, {}, BootstrapCliOptionsV1(ConfigurationRegistryV1(()))
    )
    build = build_metadata()
    reference = DatabaseRefV1(data_root / "agentmonitor.db", data_root)
    return create_application(
        settings,
        ComponentFactorySetV1(partial(_open_database, reference, build)),
        build,
        lifecycle,
        iam_mode=True,
        iam_ports=_iam_ports(reference),
        service_lock_path=data_root / ".agentmonitor-service.lock",
    )


def create_iam_schema_application() -> FastAPI:
    """Same M2 route declarations, no runnable state or database side effects."""
    return create_application(
        BootstrapConfigurationV1("1.0.0", (), (), ()),
        ComponentFactorySetV1(None),
        build_metadata(),
        LifecycleHooksV1(),
        iam_mode=True,
    )


def create_schema_application() -> FastAPI:
    """Fixed build factory: same route source, no lifespan, DB or background work.

    Deliberately cannot run as a service: its absent runtime component fails
    lifespan closed. The declaration has no external config keys to load in M1.
    """
    return create_application(
        BootstrapConfigurationV1("1.0.0", (), (), ()),
        ComponentFactorySetV1(None),
        build_metadata(),
        LifecycleHooksV1(),
    )


class _OwnedServer(uvicorn.Server):
    @contextmanager
    def capture_signals(self) -> Iterator[None]:
        # The runner owns signal installation/restoration and returns safe exit
        # codes; Uvicorn must not re-raise SIGTERM after successful cleanup.
        yield


async def _serve_loopback(
    app: FastAPI,
    *,
    host: str,
    port: int,
    ready: Callable[[str], None] | None,
    stop: asyncio.Event,
) -> None:
    """Serve actual Uvicorn on a prebound IPv4 loopback socket, including port 0."""
    if host != "127.0.0.1":
        raise LoopbackServerError("bind_not_loopback")
    if type(port) is not int or not 0 <= port <= 65535:
        raise LoopbackServerError("bind_port_invalid")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    failed = False
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.setblocking(False)
    except OSError:
        failed = True
        sock.close()
    if failed:
        raise LoopbackServerError("bind_unavailable") from None
    try:
        app.state.loopback_schema_binding.address = (host, sock.getsockname()[1])
        await _run_server(app, sock=sock, ready=ready, stop=stop)
    finally:
        app.state.loopback_schema_binding.address = None
        sock.close()


async def _run_server(
    app: FastAPI,
    *,
    sock: socket.socket,
    ready: Callable[[str], None] | None,
    stop: asyncio.Event,
) -> None:
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=sock.getsockname()[1],
        loop="asyncio",
        http="h11",
        ws="none",
        lifespan="on",
        proxy_headers=False,
        forwarded_allow_ips=[],
        workers=1,
        reload=False,
        env_file=None,
        server_header=False,
        access_log=False,
        timeout_graceful_shutdown=app.state.lifecycle.hooks.shutdown_timeout_seconds,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {"discard": {"class": "logging.NullHandler"}},
            "loggers": {
                "uvicorn": {"handlers": ["discard"], "propagate": False},
                "uvicorn.error": {"handlers": ["discard"], "propagate": False},
            },
        },
    )
    server = _OwnedServer(config)

    async def drive() -> None:
        failure: str | None = None
        try:
            await server.serve(sockets=[sock])
        except SystemExit:
            failure = "startup_failed"
        except Exception:
            failure = "server_failed"
        if failure is not None:
            raise LoopbackServerError(failure) from None
        if app.state.lifecycle.failure_code:
            raise LoopbackServerError("shutdown_failed")

    task = asyncio.create_task(drive())
    cancelled = False
    try:
        while not server.started:
            if task.done():
                await task
                raise LoopbackServerError("startup_failed")
            await asyncio.sleep(0.01)
        if ready is not None:
            ready(f"http://127.0.0.1:{sock.getsockname()[1]}")
        while not stop.is_set() and not task.done():
            await asyncio.sleep(0.02)
        server.should_exit = True
        await asyncio.shield(task)
    except asyncio.CancelledError:
        cancelled = True
    finally:
        server.should_exit = True
        while not task.done():
            try:
                # Uvicorn's bounded HTTP drain and application cleanup must finish
                # before caller cancellation is propagated or the socket is closed.
                await asyncio.shield(task)
            except asyncio.CancelledError:
                cancelled = True
    # A shutdown failure takes precedence over cancellation and remains typed.
    task.result()
    if cancelled:
        raise asyncio.CancelledError


async def serve_loopback(
    app: FastAPI,
    *,
    host: str,
    port: int,
    ready: Callable[[str], None] | None,
    stop: asyncio.Event,
) -> None:
    """Typed sanitized server boundary; callbacks never expose raw failures."""
    code = "server_failed"
    try:
        await _serve_loopback(app, host=host, port=port, ready=ready, stop=stop)
        return
    except LoopbackServerError as error:
        code = error.code
    except Exception:
        pass
    raise LoopbackServerError(code) from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--foundation-contract", action="store_true", required=True)
    args = parser.parse_args()

    async def run() -> None:
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for signum in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(signum, stop.set)
        try:
            app = create_foundation_application(
                args.config,
                args.data_root,
                lifecycle=LifecycleHooksV1(foundation_contract_mode=True),
            )

            def ready(origin: str) -> None:
                print(json.dumps({"event": "ready", "origin": origin}), flush=True)

            await serve_loopback(
                app, host=args.host, port=args.port, ready=ready, stop=stop
            )
        finally:
            for signum in (signal.SIGTERM, signal.SIGINT):
                loop.remove_signal_handler(signum)

    code = "bootstrap_failed"
    try:
        asyncio.run(run(), debug=False)
        return 0
    except (
        LoopbackServerError,
        ApplicationLifecycleError,
        BootstrapConfigurationError,
    ) as error:
        code = error.code
    except Exception:
        pass
    print(json.dumps({"event": "failed", "code": code}), flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""FND-HTTP/LIFE/OAPI/CLIENT: real Uvicorn, SQLite, subprocesses and compiler.

The empty router deliberately leaves FND-CLIENT-002 Not Run. No test endpoint,
dependency override or simulated persistence/HTTP transport is used.
"""

import asyncio
import hashlib
import importlib
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend/src"))
sys.path.insert(0, str(ROOT))
FACTORY = "agentmonitor.composition.bootstrap:create_iam_schema_application"


def implementation() -> ModuleType:
    assert (ROOT / "backend/src/agentmonitor/composition/bootstrap.py").is_file(), (
        "FND-HTTP-001: production loopback application/lifecycle is absent"
    )
    return importlib.import_module("agentmonitor.composition.bootstrap")


def generator() -> ModuleType:
    assert (ROOT / "tooling/foundation/openapi_client.py").is_file(), (
        "FND-OAPI-001: production OpenAPI/client generator is absent"
    )
    return importlib.import_module("tooling.foundation.openapi_client")


@pytest.fixture
def configured_database(tmp_path: Path) -> tuple[Path, Path]:
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
    )
    from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
        migrate_to_head,
    )

    config = tmp_path / "isolated.env"
    config.write_text("")
    config.chmod(0o600)
    migrate_to_head(DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path))
    return config, tmp_path


def request(origin: str, path: str, **headers: str) -> tuple[int, bytes]:
    # Disable proxy discovery: these requests must go to the actual local socket.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(
            urllib.request.Request(origin + path, headers=headers), timeout=2
        ) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


@asynccontextmanager
async def running(app: object, *, port: int = 0) -> AsyncIterator[str]:
    bootstrap = implementation()
    stop = asyncio.Event()
    ready: asyncio.Future[str] = asyncio.get_running_loop().create_future()
    task = asyncio.create_task(
        bootstrap.serve_loopback(
            app, host="127.0.0.1", port=port, ready=ready.set_result, stop=stop
        )
    )
    try:
        finished, _ = await asyncio.wait(
            (ready, task), timeout=8, return_when=asyncio.FIRST_COMPLETED
        )
        assert finished, "FND-LIFE-001: startup exceeded its bound"
        if task in finished:
            await task
            pytest.fail("server stopped before readiness")
        yield ready.result()
    finally:
        stop.set()
        await asyncio.wait_for(task, timeout=8)


def test_real_loopback_openapi_has_unique_versioned_operations(
    configured_database: tuple[Path, Path],
) -> None:
    bootstrap = implementation()
    from agentmonitor.foundation.application import LifecycleHooksV1

    app = bootstrap.create_foundation_application(
        *configured_database,
        lifecycle=LifecycleHooksV1(foundation_contract_mode=True),
    )
    assert app.state.lifecycle.phase == "created"

    async def exercise() -> None:
        async with running(app) as origin:
            assert origin.startswith("http://127.0.0.1:")
            status, body = await asyncio.to_thread(request, origin, "/openapi.json")
            document = json.loads(body)
            ids = [
                operation["operationId"]
                for path in document["paths"].values()
                for operation in path.values()
            ]
            assert status == 200
            assert document["openapi"].startswith("3.")
            assert all(path.startswith("/api/v1") for path in document["paths"])
            assert len(ids) == len(set(ids))
            assert document["paths"] == {}
            # M1 contract mode intentionally remains empty. The canonical
            # artifact now represents the separately composed M2 IAM surface.
            assert document == {
                "openapi": "3.1.0",
                "info": {"title": "AgentMonitor", "version": "0.0.0"},
                "paths": {},
            }
            assert app.state.lifecycle.phase == "running"
            assert getattr(app.state.lifecycle, "startup_context", None) is not None, (
                "FND-LIFE-001: the root startup correlation context is absent"
            )
            for path in ("/api/v1", "/api/v1/health", "/docs", "/redoc", "/livez"):
                assert (await asyncio.to_thread(request, origin, path))[0] == 404
            assert (
                await asyncio.to_thread(
                    request, origin, "/openapi.json", Host="outside.invalid"
                )
            )[0] == 403
            assert (
                await asyncio.to_thread(
                    request, origin, "/openapi.json", Origin="https://outside.invalid"
                )
            )[0] == 403
            assert (
                await asyncio.to_thread(request, origin, "/openapi.json", Origin=origin)
            )[0] == 200
        assert app.state.lifecycle.phase == "stopped"

    before = (configured_database[1] / "agentmonitor.db").read_bytes()
    asyncio.run(exercise())
    assert (configured_database[1] / "agentmonitor.db").read_bytes() == before
    assert not (configured_database[1] / "agentmonitor.db-wal").exists()


def test_schema_transport_disabled_without_explicit_foundation_mode(
    configured_database: tuple[Path, Path],
) -> None:
    bootstrap = implementation()
    from agentmonitor.foundation.application import LifecycleHooksV1

    app = bootstrap.create_foundation_application(
        *configured_database, lifecycle=LifecycleHooksV1()
    )

    async def exercise() -> None:
        async with running(app) as origin:
            for path in ("/openapi.json", "/docs", "/redoc"):
                assert (await asyncio.to_thread(request, origin, path))[0] == 404

    asyncio.run(exercise())


def test_schema_disclosure_requires_the_approved_loopback_runner(
    configured_database: tuple[Path, Path],
) -> None:
    bootstrap = implementation()
    import uvicorn
    from agentmonitor.foundation.application import LifecycleHooksV1

    app = bootstrap.create_foundation_application(
        *configured_database,
        lifecycle=LifecycleHooksV1(foundation_contract_mode=True),
    )

    async def exercise() -> None:
        # A real alternate loopback runner proves that mode alone grants no
        # schema disclosure. Never bind wildcard/LAN, even in negative tests.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            origin = f"http://127.0.0.1:{sock.getsockname()[1]}"
            server = uvicorn.Server(
                uvicorn.Config(
                    app,
                    host="127.0.0.1",
                    log_config=None,
                    access_log=False,
                    proxy_headers=False,
                    http="h11",
                    ws="none",
                    lifespan="on",
                )
            )
            task = asyncio.create_task(server.serve(sockets=[sock]))
            try:
                async with asyncio.timeout(5):
                    while not server.started:
                        await asyncio.sleep(0.01)
                assert (await asyncio.to_thread(request, origin, "/openapi.json"))[
                    0
                ] == 403
            finally:
                server.should_exit = True
                await asyncio.wait_for(task, 5)

    asyncio.run(exercise())


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "192.0.2.1", "localhost", ""])
def test_nonloopback_bind_refused_before_lifespan(
    configured_database: tuple[Path, Path], host: str
) -> None:
    bootstrap = implementation()
    from agentmonitor.foundation.application import LifecycleHooksV1

    app = bootstrap.create_foundation_application(
        *configured_database, lifecycle=LifecycleHooksV1()
    )
    with pytest.raises(bootstrap.LoopbackServerError, match="bind_not_loopback"):
        asyncio.run(
            bootstrap.serve_loopback(
                app, host=host, port=0, ready=None, stop=asyncio.Event()
            )
        )
    assert app.state.lifecycle.phase == "created"


def test_port_collision_and_restart_release_real_resources(
    configured_database: tuple[Path, Path],
) -> None:
    bootstrap = implementation()
    from agentmonitor.foundation.application import LifecycleHooksV1

    async def exercise() -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
            occupied.bind(("127.0.0.1", 0))
            occupied.listen()
            port = occupied.getsockname()[1]
            app = bootstrap.create_foundation_application(
                *configured_database, lifecycle=LifecycleHooksV1()
            )
            with pytest.raises(bootstrap.LoopbackServerError, match="bind_unavailable"):
                await bootstrap.serve_loopback(
                    app, host="127.0.0.1", port=port, ready=None, stop=asyncio.Event()
                )
            assert app.state.lifecycle.phase == "created"
        for _ in range(2):
            app = bootstrap.create_foundation_application(
                *configured_database,
                lifecycle=LifecycleHooksV1(foundation_contract_mode=True),
            )
            async with running(app, port=port) as origin:
                assert (await asyncio.to_thread(request, origin, "/openapi.json"))[
                    0
                ] == 200
            assert app.state.lifecycle.phase == "stopped"
            assert not (configured_database[1] / "agentmonitor.db-wal").exists()

    asyncio.run(exercise())


def test_missing_database_fails_without_creation(tmp_path: Path) -> None:
    bootstrap = implementation()
    from agentmonitor.foundation.application import LifecycleHooksV1

    config = tmp_path / "isolated.env"
    config.write_text("")
    config.chmod(0o600)
    app = bootstrap.create_foundation_application(
        config, tmp_path, lifecycle=LifecycleHooksV1()
    )
    with pytest.raises(bootstrap.LoopbackServerError, match="startup_failed"):
        asyncio.run(
            bootstrap.serve_loopback(
                app, host="127.0.0.1", port=0, ready=None, stop=asyncio.Event()
            )
        )
    assert app.state.lifecycle.failure_code == "database_missing"
    assert not (tmp_path / "agentmonitor.db").exists()


async def real_child_failure() -> None:
    child = await asyncio.create_subprocess_exec(
        sys.executable, "-c", "raise SystemExit(7)"
    )
    returncode = await child.wait()
    if returncode:
        raise subprocess.CalledProcessError(returncode, "owned-child")


async def real_child_wait() -> None:
    child = await asyncio.create_subprocess_exec(
        sys.executable, "-c", "import time; time.sleep(30)"
    )
    try:
        await child.wait()
    finally:
        if child.returncode is None:
            child.terminate()
        await child.wait()


@pytest.mark.parametrize("shutdown", ["normal", "failure", "timeout"])
def test_cancelling_server_during_shutdown_drains_lifespan_and_restarts(
    configured_database: tuple[Path, Path],
    shutdown: str,
) -> None:
    bootstrap = implementation()
    from agentmonitor.foundation.application import LifecycleHooksV1

    async def exercise() -> None:
        original_tasks = asyncio.all_tasks()
        app = bootstrap.create_foundation_application(
            *configured_database,
            lifecycle=LifecycleHooksV1(
                foundation_contract_mode=True,
                shutdown_timeout_seconds=0.4,
                shutdown=()
                if shutdown == "normal"
                else (
                    real_child_failure if shutdown == "failure" else real_child_wait,
                ),
            ),
        )
        ready: asyncio.Future[str] = asyncio.get_running_loop().create_future()
        stop = asyncio.Event()
        server_task = asyncio.create_task(
            bootstrap.serve_loopback(
                app,
                host="127.0.0.1",
                port=0,
                ready=ready.set_result,
                stop=stop,
            )
        )
        try:
            origin = await asyncio.wait_for(ready, 5)
            assert (await asyncio.to_thread(request, origin, "/openapi.json"))[0] == 200
            stop.set()
            await asyncio.sleep(0.04)
            server_task.cancel()
            # Repeated cancellation must not interrupt the owned cleanup either.
            again = asyncio.get_running_loop().call_later(0.02, server_task.cancel)
            try:
                expected = (
                    asyncio.CancelledError
                    if shutdown == "normal"
                    else bootstrap.LoopbackServerError
                )
                with pytest.raises(expected):
                    await asyncio.wait_for(server_task, 5)
            finally:
                again.cancel()
            assert app.state.lifecycle.phase == (
                "stopped" if shutdown == "normal" else "failed"
            ), "FND-LIFE-001: caller cancellation abandoned the real lifespan"
            assert (
                app.state.lifecycle.failure_code
                == {
                    "normal": None,
                    "failure": "shutdown_failed",
                    "timeout": "shutdown_timeout",
                }[shutdown]
            )
            assert not (configured_database[1] / "agentmonitor.db-wal").exists()
            assert not (configured_database[1] / "agentmonitor.db-shm").exists()
            await asyncio.sleep(0)
            assert not (asyncio.all_tasks() - original_tasks), "owned task leaked"
            restarted = bootstrap.create_foundation_application(
                *configured_database,
                lifecycle=LifecycleHooksV1(foundation_contract_mode=True),
            )
            async with running(
                restarted, port=int(origin.rsplit(":", 1)[1])
            ) as new_origin:
                assert (await asyncio.to_thread(request, new_origin, "/openapi.json"))[
                    0
                ] == 200
            assert restarted.state.lifecycle.phase == "stopped"
        finally:
            # Preserve genuine Red while cleaning up this test's owned tasks.
            remaining = asyncio.all_tasks() - original_tasks
            for task in remaining:
                task.cancel()
            await asyncio.gather(*remaining, return_exceptions=True)

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "condition",
    [
        "startup_failure",
        "startup_cancellation",
        "shutdown_failure",
        "shutdown_cancellation",
        "shutdown_timeout",
        "normal",
    ],
)
def test_partial_startup_and_cleanup_failures_reap_owned_resources(
    configured_database: tuple[Path, Path],
    condition: str,
) -> None:
    bootstrap = implementation()
    from agentmonitor.foundation.application import LifecycleHooksV1

    async def exercise() -> None:
        original_tasks = asyncio.all_tasks()
        children: list[asyncio.subprocess.Process] = []
        cleanup_order: list[str] = []

        async def acquire() -> None:
            children.append(
                await asyncio.create_subprocess_exec(
                    sys.executable,
                    "-c",
                    "import time; time.sleep(30)",
                )
            )

        async def release() -> None:
            # Idempotent cleanup also tolerates acquisition not having happened.
            cleanup_order.append("resource")
            for child in children:
                if child.returncode is None:
                    child.terminate()
                await child.wait()

        async def cancel_this_hook() -> None:
            task = asyncio.current_task()
            assert task is not None
            task.cancel()
            await asyncio.sleep(0)

        async def second_startup() -> None:
            if condition == "startup_failure":
                await real_child_failure()
            elif condition == "startup_cancellation":
                await cancel_this_hook()

        async def second_cleanup() -> None:
            cleanup_order.append("second")
            if condition == "shutdown_failure":
                await real_child_failure()
            elif condition == "shutdown_cancellation":
                await cancel_this_hook()
            elif condition == "shutdown_timeout":
                await real_child_wait()

        app = bootstrap.create_foundation_application(
            *configured_database,
            lifecycle=LifecycleHooksV1(
                startup=(acquire, second_startup),
                shutdown=(release, second_cleanup),
                shutdown_timeout_seconds=0.4,
            ),
        )
        try:
            if condition == "normal":
                async with running(app):
                    pass
            else:
                # A self-cancelled hook must also be a visible typed failure.
                with pytest.raises(bootstrap.LoopbackServerError):
                    async with running(app):
                        pass
            assert children and all(
                child.returncode is not None for child in children
            ), "FND-LIFE-001: registered cleanup left an owned child alive"
            assert cleanup_order == ["second", "resource"]
            expected_codes = {
                "startup_failure": "startup_failed",
                "startup_cancellation": "startup_cancelled",
                "shutdown_failure": "shutdown_failed",
                "shutdown_cancellation": "shutdown_cancelled",
                "shutdown_timeout": "shutdown_timeout",
                "normal": None,
            }
            assert app.state.lifecycle.failure_code == expected_codes[condition]
            assert app.state.lifecycle.phase == (
                "stopped" if condition == "normal" else "failed"
            )
            assert not (configured_database[1] / "agentmonitor.db-wal").exists()
            await asyncio.sleep(0)
            assert not (asyncio.all_tasks() - original_tasks), "owned task leaked"
        finally:
            for child in children:
                if child.returncode is None:
                    child.terminate()
                await child.wait()
            remaining = asyncio.all_tasks() - original_tasks
            for task in remaining:
                task.cancel()
            await asyncio.gather(*remaining, return_exceptions=True)

    asyncio.run(exercise())


def test_real_task_failure_is_surfaced_without_stopping_http(
    configured_database: tuple[Path, Path],
) -> None:
    bootstrap = implementation()
    from agentmonitor.foundation.application import LifecycleHooksV1

    app = bootstrap.create_foundation_application(
        *configured_database,
        lifecycle=LifecycleHooksV1(
            foundation_contract_mode=True, tasks=(real_child_failure, real_child_wait)
        ),
    )

    async def exercise() -> None:
        async with running(app) as origin:
            async with asyncio.timeout(3):
                while not app.state.lifecycle.task_failures:
                    await asyncio.sleep(0.01)
            assert app.state.lifecycle.task_failures == ("background_task_failed",)
            assert (await asyncio.to_thread(request, origin, "/openapi.json"))[0] == 200
        assert app.state.lifecycle.phase == "stopped"

    asyncio.run(exercise())


@pytest.mark.parametrize("phase", ["startup", "shutdown"])
def test_lifecycle_deadline_closes_database_and_own_child(
    configured_database: tuple[Path, Path], phase: str
) -> None:
    bootstrap = implementation()
    from agentmonitor.foundation.application import LifecycleHooksV1

    lifecycle = LifecycleHooksV1(
        startup=(real_child_wait,) if phase == "startup" else (),
        shutdown=(real_child_wait,) if phase == "shutdown" else (),
        startup_timeout_seconds=0.2,
        shutdown_timeout_seconds=0.2,
    )
    app = bootstrap.create_foundation_application(
        *configured_database, lifecycle=lifecycle
    )

    async def exercise() -> None:
        if phase == "startup":
            with pytest.raises(bootstrap.LoopbackServerError, match="startup_failed"):
                async with running(app):
                    pytest.fail("timed out startup became ready")
        else:
            with pytest.raises(bootstrap.LoopbackServerError, match="shutdown_failed"):
                async with running(app):
                    pass

    began = time.monotonic()
    asyncio.run(exercise())
    assert time.monotonic() - began < 4
    assert app.state.lifecycle.failure_code == f"{phase}_timeout"
    assert not (configured_database[1] / "agentmonitor.db-wal").exists()


@pytest.mark.parametrize("unregistered_server_settings", [False, True])
def test_real_process_sigterm_is_bounded_and_restartable(
    configured_database: tuple[Path, Path],
    unregistered_server_settings: bool,
) -> None:
    implementation()
    config, root = configured_database
    environment = {"PYTHONPATH": str(ROOT / "backend/src"), "PATH": os.defpath}
    if unregistered_server_settings:
        environment |= {"WEB_CONCURRENCY": "unregistered", "FORWARDED_ALLOW_IPS": "*"}
    for _ in range(2):
        child = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "agentmonitor.composition.bootstrap",
                "--config",
                str(config),
                "--data-root",
                str(root),
                "--host",
                "127.0.0.1",
                "--port",
                "0",
                "--foundation-contract",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
        )
        try:
            assert child.stdout is not None
            import select

            assert select.select([child.stdout], [], [], 8)[0], "no bounded readiness"
            record = json.loads(child.stdout.readline())
            assert record["event"] == "ready"
            assert request(record["origin"], "/openapi.json")[0] == 200
            child.send_signal(signal.SIGTERM)
            out, err = child.communicate(timeout=8)
            assert child.returncode == 0
            assert not err
            assert str(root) not in out
        finally:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=8)
        assert not (root / "agentmonitor.db-wal").exists()


@pytest.fixture
def isolated_generator(tmp_path: Path) -> Iterator[tuple[Path, dict[str, str]]]:
    for relative in ("backend/src", "backend/migrations", "tooling/foundation"):
        shutil.copytree(
            ROOT / relative,
            tmp_path / relative,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
    shutil.copyfile(
        ROOT / "backend/pyproject.toml", tmp_path / "backend/pyproject.toml"
    )
    # The compatibility oracle is the real approved artifact committed at
    # HEAD, not a synthetic in-memory schema or an uncommitted M2 draft.
    for relative in (
        "contracts/openapi/agentmonitor-v1.json",
        "frontend/src/generated/api/index.ts",
    ):
        baseline = subprocess.run(
            ["git", "show", f"HEAD:{relative}"],
            cwd=ROOT,
            capture_output=True,
            check=False,
            timeout=5,
        )
        assert baseline.returncode == 0, "committed generator baseline missing"
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(baseline.stdout)
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True, timeout=5)
    subprocess.run(
        [
            "git",
            "add",
            "contracts/openapi/agentmonitor-v1.json",
            "frontend/src/generated/api/index.ts",
        ],
        cwd=tmp_path,
        check=True,
        timeout=5,
    )
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=AgentMonitor Test",
            "-c",
            "user.email=agentmonitor-test@invalid.example",
            "commit",
            "--quiet",
            "-m",
            "approved artifact baseline",
        ],
        cwd=tmp_path,
        check=True,
        timeout=5,
    )
    (tmp_path / "contracts/openapi/agentmonitor-v1.json").unlink()
    (tmp_path / "frontend/src/generated/api/index.ts").unlink()
    yield tmp_path, {"PYTHONPATH": str(tmp_path / "backend/src"), "PATH": os.defpath}


def test_generation_replaces_only_uncommitted_generated_draft_against_head(
    isolated_generator: tuple[Path, dict[str, str]],
) -> None:
    root, environment = isolated_generator
    command = [sys.executable, str(root / "tooling/foundation/openapi_client.py")]
    first = subprocess.run(
        command + ["--write"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert first.returncode == 0, first.stdout + first.stderr
    artifact = root / "contracts/openapi/agentmonitor-v1.json"
    before = artifact.read_bytes()
    route_source = root / "backend/src/agentmonitor/api/v1/routers/iam.py"
    original = route_source.read_text()
    # A source-only draft changes the generated provenance hash without
    # changing the approved HTTP contract. Breaking descriptions are checked
    # separately below and must never be accepted as a draft replacement.
    route_source.write_text(original + "\n# Compatible source-only draft update.\n")
    rewritten = subprocess.run(
        command + ["--write"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert rewritten.returncode == 0, rewritten.stdout + rewritten.stderr
    assert artifact.read_bytes() != before
    checked = subprocess.run(
        command + ["--check"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert checked.returncode == 0, checked.stdout + checked.stderr


@pytest.mark.parametrize("baseline_loss", ["not_a_repository", "missing_head_blob"])
def test_generation_refuses_absent_committed_baseline(
    isolated_generator: tuple[Path, dict[str, str]], baseline_loss: str
) -> None:
    root, environment = isolated_generator
    if baseline_loss == "not_a_repository":
        (root / ".git").rename(root / ".git-hidden")
    else:
        subprocess.run(
            [
                "git",
                "rm",
                "--cached",
                "--quiet",
                "contracts/openapi/agentmonitor-v1.json",
            ],
            cwd=root,
            check=True,
            timeout=5,
        )
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=AgentMonitor Test",
                "-c",
                "user.email=agentmonitor-test@invalid.example",
                "commit",
                "--quiet",
                "-m",
                "remove approved artifact baseline",
            ],
            cwd=root,
            check=True,
            timeout=5,
        )
    command = [sys.executable, str(root / "tooling/foundation/openapi_client.py")]
    refused = subprocess.run(
        command + ["--write"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert refused.returncode == 1
    assert "approved_baseline_unavailable" in refused.stdout
    assert not refused.stderr
    assert not (root / "contracts/openapi/agentmonitor-v1.json").exists()
    assert not (root / "frontend/src/generated/api/index.ts").exists()


def test_generation_is_reproducible_check_detects_drift_and_types_compile(
    isolated_generator: tuple[Path, dict[str, str]],
) -> None:
    generator()
    root, environment = isolated_generator
    command = [sys.executable, str(root / "tooling/foundation/openapi_client.py")]

    def invoke(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command + list(args),
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
        )

    first = invoke()
    assert first.returncode == 0, first.stdout + first.stderr
    schema = root / "contracts/openapi/agentmonitor-v1.json"
    client = root / "frontend/src/generated/api/index.ts"
    before = schema.read_bytes(), client.read_bytes()
    assert invoke().returncode == 0
    assert before == (schema.read_bytes(), client.read_bytes())
    assert invoke("--check").returncode == 0
    digest = hashlib.sha256(before[0]).hexdigest()
    assert digest in before[1].decode()
    operations = [
        operation["operationId"]
        for methods in json.loads(before[0])["paths"].values()
        for operation in methods.values()
    ]
    assert len(operations) == len(set(operations)) == 23
    assert str(root).encode() not in b"".join(before)
    compiled = subprocess.run(
        [
            str(ROOT / "frontend/node_modules/.bin/tsc"),
            "--strict",
            "--noEmit",
            "--noUncheckedIndexedAccess",
            "--target",
            "ES2023",
            str(client),
        ],
        capture_output=True,
        text=True,
        timeout=20,
        env={"PATH": os.defpath},
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    client.write_bytes(before[1] + b"\n// isolated deliberate drift\n")
    drifted = client.read_bytes()
    checked = invoke("--check")
    assert checked.returncode == 1
    assert "generated_drift" in checked.stdout
    assert client.read_bytes() == drifted and schema.read_bytes() == before[0]


def test_generation_rejects_arbitrary_factory_and_output_paths(tmp_path: Path) -> None:
    tool = generator()
    with pytest.raises(tool.OpenApiGenerationError, match="factory_not_approved"):
        tool.generate_openapi_client("os:system", tmp_path / "schema.json", tmp_path)
    with pytest.raises(tool.OpenApiGenerationError, match="output_not_allocated"):
        tool.generate_openapi_client(FACTORY, tmp_path / "schema.json", tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("mutation", ["breaking", "symlink", "schema_drift", "absent"])
def test_generator_cli_preserves_outputs_on_refusal(
    isolated_generator: tuple[Path, dict[str, str]], mutation: str
) -> None:
    root, environment = isolated_generator
    command = [sys.executable, str(root / "tooling/foundation/openapi_client.py")]
    schema = root / "contracts/openapi/agentmonitor-v1.json"
    client = root / "frontend/src/generated/api/index.ts"
    if mutation == "absent":
        failed = subprocess.run(
            command + ["--check"],
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert failed.returncode == 1 and "generated_drift" in failed.stdout
        assert not schema.exists() and not client.exists()
        return
    generated = subprocess.run(
        command, env=environment, capture_output=True, text=True, timeout=15
    )
    assert generated.returncode == 0
    arguments: list[str] = []
    if mutation == "breaking":
        subprocess.run(
            [
                "git",
                "add",
                "contracts/openapi/agentmonitor-v1.json",
                "frontend/src/generated/api/index.ts",
            ],
            cwd=root,
            check=True,
            timeout=5,
        )
        staged = subprocess.run(
            [
                "git",
                "diff",
                "--cached",
                "--quiet",
                "--",
                "contracts/openapi/agentmonitor-v1.json",
                "frontend/src/generated/api/index.ts",
            ],
            cwd=root,
            check=False,
            timeout=5,
        )
        assert staged.returncode in (0, 1), "generated artifact staging failed"
        # Older checkout baselines need the generated M2 contract committed;
        # current M2 baselines already contain it, so Git has nothing to commit.
        if staged.returncode == 1:
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=AgentMonitor Test",
                    "-c",
                    "user.email=agentmonitor-test@invalid.example",
                    "commit",
                    "--quiet",
                    "-m",
                    "accepted generated M2 contract",
                ],
                cwd=root,
                check=True,
                timeout=5,
            )
        route_source = root / "backend/src/agentmonitor/api/v1/routers/iam.py"
        original = route_source.read_text()
        assert '"description": "SafeProblemV1"' in original
        route_source.write_text(
            original.replace(
                '"description": "SafeProblemV1"',
                '"description": "SafeProblemV1 adjusted"',
                1,
            )
        )
        expected = "breaking_drift"
    elif mutation == "symlink":
        preserved = root / "preserved-generated.ts"
        client.rename(preserved)
        client.symlink_to(preserved)
        expected = "artifact_path_unsafe"
    else:
        schema.write_bytes(schema.read_bytes() + b"\n")
        arguments = ["--check"]
        expected = "generated_drift"
    before = schema.read_bytes(), client.read_bytes()
    failed = subprocess.run(
        command + arguments, env=environment, capture_output=True, text=True, timeout=15
    )
    assert failed.returncode == 1 and expected in failed.stdout
    assert not failed.stderr
    assert before == (schema.read_bytes(), client.read_bytes())
    assert not list(root.rglob(".agentmonitor-generation-*"))


def test_schema_validation_and_breaking_diff_are_fail_closed() -> None:
    tool = generator()
    source = {
        "openapi": "3.1.0",
        "info": {"title": "AgentMonitor", "version": "0.0.0"},
        "paths": {},
    }
    assert tool.validate_openapi(source) == ()
    valid_operation = {
        "operationId": "repeated",
        "responses": {"200": {"description": "Success"}},
    }
    for change, expected in (
        ({"openapi": "2.0"}, "openapi_version_unsupported"),
        ({"paths": {"/outside": {"get": valid_operation}}}, "unversioned_path"),
        (
            {
                "paths": {
                    "/api/v1/one": {"get": valid_operation},
                    "/api/v1/two": {"get": valid_operation},
                }
            },
            "operation_id_duplicate",
        ),
    ):
        with pytest.raises(tool.OpenApiGenerationError, match=expected):
            tool.validate_openapi(source | change)
    previous = source | {
        "paths": {
            "/api/v1/one": {
                "get": {
                    "operationId": "one",
                    "responses": {"200": {"description": "Success"}},
                }
            }
        }
    }
    assert tool.classify_compatibility(previous, source) == "breaking"
    assert tool.classify_compatibility(source, previous) == "compatible"
    component_baseline = previous | {
        "components": {"schemas": {"ExistingV1": {"type": "string"}}}
    }
    component_addition = previous | {
        "components": {
            "schemas": {
                "ExistingV1": {"type": "string"},
                "AddedV1": {"type": "integer"},
            }
        }
    }
    assert tool.classify_compatibility(component_baseline, component_addition) == (
        "compatible"
    )
    changed_existing = previous | {
        "components": {"schemas": {"ExistingV1": {"type": "integer"}}}
    }
    assert tool.classify_compatibility(component_baseline, changed_existing) == (
        "breaking"
    )
    object_baseline = previous | {
        "components": {
            "schemas": {
                "ExistingV1": {
                    "type": "object",
                    "properties": {"existing": {"type": "string"}},
                    "required": ["existing"],
                }
            }
        }
    }
    optional_addition = previous | {
        "components": {
            "schemas": {
                "ExistingV1": {
                    "type": "object",
                    "properties": {
                        "existing": {"type": "string"},
                        "added": {"type": "integer"},
                    },
                    "required": ["existing"],
                }
            }
        }
    }
    assert tool.classify_compatibility(object_baseline, optional_addition) == (
        "compatible"
    )
    required_addition = previous | {
        "components": {
            "schemas": {
                "ExistingV1": {
                    "type": "object",
                    "properties": {
                        "existing": {"type": "string"},
                        "added": {"type": "integer"},
                    },
                    "required": ["existing", "added"],
                }
            }
        }
    }
    assert tool.classify_compatibility(object_baseline, required_addition) == "breaking"


def test_generator_public_failure_is_typed_and_sanitized(
    isolated_generator: tuple[Path, dict[str, str]],
) -> None:
    root, environment = isolated_generator
    tool = root / "tooling/foundation/openapi_client.py"
    generated = subprocess.run(
        [sys.executable, str(tool)],
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert generated.returncode == 0
    schema = root / "contracts/openapi/agentmonitor-v1.json"
    schema.write_text("invalid isolated baseline")
    code = """
from pathlib import Path
from tooling.foundation.openapi_client import (
    FACTORY_REF, generate_openapi_client, OpenApiGenerationError,
)
root = Path.cwd()
try:
    generate_openapi_client(
        FACTORY_REF, root / 'contracts/openapi/agentmonitor-v1.json',
        root / 'frontend/src/generated/api')
except OpenApiGenerationError as error:
    print(error.code)
else:
    raise AssertionError('invalid baseline was accepted')
"""
    checked = subprocess.run(
        [sys.executable, "-c", code],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert checked.returncode == 0, "public generator leaked an untyped failure"
    assert checked.stdout.strip() == "generation_input_invalid"
    assert not checked.stderr
    assert schema.read_text() == "invalid isolated baseline"


def test_production_imports_do_not_open_data_or_network(tmp_path: Path) -> None:
    implementation()
    code = """
import sys
def guard(event, args):
    prohibited = {'socket.__new__', 'socket.connect', 'socket.bind',
                  'sqlite3.connect', 'subprocess.Popen'}
    if event in prohibited:
        raise RuntimeError('import_boundary_io')
sys.addaudithook(guard)
import agentmonitor.foundation.application
import agentmonitor.api.app
import agentmonitor.composition.bootstrap
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env={"PYTHONPATH": str(ROOT / "backend/src"), "PATH": os.defpath},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert list(tmp_path.iterdir()) == []

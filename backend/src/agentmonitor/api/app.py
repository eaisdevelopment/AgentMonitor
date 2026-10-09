"""Production FastAPI factory for M1 foundation and M2 IAM modes.

Foundation schema disclosure and authenticated local IAM documentation are
separate transports. The foundation guard is not IAM Host/Origin/CSRF policy.
"""

import fcntl
import ipaddress
import os
import re
import secrets
import stat
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from agentmonitor.api.problem import (
    PROBLEM_DESCRIPTIONS,
    ProblemError,
    SafeProblemV1,
    handle_http,
    handle_problem,
    handle_repository_unavailable,
    handle_unexpected,
    handle_validation,
)
from agentmonitor.api.transport import IamTransportGuard
from agentmonitor.api.v1.dependencies import (
    IamApiPortsV1,
    ObservationApiPortsV1,
    authenticate_documentation_request,
)
from agentmonitor.api.v1.pagination import CursorCodecV1
from agentmonitor.api.v1.router import create_router
from agentmonitor.contracts.configuration_v1 import BootstrapConfigurationV1
from agentmonitor.contracts.foundation_v1 import BuildMetadataV1
from agentmonitor.foundation.application import (
    ApplicationLifecycleError,
    ApplicationLifecycleV1,
    ComponentFactorySetV1,
    LifecycleHooksV1,
)
from agentmonitor.modules.identity_access.application.errors import (
    IamRepositoryUnavailableV1,
)
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send


@dataclass(slots=True)
class LoopbackSchemaBinding:
    """Runner-owned authority; absent until the approved socket is bound."""

    address: tuple[str, int] | None = None
    lan_address: tuple[str, int] | None = None
    lan_network: ipaddress.IPv4Network | None = None


@asynccontextmanager
async def hold_service_quiescence_lock(path: Path) -> AsyncIterator[None]:
    """Service side of the stable, owner-only recovery exclusion protocol.

    Recovery must take this same lock before opening SQLite. The file is never
    unlinked because unlinking could create two independent lock inodes.
    """
    flags = os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as error:
        raise ApplicationLifecycleError("service_lock_unavailable") from error
    try:
        state = os.fstat(descriptor)
        if (
            not stat.S_ISREG(state.st_mode)
            or stat.S_IMODE(state.st_mode) != 0o600
            or state.st_uid != os.getuid()
        ):
            raise ApplicationLifecycleError("service_lock_unsafe")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise ApplicationLifecycleError("service_lock_occupied") from error
        try:
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)


class FoundationSchemaGuard:
    """Allow schema disclosure only over an actual IPv4 loopback transport.

    Uvicorn proxy trust is off. Even an app served outside the approved runner
    cannot expose the schema through a wildcard/non-loopback listening address.
    Exact Host and optional Origin must match the actual socket's authority.
    """

    def __init__(self, app: ASGIApp, binding: LoopbackSchemaBinding) -> None:
        self.app = app
        self.binding = binding

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"] == "/openapi.json":
            server = scope.get("server")
            client = scope.get("client")
            allowed = (
                server is not None
                and server[0] == "127.0.0.1"
                and server == self.binding.address
                and client is not None
                and client[0] == "127.0.0.1"
                and scope.get("scheme") == "http"
            )
            if server is not None:
                authority = f"127.0.0.1:{server[1]}".encode("ascii")
                hosts = [value for key, value in scope["headers"] if key == b"host"]
                origins = [value for key, value in scope["headers"] if key == b"origin"]
                allowed = (
                    allowed
                    and hosts == [authority]
                    and (not origins or origins == [b"http://" + authority])
                )
            if not allowed:
                await Response(status_code=403)(scope, receive, send)
                return
        await self.app(scope, receive, send)


def create_application(
    settings: BootstrapConfigurationV1,
    components: ComponentFactorySetV1,
    build: BuildMetadataV1,
    lifecycle: LifecycleHooksV1,
    *,
    iam_mode: bool = False,
    iam_ports: IamApiPortsV1 | None = None,
    observation_ports: ObservationApiPortsV1 | None = None,
    service_lock_path: Path | None = None,
) -> FastAPI:
    """CTR-FND-002: explicit dependencies, no I/O until real ASGI lifespan."""
    if settings.configuration_version != "1.0.0":
        raise ApplicationLifecycleError("configuration_version_unsupported")
    if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", build.application_version) is None:
        raise ApplicationLifecycleError("build_version_invalid")
    runtime = ApplicationLifecycleV1(components, lifecycle)
    binding = LoopbackSchemaBinding()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if iam_mode:
            if service_lock_path is None:
                raise ApplicationLifecycleError("service_lock_unavailable")
            app.state.cursor_codec = CursorCodecV1(secrets.token_bytes(32))
            try:
                async with hold_service_quiescence_lock(service_lock_path):
                    async with runtime.lifespan():
                        yield
            finally:
                app.state.cursor_codec = None
        else:
            async with runtime.lifespan():
                yield

    app = FastAPI(
        title="AgentMonitor",
        version=build.application_version,
        docs_url=None,
        redoc_url=None,
        openapi_url=(
            "/openapi.json"
            if lifecycle.foundation_contract_mode and not iam_mode
            else None
        ),
        lifespan=lifespan,
    )
    app.openapi_version = "3.1.0"
    app.state.lifecycle = runtime
    app.state.build = build
    app.state.loopback_schema_binding = binding
    app.state.iam_ports = iam_ports
    app.state.observation_ports = observation_ports
    app.include_router(create_router(iam_mode=iam_mode))
    frontend_build = Path(__file__).resolve().parents[4] / "frontend" / "dist"
    if iam_mode:
        original_openapi = app.openapi

        def iam_openapi() -> dict[str, object]:
            schema = original_openapi()
            components = schema.setdefault("components", {})
            models = components.setdefault("schemas", {})
            safe_problem = SafeProblemV1.model_json_schema(
                ref_template="#/components/schemas/{model}"
            )
            definitions = safe_problem.pop("$defs", {})
            models.update(definitions)
            models["SafeProblemV1"] = safe_problem
            components["securitySchemes"] = {
                "BearerTokenV1": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "opaque",
                },
                "BrowserSessionCookieV1": {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": "agentmonitor_session",
                },
                "BrowserCsrfHeaderV1": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-CSRF-Token",
                },
            }
            return schema

        # FastAPI intentionally publishes this method as a replaceable schema hook.
        app.openapi = iam_openapi  # type: ignore[method-assign]

        @app.get("/openapi.json", include_in_schema=False)
        def authenticated_openapi(request: Request) -> JSONResponse:
            authenticate_documentation_request(request)
            return JSONResponse(app.openapi())

        @app.get("/docs", include_in_schema=False)
        def authenticated_swagger(request: Request) -> HTMLResponse:
            authenticate_documentation_request(request)
            return HTMLResponse(
                '<!doctype html><html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                "<title>AgentMonitor API</title>"
                '<link rel="stylesheet" href="/docs-assets/swagger/swagger-ui.css">'
                '</head><body><div id="swagger-ui"></div>'
                '<script src="/docs-assets/swagger/swagger-ui-bundle.js"></script>'
                '<script src="/docs-assets/swagger/'
                'swagger-ui-standalone-preset.js"></script>'
                '<script src="/docs-assets/swagger/bootstrap.js"></script>'
                "</body></html>"
            )

        @app.get("/redoc", include_in_schema=False)
        def authenticated_redoc(request: Request) -> HTMLResponse:
            authenticate_documentation_request(request)
            return HTMLResponse(
                '<!doctype html><html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                "<title>AgentMonitor API Reference</title>"
                '</head><body><div id="redoc"></div>'
                '<script src="/docs-assets/redoc/redoc.standalone.js"></script>'
                '<script src="/docs-assets/redoc/bootstrap.js"></script>'
                "</body></html>"
            )

        documentation_assets = {
            "swagger-ui.css": ("swagger", "text/css"),
            "swagger-ui-bundle.js": ("swagger", "application/javascript"),
            "swagger-ui-standalone-preset.js": (
                "swagger",
                "application/javascript",
            ),
            "bootstrap.js": ("swagger", "application/javascript"),
        }
        redoc_assets = {
            "redoc.standalone.js": ("redoc", "application/javascript"),
            "bootstrap.js": ("redoc", "application/javascript"),
            "redoc-mark.svg": ("redoc", "image/svg+xml"),
        }

        @app.get("/docs-assets/{family}/{filename}", include_in_schema=False)
        def authenticated_documentation_asset(
            request: Request, family: str, filename: str
        ) -> FileResponse:
            authenticate_documentation_request(request)
            entry = (
                documentation_assets.get(filename)
                if family == "swagger"
                else redoc_assets.get(filename)
                if family == "redoc"
                else None
            )
            if entry is None or entry[0] != family:
                raise ProblemError(404, "resource_not_found")
            asset = (
                Path(__file__).resolve().parent / "assets" / "docs" / family / filename
            )
            if not asset.is_file():
                raise ProblemError(500, "internal_error")
            return FileResponse(asset, media_type=entry[1])

        @app.get("/problems/{code}", include_in_schema=False)
        def authenticated_problem_document(request: Request, code: str) -> HTMLResponse:
            authenticate_documentation_request(request)
            description = PROBLEM_DESCRIPTIONS.get(code)
            if description is None:
                raise ProblemError(404, "resource_not_found")
            # Both fields come only from the closed catalog, never request data.
            return HTMLResponse(
                '<!doctype html><html lang="en"><head><meta charset="utf-8">'
                f"<title>AgentMonitor problem: {code}</title></head><body>"
                f"<h1>{code}</h1><p>{description}</p></body></html>"
            )

        @app.get("/", include_in_schema=False)
        @app.get("/login", include_in_schema=False)
        @app.get("/settings/api-tokens", include_in_schema=False)
        @app.get("/accounts", include_in_schema=False)
        @app.get("/accounts/{account_id}", include_in_schema=False)
        @app.get("/organizations", include_in_schema=False)
        @app.get("/providers", include_in_schema=False)
        @app.get("/collectors", include_in_schema=False)
        @app.get("/sessions", include_in_schema=False)
        @app.get("/operations", include_in_schema=False)
        @app.get("/alerts", include_in_schema=False)
        @app.get("/alert-rules", include_in_schema=False)
        def dashboard_html() -> FileResponse:
            """Serve only approved SPA entries; API/docs routes remain distinct."""
            entry = frontend_build / "dashboard.html"
            if not entry.is_file():
                raise ProblemError(500, "internal_error")
            return FileResponse(entry, media_type="text/html")

        app.add_exception_handler(ProblemError, handle_problem)
        app.add_exception_handler(RequestValidationError, handle_validation)
        app.add_exception_handler(StarletteHTTPException, handle_http)
        app.add_exception_handler(
            IamRepositoryUnavailableV1, handle_repository_unavailable
        )
        app.add_exception_handler(Exception, handle_unexpected)
        app.add_middleware(IamTransportGuard, binding=binding)
    else:
        app.add_middleware(FoundationSchemaGuard, binding=binding)
    if iam_mode:

        @app.get("/favicon.svg", include_in_schema=False)
        def dashboard_favicon() -> FileResponse:
            icon = frontend_build / "favicon.svg"
            if not icon.is_file():
                raise ProblemError(404, "resource_not_found")
            return FileResponse(icon, media_type="image/svg+xml")

        # In IAM mode, the exact HTML routes above are the only public shell
        # entries. Never expose the M1 index or dashboard source HTML by file
        # name through a catch-all static mount.
        app.mount(
            "/assets",
            StaticFiles(
                directory=str(frontend_build / "assets"),
                html=False,
                check_dir=False,
            ),
            name="dashboard_assets",
        )
    else:
        # M1's foundation entrypoint remains unchanged and uses only the
        # locally built artifact, never a Vite development server.
        app.mount(
            "/",
            StaticFiles(directory=str(frontend_build), html=True, check_dir=False),
            name="frontend",
        )
    return app

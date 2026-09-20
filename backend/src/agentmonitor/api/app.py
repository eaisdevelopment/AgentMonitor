"""Production FastAPI factory for the bounded M1 foundation contract mode.

No installed/public documentation is inferred. IAM/P01 must supply approved
authenticated documentation later. This schema transport guard is deliberately
limited to M1; it is not the V1 authentication, Host/Origin or CSRF contract.
"""

import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from agentmonitor.api.v1.router import create_router
from agentmonitor.contracts.configuration_v1 import BootstrapConfigurationV1
from agentmonitor.contracts.foundation_v1 import BuildMetadataV1
from agentmonitor.foundation.application import (
    ApplicationLifecycleError,
    ApplicationLifecycleV1,
    ComponentFactorySetV1,
    LifecycleHooksV1,
)
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send


@dataclass(slots=True)
class LoopbackSchemaBinding:
    """Runner-owned authority; absent until the approved socket is bound."""

    address: tuple[str, int] | None = None


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
        async with runtime.lifespan():
            yield

    app = FastAPI(
        title="AgentMonitor",
        version=build.application_version,
        docs_url=None,
        redoc_url=None,
        openapi_url="/openapi.json" if lifecycle.foundation_contract_mode else None,
        lifespan=lifespan,
    )
    app.openapi_version = "3.1.0"
    app.state.lifecycle = runtime
    app.state.build = build
    app.state.loopback_schema_binding = binding
    app.include_router(create_router())
    app.add_middleware(FoundationSchemaGuard, binding=binding)
    # The static mount is deliberately a fallback after the versioned API and
    # framework schema routes. It serves only a locally built artifact through
    # the same loopback authority; Vite's development server is never used as
    # a product boundary.
    frontend_build = Path(__file__).resolve().parents[4] / "frontend" / "dist"
    app.mount(
        "/",
        StaticFiles(directory=str(frontend_build), html=True, check_dir=False),
        name="frontend",
    )
    return app

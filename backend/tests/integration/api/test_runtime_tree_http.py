"""CTR-RUN-003 authenticated transport checks over real HTTP and SQLite."""

from __future__ import annotations

import asyncio
import http.cookiejar
import json
from pathlib import Path

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
)


def test_session_tree_route_is_authenticated_and_validates_bounds(
    tmp_path: Path,
) -> None:
    """M06-API-003: the route exists and rejects invalid bounds at HTTP."""

    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            denied = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/sessions/not-observed/tree",
            )
            assert denied[0] == 401

            jar = http.cookiejar.CookieJar()
            login = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/session",
                body={"password": credential},
                headers={"Origin": origin},
                cookies=jar,
            )
            assert login[0] == 204
            invalid = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/sessions/not-observed/tree?depth_limit=0",
                cookies=jar,
            )
            assert invalid[0] == 422
            assert json.loads(invalid[2])["code"] == "invalid_request_fields"

    asyncio.run(exercise())


def test_session_tree_openapi_publishes_exact_read_policy() -> None:
    """M06-API-003: contract metadata maps one route to GetSessionTreeV1."""

    from agentmonitor.composition.bootstrap import create_iam_schema_application

    schema = create_iam_schema_application().openapi()
    operation = schema["paths"]["/api/v1/sessions/{session_id}/tree"]["get"]
    assert operation["operationId"] == "runtime_get_session_tree_v1"
    assert operation["x-agentmonitor-required-permission"] == "read:telemetry"
    assert operation["x-agentmonitor-application-port"] == "GetSessionTreeV1"
    assert operation["x-agentmonitor-replay-policy"] == "safe_query_repeat"
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/SessionTreeViewV1"
    }
    tree = schema["components"]["schemas"]["SessionTreeViewV1"]
    assert {"included_count", "excluded_count", "unknown_count"} <= set(
        tree["required"]
    )

"""M4-OPS-HTTP: actual migrated IAM and Uvicorn; no constructed health leaves."""

import asyncio
import http.cookiejar
import json
from pathlib import Path

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
)


def test_operations_require_auth_and_report_actual_lifecycle(tmp_path: Path) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            denied = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/operations/liveness",
                headers={"Origin": origin},
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
            result = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/operations/liveness",
                cookies=jar,
            )
            assert result[0] == 200
            payload = json.loads(result[2])
            assert payload["state"] == "healthy"
            assert payload["checked_at"] and payload["correlation_id"]
            assert "components" not in payload

    asyncio.run(exercise())


def test_operations_diagnostics_use_real_schema_and_closed_safe_output(
    tmp_path: Path,
) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
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
            result = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/operations/diagnostics",
                cookies=jar,
            )
            assert result[0] == 200
            payload = json.loads(result[2])
            assert payload["versions"]["schema_version"]["value"] == "v1_0707"
            revision = payload["versions"]["source_revision"]
            assert set(revision) == {"value", "availability", "source"}
            assert revision["source"] == "build_manifest"
            if app.state.build.source_revision is None:
                assert revision == {
                    "value": None,
                    "availability": "unknown",
                    "source": "build_manifest",
                }
            else:
                assert revision["value"] == app.state.build.source_revision
                assert revision["availability"] == "available"
            assert payload["readiness"]["state"] == "ready"
            keys = {item["component_key"] for item in payload["health"]["components"]}
            assert {
                "foundation",
                "configuration",
                "database",
                "identity_access",
                "registry",
            } <= keys
            wire = result[2].decode()
            assert credential not in wire
            assert str(tmp_path) not in wire
            assert str(Path(__file__).resolve().parents[4]) not in wire
            assert '"password"' not in wire and '"email"' not in wire
            assert set(payload) == {
                "versions",
                "health",
                "readiness",
                "configuration_presence",
                "generated_at",
                "valid_until",
                "availability",
                "reason_codes",
                "correlation_id",
            }

    asyncio.run(exercise())

"""M4-CAP-HTTP: real empty installation, authenticated HTTP, no quota fixtures."""

import asyncio
import http.cookiejar
import json
from pathlib import Path

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
)


def test_scope_inventory_reports_actual_empty_registry_and_rejects_bad_filters(
    tmp_path: Path,
) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            denied = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/capacity/scope",
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
                "/api/v1/capacity/scope?scope_kind=global",
                cookies=jar,
            )
            assert result[0] == 200
            payload = json.loads(result[2])
            assert payload["scope_kind"] == "global"
            assert payload["registry_revision"] == 1
            assert payload["registered_account_count"] == 0
            assert payload["eligible_account_count"] == 0
            assert payload["covered_account_count"] == 0
            assert payload["accounts"] == [] and payload["window_groups"] == []
            assert payload["input_observation_ids"] == []
            assert payload["worst_health"] == "unknown"
            cloud_safe = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/capacity/scope/v2?scope_kind=global",
                cookies=jar,
            )
            assert cloud_safe[0] == 200
            cloud_payload = json.loads(cloud_safe[2])
            assert cloud_payload["scope_kind"] == "global"
            assert cloud_payload["registry_revision"] == payload["registry_revision"]
            assert cloud_payload["registered_account_count"] == 0
            assert cloud_payload["accounts"] == []
            assert cloud_payload["window_groups"] == []
            assert cloud_payload["input_observation_ids"] == []
            for query in (
                "scope_kind=global&scope_id=invalid",
                "scope_kind=organization",
                "scope_kind=global&scope_kind=account",
                "extra=true",
            ):
                invalid = await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    "/api/v1/capacity/scope?" + query,
                    cookies=jar,
                )
                assert invalid[0] == 400
            absent = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/accounts/nonexistent/forecasts",
                cookies=jar,
            )
            assert absent[0] == 404

    asyncio.run(exercise())

"""Actual IAM/HTTP guards for retained report discovery; no telemetry seeds."""

import asyncio
import http.cookiejar
import json
import secrets
from pathlib import Path

from backend.tests.integration.api.test_budget_history_http import _query
from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
    _session_cookies,
)


def test_report_discovery_authentication_and_selection_guards(tmp_path: Path) -> None:
    app, credential = _installation(tmp_path)
    route = "/api/v1/budgets/absent/reports?"
    query = _query(account_id="absent")

    async def exercise() -> None:
        async with _running(app) as origin:
            denied = await asyncio.to_thread(_request, origin, "GET", route + query)
            assert denied[0] == 401, "budget_report_discovery_route_missing"
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
            missing = await asyncio.to_thread(
                _request, origin, "GET", route + query, cookies=jar
            )
            assert missing[0] == 404
            assert json.loads(missing[2])["code"] == "registry_subject_not_found"
            for changes, expected in (
                ({"account_id": ""}, 400),
                ({"limit": "201"}, 422),
                ({"period_end": "2026-01-01T00:00:00Z"}, 400),
                ({"as_of": "2026-01-07T00:00:00Z"}, 400),
                ({"period_start": "2026-01-01T00:00:00+01:00"}, 400),
                ({"scope_generation": "1"}, 400),
                ({"cursor": "invalid"}, 400),
            ):
                selection = {"account_id": "absent", **changes}
                result = await asyncio.to_thread(
                    _request, origin, "GET", route + _query(**selection), cookies=jar
                )
                assert result[0] == expected
            duplicate = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                route + query + "&account_id=other",
                cookies=jar,
            )
            assert duplicate[0] == 400
            for scope, expected in (("read:accounts", 403), ("read:telemetry", 404)):
                issued = await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/api-tokens",
                    body={"name": "Report discovery permission", "scopes": [scope]},
                    headers={
                        "Origin": origin,
                        "X-CSRF-Token": _session_cookies(jar)["agentmonitor_csrf"],
                        "Idempotency-Key": secrets.token_urlsafe(24),
                    },
                    cookies=jar,
                )
                assert issued[0] == 201
                guarded = await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    route + query,
                    headers={
                        "Authorization": "Bearer "
                        + json.loads(issued[2])["bearer_credential"]
                    },
                )
                assert guarded[0] == expected

    asyncio.run(exercise())

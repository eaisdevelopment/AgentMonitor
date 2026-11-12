"""Real HTTP/IAM history and compact summaries; no seeded financial telemetry."""

from __future__ import annotations

import asyncio
import http.cookiejar
import json
import secrets
import urllib.parse
from pathlib import Path

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
    _session_cookies,
)


def _query(**changes: str) -> str:
    return urllib.parse.urlencode(
        {
            "period_start": "2026-01-01T00:00:00Z",
            "period_end": "2026-01-08T00:00:00Z",
            "as_of": "2026-01-09T00:00:00Z",
            **changes,
        }
    )


def test_history_route_authentication_missing_selection_and_filter_guards(
    tmp_path: Path,
) -> None:
    app, credential = _installation(tmp_path)
    path = "/api/v1/budgets/absent/history?" + _query(
        account_id="absent", report_id="absent"
    )

    async def exercise() -> None:
        async with _running(app) as origin:
            denied = await asyncio.to_thread(_request, origin, "GET", path)
            assert denied[0] == 401, "budget_history_route_missing"
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
                _request, origin, "GET", path, cookies=jar
            )
            assert missing[0] == 404
            assert json.loads(missing[2])["code"] == "budget_report_not_found"
            for changes, expected in (
                ({"account_id": ""}, 400),
                ({"report_id": ""}, 400),
                ({"period_end": "2026-01-01T00:00:00Z"}, 400),
                ({"as_of": "2026-01-07T00:00:00Z"}, 400),
                ({"period_start": "2026-01-01T00:00:00+01:00"}, 400),
                ({"limit": "201"}, 422),
                ({"limit": "0"}, 422),
                ({"scope_generation": "1"}, 400),
            ):
                selection = {"account_id": "absent", "report_id": "absent", **changes}
                result = await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    "/api/v1/budgets/absent/history?" + _query(**selection),
                    cookies=jar,
                )
                assert result[0] == expected
            duplicate = await asyncio.to_thread(
                _request, origin, "GET", path + "&report_id=other", cookies=jar
            )
            assert duplicate[0] == 400
            invalid_cursor = await asyncio.to_thread(
                _request, origin, "GET", path + "&cursor=invalid", cookies=jar
            )
            assert invalid_cursor[0] == 400
            assert json.loads(invalid_cursor[2])["code"] == "invalid_cursor"
            for scope, expected in (("read:accounts", 403), ("read:telemetry", 404)):
                issued = await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/api-tokens",
                    body={"name": "History read permission", "scopes": [scope]},
                    headers={
                        "Origin": origin,
                        "X-CSRF-Token": _session_cookies(jar)["agentmonitor_csrf"],
                        "Idempotency-Key": secrets.token_urlsafe(24),
                    },
                    cookies=jar,
                )
                assert issued[0] == 201
                for target in (path, "/api/v1/accounts/absent/budgets?" + _query()):
                    guarded = await asyncio.to_thread(
                        _request,
                        origin,
                        "GET",
                        target,
                        headers={
                            "Authorization": "Bearer "
                            + json.loads(issued[2])["bearer_credential"]
                        },
                    )
                    assert guarded[0] == expected

    asyncio.run(exercise())


def test_compact_account_summary_route_requires_authentication(tmp_path: Path) -> None:
    app, credential = _installation(tmp_path)
    path = "/api/v1/accounts/absent/budgets?" + _query()

    async def exercise() -> None:
        async with _running(app) as origin:
            denied = await asyncio.to_thread(_request, origin, "GET", path)
            assert denied[0] == 401, "budget_summary_route_missing"
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
                _request, origin, "GET", path, cookies=jar
            )
            assert missing[0] == 404
            assert json.loads(missing[2])["code"] == "registry_subject_not_found"

    asyncio.run(exercise())

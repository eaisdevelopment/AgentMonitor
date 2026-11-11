"""M7 T010/T012 Overview over actual IAM, HTTP and empty migrated SQLite."""

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


def _overview_path(**overrides: str) -> str:
    return "/api/v1/budgets?" + urllib.parse.urlencode(
        {
            "period_start": "2026-01-01T00:00:00Z",
            "period_end": "2026-01-08T00:00:00Z",
            "as_of": "2026-01-09T00:00:00Z",
            **overrides,
        }
    )


def _selected_path(**overrides: str) -> str:
    return "/api/v1/budgets/not-enrolled?" + urllib.parse.urlencode(
        {
            "account_id": "not-enrolled",
            "report_id": "not-retained",
            "period_start": "2026-01-01T00:00:00Z",
            "period_end": "2026-01-08T00:00:00Z",
            "as_of": "2026-01-09T00:00:00Z",
            **overrides,
        }
    )


def test_selected_budget_report_requires_authenticated_exact_selection(
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
            missing = await asyncio.to_thread(
                _request, origin, "GET", _selected_path(), cookies=jar
            )
            assert missing[0] == 404
            assert json.loads(missing[2]).get("code") == "budget_report_not_found"
            denied = await asyncio.to_thread(_request, origin, "GET", _selected_path())
            assert denied[0] == 401
            for path, expected in (
                ("/api/v1/budgets/not-enrolled", 422),
                (_selected_path(account_id=""), 400),
                (_selected_path(report_id=""), 400),
                (_selected_path(period_end="2026-01-01T00:00:00Z"), 400),
                (_selected_path(as_of="2026-01-07T00:00:00Z"), 400),
                (_selected_path(period_start="2026-01-01T00:00:00+01:00"), 400),
                (_selected_path(scope_generation="1"), 400),
                (_selected_path() + "&report_id=another-report", 400),
            ):
                invalid = await asyncio.to_thread(
                    _request, origin, "GET", path, cookies=jar
                )
                assert invalid[0] == expected
                assert json.loads(invalid[2])["code"] == (
                    "invalid_request_fields" if expected == 422 else "invalid_filter"
                )
            for scope, expected in (("read:accounts", 403), ("read:telemetry", 404)):
                issued = await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/api-tokens",
                    body={"name": "Selected report permission", "scopes": [scope]},
                    headers={
                        "Origin": origin,
                        "X-CSRF-Token": _session_cookies(jar)["agentmonitor_csrf"],
                        "Idempotency-Key": secrets.token_urlsafe(24),
                    },
                    cookies=jar,
                )
                assert issued[0] == 201
                selected = await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    _selected_path(),
                    headers={
                        "Authorization": "Bearer "
                        + json.loads(issued[2])["bearer_credential"]
                    },
                )
                assert selected[0] == expected

    asyncio.run(exercise())


def test_overview_authentication_empty_result_and_filter_guards(tmp_path: Path) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            denied = await asyncio.to_thread(_request, origin, "GET", _overview_path())
            assert denied[0] == 401, (
                f"Overview authentication returned HTTP {denied[0]}"
            )
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
            for path in (
                _overview_path(),
                _overview_path(organization_ids="", include_ungrouped="false"),
                _overview_path(provider_key="ollama", limit="200"),
            ):
                response = await asyncio.to_thread(
                    _request, origin, "GET", path, cookies=jar
                )
                assert response[0] == 200
                payload = json.loads(response[2])
                assert payload["items"] == []
                assert payload["summaries"] == []
                assert payload["inventory_count"] == 0
                assert payload["subscription_account_ids"] == []
                assert payload["summary_reason"] is None
                assert payload["period"] == {
                    "start": "2026-01-01T00:00:00Z",
                    "end": "2026-01-08T00:00:00Z",
                }
                assert payload["as_of"] == "2026-01-09T00:00:00Z"
                assert payload["availability"]["state"] == "available"
                assert payload["page"]["has_more"] is False
                assert payload["page"]["next_cursor"] is None
                assert "no-store" in response[1].get("Cache-Control", "")
                assert "ETag" not in response[1]
            for path, expected in (
                ("/api/v1/budgets", 422),
                (_overview_path(limit="0"), 422),
                (_overview_path(limit="201"), 422),
                (_overview_path(provider_key="unknown"), 400),
                (_overview_path(include_ungrouped="maybe"), 422),
                (_overview_path(organization_ids="one,one"), 400),
                (_overview_path(period_end="2026-01-09T00:00:00Z"), 400),
                (_overview_path(period_start="2026-01-01T00:00:00+01:00"), 400),
                (_overview_path(period_start="2026-01-01T00:00:00"), 400),
                (_overview_path(as_of="2026-01-07T00:00:00Z"), 400),
                (_overview_path(scope_generation="1"), 400),
                (_overview_path() + "&limit=1&limit=2", 400),
            ):
                invalid = await asyncio.to_thread(
                    _request, origin, "GET", path, cookies=jar
                )
                assert invalid[0] == expected
                assert json.loads(invalid[2])["code"] == (
                    "invalid_request_fields" if expected == 422 else "invalid_filter"
                )
            cursor = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                _overview_path(cursor="invalid-cursor"),
                cookies=jar,
            )
            assert cursor[0] == 400
            assert json.loads(cursor[2])["code"] == "invalid_cursor"
            headers = {
                "Origin": origin,
                "X-CSRF-Token": _session_cookies(jar)["agentmonitor_csrf"],
            }
            for scope, expected in (("read:accounts", 403), ("read:telemetry", 200)):
                issued = await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/api-tokens",
                    body={"name": "Overview permission", "scopes": [scope]},
                    headers={**headers, "Idempotency-Key": secrets.token_urlsafe(24)},
                    cookies=jar,
                )
                assert issued[0] == 201
                checked = await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    _overview_path(),
                    headers={
                        "Authorization": "Bearer "
                        + json.loads(issued[2])["bearer_credential"]
                    },
                )
                assert checked[0] == expected

    asyncio.run(exercise())


def test_overview_cursor_is_bound_to_filters_and_preserves_full_inventory(
    tmp_path: Path,
) -> None:
    """Production account commands create local metadata, never telemetry."""
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
            for name in ("Overview A", "Overview B"):
                created = await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/accounts",
                    body={
                        "provider_key": "claude",
                        "friendly_name": name,
                        "organization_id": None,
                        "initial_connection_purpose": "api",
                    },
                    headers={
                        "Origin": origin,
                        "X-CSRF-Token": _session_cookies(jar)["agentmonitor_csrf"],
                        "Idempotency-Key": secrets.token_urlsafe(24),
                    },
                    cookies=jar,
                )
                assert created[0] == 201
            first = await asyncio.to_thread(
                _request, origin, "GET", _overview_path(limit="1"), cookies=jar
            )
            assert first[0] == 200
            payload = json.loads(first[2])
            assert len(payload["items"]) == 1
            assert payload["inventory_count"] == 2
            assert payload["subscription_account_ids"] == []
            assert payload["summaries"] == []
            assert payload["page"]["has_more"] is True
            cursor = payload["page"]["next_cursor"]
            assert isinstance(cursor, str) and cursor
            second = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                _overview_path(limit="1", cursor=cursor),
                cookies=jar,
            )
            assert second[0] == 200
            following = json.loads(second[2])
            assert len(following["items"]) == 1
            assert following["inventory_count"] == 2
            assert following["items"][0]["row_id"] != payload["items"][0]["row_id"]
            assert following["page"]["has_more"] is False
            assert following["summaries"] == payload["summaries"]
            assert following["exclusions"] == payload["exclusions"]
            for changes in (
                {"provider_key": "ollama"},
                {"organization_ids": ""},
                {"include_ungrouped": "true"},
                {"as_of": "2026-01-10T00:00:00Z"},
                {
                    "period_start": "2026-01-02T00:00:00Z",
                    "period_end": "2026-01-09T00:00:00Z",
                },
            ):
                changed = await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    _overview_path(limit="1", cursor=cursor, **changes),
                    cookies=jar,
                )
                assert changed[0] == 400
                assert json.loads(changed[2])["code"] == "cursor_query_mismatch"
            none_selected = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                _overview_path(organization_ids="", include_ungrouped="false"),
                cookies=jar,
            )
            assert none_selected[0] == 200
            assert json.loads(none_selected[2])["inventory_count"] == 0
            assert json.loads(none_selected[2])["items"] == []

    asyncio.run(exercise())

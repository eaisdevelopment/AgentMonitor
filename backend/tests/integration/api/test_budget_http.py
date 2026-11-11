"""M7-HTTP-001: current financial reads over real IAM, HTTP and SQLite."""

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


def _current_path(account_id: str = "not-enrolled", **overrides: str) -> str:
    parameters = {
        "period_start": "2026-01-01T00:00:00Z",
        "period_end": "2026-01-08T00:00:00Z",
        "as_of": "2026-01-09T00:00:00Z",
        **overrides,
    }
    return f"/api/v1/accounts/{account_id}/api-capacity?" + urllib.parse.urlencode(
        parameters
    )


def test_current_budget_authentication_and_filter_boundary(tmp_path: Path) -> None:
    """Missing accounts stay private; callers cannot choose a scope epoch."""
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            denied = await asyncio.to_thread(_request, origin, "GET", _current_path())
            assert denied[0] == 401, (
                "The current budget read must authenticate before account lookup; "
                f"received HTTP {denied[0]}"
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
            missing = await asyncio.to_thread(
                _request, origin, "GET", _current_path(), cookies=jar
            )
            assert missing[0] == 404
            assert json.loads(missing[2])["code"] == "registry_subject_not_found"
            for path in (
                _current_path(scope_generation="1"),
                _current_path(period_start="2026-01-08T00:00:00Z"),
                _current_path(period_start="2026-01-10T00:00:00Z"),
                _current_path(period_start="2026-01-01T00:00:00+01:00"),
                _current_path(period_start="2026-01-01T00:00:00"),
                _current_path() + "&as_of=2026-01-09T00%3A00%3A00Z",
            ):
                invalid = await asyncio.to_thread(
                    _request, origin, "GET", path, cookies=jar
                )
                assert invalid[0] == 400
                assert json.loads(invalid[2])["code"] == "invalid_filter"

    asyncio.run(exercise())


def test_current_budget_configured_empty_account_and_permissions(
    tmp_path: Path,
) -> None:
    """Actual metadata has no reported money until a genuine report is committed."""
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
            headers = {
                "Origin": origin,
                "X-CSRF-Token": _session_cookies(jar)["agentmonitor_csrf"],
                "Idempotency-Key": secrets.token_urlsafe(24),
            }
            created = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/accounts",
                body={
                    "provider_key": "claude",
                    "friendly_name": "HTTP budget " + secrets.token_hex(8),
                    "organization_id": None,
                    "initial_connection_purpose": "api",
                },
                headers=headers,
                cookies=jar,
            )
            assert created[0] == 201
            account_id = json.loads(created[2])["account_id"]
            empty = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                _current_path(account_id),
                cookies=jar,
            )
            assert empty[0] == 200, f"Current financial query returned HTTP {empty[0]}"
            empty_payload = json.loads(empty[2])
            assert empty_payload["resources"] == []
            assert empty_payload["availability"]["state"] == "available"
            assert (
                empty_payload["availability"]["reason_code"] == "billing_not_configured"
            )
            assert "funds" in empty_payload, (
                "Current financial HTTP must expose the independent funds read "
                "even before a billing connection exists"
            )
            funds = empty_payload["funds"]
            assert funds["account_id"] == account_id
            assert funds["as_of"] == empty_payload["as_of"]
            assert funds["availability"]["state"] == "unavailable"
            assert funds["availability"]["reason_code"] == "funds_source_unavailable"
            assert funds["availability"]["as_of"] == funds["as_of"]
            assert funds["components"] == []
            assert "currency" not in funds

            connection = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                f"/api/v1/accounts/{account_id}/billing-connections",
                body={"scope_id": None},
                headers={
                    **headers,
                    "If-Match": created[1]["ETag"],
                    "Idempotency-Key": secrets.token_urlsafe(24),
                },
                cookies=jar,
            )
            assert connection[0] == 201
            configured = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                _current_path(account_id),
                cookies=jar,
            )
            assert configured[0] == 200
            payload = json.loads(configured[2])
            assert payload["account_id"] == account_id
            assert payload["period"] == {
                "start": "2026-01-01T00:00:00Z",
                "end": "2026-01-08T00:00:00Z",
            }
            assert payload["as_of"] == "2026-01-09T00:00:00Z"
            assert len(payload["resources"]) == 1
            resource = payload["resources"][0]
            assert resource["connection"] == json.loads(connection[2])
            assert resource["reports"] == []
            assert resource["reported_spend"] == []
            assert resource["report_availability"]["state"] == "unavailable"
            assert resource["latest_collection"] is None
            configured_funds = payload["funds"]
            assert configured_funds["account_id"] == account_id
            assert configured_funds["as_of"] == payload["as_of"]
            assert configured_funds["availability"] == funds["availability"]
            assert configured_funds["components"] == []
            assert "currency" not in configured_funds
            assert "no-store" in configured[1].get("Cache-Control", "")
            assert "ETag" not in configured[1]
            assert "binding_id" not in configured[2].decode()
            assert "credential" not in configured[2].decode()
            for scope, expected in (("read:accounts", 403), ("read:telemetry", 200)):
                issued = await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/api-tokens",
                    body={"name": "Budget HTTP permission", "scopes": [scope]},
                    headers={**headers, "Idempotency-Key": secrets.token_urlsafe(24)},
                    cookies=jar,
                )
                assert issued[0] == 201
                checked = await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    _current_path(account_id),
                    headers={
                        "Authorization": "Bearer "
                        + json.loads(issued[2])["bearer_credential"]
                    },
                )
                assert checked[0] == expected
            runs = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                f"/api/v1/collection-runs?account_id={account_id}",
                cookies=jar,
            )
            assert runs[0] == 200
            assert json.loads(runs[2])["items"] == []

    asyncio.run(exercise())


def test_report_projection_is_pure_exact_and_excludes_custody() -> None:
    """Constructed values stay in this pure mapper; never enter HTTP or storage."""
    from agentmonitor.api.v1.routers.budgets import report_wire

    from backend.tests.capacity.pure.test_budget_report_selection import _report

    report = _report(1, "9007199254740993.123456789")
    projected = report_wire(report).model_dump(mode="json")
    assert projected["cost_buckets"][0]["amount"] == {
        "coefficient": "9007199254740993123456789",
        "scale": 9,
        "currency": "USD",
    }
    assert projected["report_id"] == report.report_id.value
    assert projected["source_id"] == report.report.source_id
    assert projected["scope_generation"] == report.report.scope_generation
    assert projected["source_data_through"] == "2026-11-02T00:00:00Z"
    assert "binding_id" not in projected
    assert "binding_generation" not in projected

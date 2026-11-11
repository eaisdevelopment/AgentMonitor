"""M7-REG-001: API billing intent over real IAM, HTTP and file SQLite."""

from __future__ import annotations

import asyncio
import http.cookiejar
import json
import secrets
from pathlib import Path

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
    _session_cookies,
)


def test_api_account_creation_exposes_safe_billing_status(tmp_path: Path) -> None:
    """Owner metadata can select API setup without claiming provider access."""
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
            created = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/accounts",
                body={
                    "provider_key": "claude",
                    "friendly_name": "Billing account " + secrets.token_urlsafe(8),
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
            assert created[0] == 201, (
                f"API-purpose account creation must succeed; received HTTP {created[0]}"
            )
            account = json.loads(created[2])
            account_id = account["account_id"]
            assert isinstance(account_id, str) and account_id
            assert account["initial_connection_purpose"] == "api"
            assert account["monitoring_preference"] == "disabled"
            assert account["is_effective_monitoring_enabled"] is False
            assert account["identity_state"] == "unresolved"
            assert created[1]["Location"] == f"/api/v1/accounts/{account_id}"

            status = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                f"/api/v1/accounts/{account_id}/billing-connections",
                cookies=jar,
            )
            assert status[0] == 200, (
                "The created account must expose safe billing setup status; "
                f"received HTTP {status[0]}"
            )
            payload = json.loads(status[2])
            assert isinstance(payload, dict)
            assert payload["account_id"] == account_id
            assert "no-store" in status[1].get("Cache-Control", "")
            assert payload["connections"] == []
            assert payload["can_add_connection"] is True
            assert payload["account_lifecycle"] == "pending"

            unauthenticated = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                f"/api/v1/accounts/{account_id}/billing-connections",
            )
            assert unauthenticated[0] == 401
            missing_account = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                f"/api/v1/accounts/{secrets.token_urlsafe(24)}/billing-connections",
                cookies=jar,
            )
            assert missing_account[0] == 404

            enrollment_headers = {
                "Origin": origin,
                "X-CSRF-Token": _session_cookies(jar)["agentmonitor_csrf"],
                "Idempotency-Key": secrets.token_urlsafe(24),
                "If-Match": created[1]["ETag"],
            }
            for omit, expected_status in (
                ("X-CSRF-Token", 403),
                ("If-Match", 428),
                ("Idempotency-Key", 400),
            ):
                rejected = await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    f"/api/v1/accounts/{account_id}/billing-connections",
                    body={"scope_id": None},
                    headers={k: v for k, v in enrollment_headers.items() if k != omit},
                    cookies=jar,
                )
                assert rejected[0] == expected_status
            secret_field = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                f"/api/v1/accounts/{account_id}/billing-connections",
                body={"scope_id": None, "api_key": None},
                headers=enrollment_headers,
                cookies=jar,
            )
            assert secret_field[0] == 422

            connection = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                f"/api/v1/accounts/{account_id}/billing-connections",
                body={"scope_id": None},
                headers=enrollment_headers,
                cookies=jar,
            )
            assert connection[0] == 201
            connected = json.loads(connection[2])
            assert connected["account_id"] == account_id
            assert connected["provider_key"] == "claude"
            assert connected["scope_evidence"] == "unresolved"
            assert connected["scope_generation"] == 1
            assert connected["monitoring_preference"] == "disabled"
            assert connected["lifecycle"] == "pending"
            assert connected["resource_id"]
            replay = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                f"/api/v1/accounts/{account_id}/billing-connections",
                body={"scope_id": None},
                headers=enrollment_headers,
                cookies=jar,
            )
            assert replay[0] == 201
            assert json.loads(replay[2]) == connected
            conflict = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                f"/api/v1/accounts/{account_id}/billing-connections",
                body={"scope_id": "owner-asserted-" + secrets.token_hex(8)},
                headers=enrollment_headers,
                cookies=jar,
            )
            assert conflict[0] == 409
            assert json.loads(conflict[2])["code"] == "registry_idempotency_conflict"
            listed = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                f"/api/v1/accounts/{account_id}/billing-connections",
                cookies=jar,
            )
            assert listed[0] == 200
            assert json.loads(listed[2])["connections"] == [connected]
            assert json.loads(listed[2])["can_add_connection"] is False
            unchanged = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                f"/api/v1/accounts/{account_id}",
                cookies=jar,
            )
            assert unchanged[0] == 200
            assert json.loads(unchanged[2])["identity_state"] == "unresolved"
            assert json.loads(unchanged[2])["monitoring_preference"] == "disabled"

    asyncio.run(exercise())


def test_account_creation_rejects_invalid_purpose_and_unknown_fields(
    tmp_path: Path,
) -> None:
    """The enrollment boundary rejects extra fields without credential input."""
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
            for rejected_fields in (
                {"initial_connection_purpose": "unsupported-purpose"},
                {"unrecognized_field": None},
                {"api_key": None},
            ):
                rejected = await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/accounts",
                    body={
                        "provider_key": "claude",
                        "friendly_name": "Billing account " + secrets.token_urlsafe(8),
                        "organization_id": None,
                        **rejected_fields,
                    },
                    headers={
                        "Origin": origin,
                        "X-CSRF-Token": _session_cookies(jar)["agentmonitor_csrf"],
                        "Idempotency-Key": secrets.token_urlsafe(24),
                    },
                    cookies=jar,
                )
                assert rejected[0] == 422
                problem = json.loads(rejected[2])
                assert problem["status"] == 422
                assert "unsupported-purpose" not in rejected[2].decode("utf-8")
            accounts = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/accounts", cookies=jar
            )
            assert accounts[0] == 200
            assert json.loads(accounts[2])["items"] == []

    asyncio.run(exercise())

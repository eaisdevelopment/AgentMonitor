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
            assert account.get("has_active_subscription_resource") is False
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
            # Account versions fence mutations, not this composite status view.
            assert "ETag" not in status[1]
            assert payload["connections"] == []
            assert payload["credential_status"] is None
            assert payload["local_setup"] is None
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
            assert json.loads(listed[2])["credential_status"] == {
                "state": "missing",
                "active_generation": None,
                "pending_generation": None,
                "cleanup_required": False,
            }
            setup = json.loads(listed[2])["local_setup"]
            assert setup["host_label"]
            assert (
                "agentmonitor.composition.billing_credential_operator"
                in setup["command"]
            )
            assert "--account-id=" + account_id in setup["command"]
            assert "--resource-id=" + connected["resource_id"] in setup["command"]
            assert str(tmp_path) in setup["command"]
            assert "agentmonitor-dashboard.service" in setup["command"]
            assert "/worktrees/" not in setup["command"]
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

            scope_path = (
                f"/api/v1/accounts/{account_id}/billing-connections/"
                f"{connected['resource_id']}/scope"
            )
            scope_headers = {
                "Origin": origin,
                "X-CSRF-Token": _session_cookies(jar)["agentmonitor_csrf"],
                "If-Match": connection[1]["ETag"],
                "Idempotency-Key": secrets.token_urlsafe(24),
            }
            scope_body = {
                "scope_id": "owner-asserted-updated-scope",
                "expected_account_version": account["record_version"],
                "expected_scope_generation": connected["scope_generation"],
            }
            changed = await asyncio.to_thread(
                _request,
                origin,
                "PUT",
                scope_path,
                body=scope_body,
                headers=scope_headers,
                cookies=jar,
            )
            assert changed[0] == 200, "billing_scope_edit_must_be_available"
            updated_scope = json.loads(changed[2])
            assert updated_scope["scope_id"] == scope_body["scope_id"]
            assert updated_scope["scope_generation"] == 2
            assert updated_scope["scope_evidence"] == "owner_asserted"
            assert updated_scope["monitoring_preference"] == "disabled"
            assert updated_scope["lifecycle"] == "pending"
            for omit, expected_status in (
                ("X-CSRF-Token", 403),
                ("If-Match", 428),
                ("Idempotency-Key", 400),
            ):
                denied = await asyncio.to_thread(
                    _request,
                    origin,
                    "PUT",
                    scope_path,
                    body=scope_body,
                    headers={k: v for k, v in scope_headers.items() if k != omit},
                    cookies=jar,
                )
                assert denied[0] == expected_status
            repeated = await asyncio.to_thread(
                _request,
                origin,
                "PUT",
                scope_path,
                body=scope_body,
                headers=scope_headers,
                cookies=jar,
            )
            assert repeated[0] == 200 and json.loads(repeated[2]) == updated_scope
            stale = await asyncio.to_thread(
                _request,
                origin,
                "PUT",
                scope_path,
                body=scope_body,
                headers={**scope_headers, "Idempotency-Key": secrets.token_urlsafe(24)},
                cookies=jar,
            )
            assert stale[0] == 412
            fresh_headers = {
                **scope_headers,
                "If-Match": changed[1]["ETag"],
                "Idempotency-Key": secrets.token_urlsafe(24),
            }
            no_op = await asyncio.to_thread(
                _request,
                origin,
                "PUT",
                scope_path,
                body={**scope_body, "expected_scope_generation": 2},
                headers=fresh_headers,
                cookies=jar,
            )
            assert no_op[0] == 200 and json.loads(no_op[2]) == updated_scope
            omitted_scope = await asyncio.to_thread(
                _request,
                origin,
                "PUT",
                scope_path,
                body={
                    "expected_account_version": account["record_version"],
                    "expected_scope_generation": 2,
                },
                headers={**fresh_headers, "Idempotency-Key": secrets.token_urlsafe(24)},
                cookies=jar,
            )
            assert omitted_scope[0] == 422, "scope_edit_requires_explicit_scope_or_null"
            invalid = await asyncio.to_thread(
                _request,
                origin,
                "PUT",
                scope_path,
                body={**scope_body, "api_key": None},
                headers=fresh_headers,
                cookies=jar,
            )
            assert invalid[0] == 422
            cleared = await asyncio.to_thread(
                _request,
                origin,
                "PUT",
                scope_path,
                body={
                    **scope_body,
                    "scope_id": None,
                    "expected_scope_generation": 2,
                },
                headers={**fresh_headers, "Idempotency-Key": secrets.token_urlsafe(24)},
                cookies=jar,
            )
            assert cleared[0] == 200
            unresolved = json.loads(cleared[2])
            assert unresolved["scope_id"] is None
            assert unresolved["scope_evidence"] == "unresolved"
            assert unresolved["scope_generation"] == 3
            stale_replay = await asyncio.to_thread(
                _request,
                origin,
                "PUT",
                scope_path,
                body=scope_body,
                headers=scope_headers,
                cookies=jar,
            )
            assert stale_replay[0] == 409
            assert json.loads(stale_replay[2])["code"] == "registry_replay_stale"

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

"""Billing reconnect over real HTTP, IAM and SQLite; no provider data invented."""

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


def test_billing_reconnect_http_guards_and_restored_setup(tmp_path: Path) -> None:
    """M7-HTTP-RECONNECT-001: explicit action, same source, no access proof."""
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            endpoint = (
                "/api/v1/accounts/unselected/billing-connections/unselected/reconnect"
            )
            unauthenticated = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                endpoint,
                body={"expected_account_version": 1, "expected_scope_generation": 1},
                headers={"Origin": origin},
            )
            assert unauthenticated[0] == 401, "billing_reconnect_route_missing"
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
            }
            created = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/accounts",
                body={
                    "provider_key": "codex",
                    "friendly_name": "Reconnect " + secrets.token_urlsafe(8),
                    "organization_id": None,
                    "initial_connection_purpose": "api",
                },
                headers={**headers, "Idempotency-Key": secrets.token_urlsafe(24)},
                cookies=jar,
            )
            assert created[0] == 201
            account = json.loads(created[2])
            path = "/api/v1/accounts/" + account["account_id"]
            creation = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                path + "/billing-connections",
                body={"scope_id": None},
                headers={
                    **headers,
                    "If-Match": created[1]["ETag"],
                    "Idempotency-Key": secrets.token_urlsafe(24),
                },
                cookies=jar,
            )
            assert creation[0] == 201
            original = json.loads(creation[2])
            endpoint = (
                path + "/billing-connections/" + original["resource_id"] + "/reconnect"
            )
            archived = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                path + "/archivals",
                body={},
                headers={
                    **headers,
                    "If-Match": created[1]["ETag"],
                    "Idempotency-Key": secrets.token_urlsafe(24),
                },
                cookies=jar,
            )
            assert archived[0] == 200
            restored = await asyncio.to_thread(
                _request,
                origin,
                "DELETE",
                path + "/archival",
                headers={**headers, "If-Match": archived[1]["ETag"]},
                cookies=jar,
            )
            assert restored[0] == 200
            status = await asyncio.to_thread(
                _request, origin, "GET", path + "/billing-connections", cookies=jar
            )
            assert status[0] == 200
            before = json.loads(status[2])
            disconnected = before["connections"][0]
            assert disconnected["lifecycle"] == "disconnected"
            assert before["local_setup"] is None
            body = {
                "expected_account_version": before["account_record_version"],
                "expected_scope_generation": disconnected["scope_generation"],
            }
            mutation = {
                **headers,
                "If-Match": (
                    f'"{disconnected["resource_id"]}.{disconnected["record_version"]}"'
                ),
                "Idempotency-Key": secrets.token_urlsafe(24),
            }
            for omitted, expected in (
                ("X-CSRF-Token", 403),
                ("If-Match", 428),
                ("Idempotency-Key", 400),
            ):
                denied = await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    endpoint,
                    body=body,
                    headers={k: v for k, v in mutation.items() if k != omitted},
                    cookies=jar,
                )
                assert denied[0] == expected
            for suffix, extra, expected in (
                ("?unexpected=yes", {}, 400),
                ("", {"api_key": None}, 422),
                ("", {"expected_account_version": 1}, 412),
            ):
                denied = await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    endpoint + suffix,
                    body={**body, **extra},
                    headers=mutation,
                    cookies=jar,
                )
                assert denied[0] == expected
            reconnected = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                endpoint,
                body=body,
                headers=mutation,
                cookies=jar,
            )
            assert reconnected[0] == 200
            result = json.loads(reconnected[2])
            assert result["resource_id"] == original["resource_id"]
            assert result["scope_id"] == original["scope_id"]
            assert result["scope_generation"] == original["scope_generation"]
            assert result["monitoring_preference"] == "disabled"
            assert result["lifecycle"] == "pending"
            assert result["record_version"] == disconnected["record_version"] + 1
            assert "no-store" in reconnected[1]["Cache-Control"]
            replay = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                endpoint,
                body=body,
                headers=mutation,
                cookies=jar,
            )
            assert replay[0] == 200 and json.loads(replay[2]) == result
            final = await asyncio.to_thread(
                _request, origin, "GET", path + "/billing-connections", cookies=jar
            )
            assert final[0] == 200
            current = json.loads(final[2])
            assert current["credential_status"]["state"] == "missing"
            assert current["credential_status"]["active_generation"] is None
            assert current["account_record_version"] == before["account_record_version"]
            assert current["connections"] == [result]

    asyncio.run(exercise())

"""Codex reaches the provider-neutral dashboard through the real HTTP stack."""

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


def test_codex_service_shutdown_deadline_covers_provider_operation_and_cleanup(
    tmp_path: Path,
) -> None:
    """M5-CDX-COL-013: shutdown can drain a 30s call plus owned-child cleanup."""
    app, _ = _installation(tmp_path)

    assert app.state.lifecycle.hooks.shutdown_timeout_seconds > 34


def test_codex_manifest_and_pending_account_are_available_over_http(
    tmp_path: Path,
) -> None:
    """M5-CDX-API-001/002: bootstrap registers Codex in the V1 API."""
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            jar = http.cookiejar.CookieJar()
            assert (
                await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/session",
                    body={"password": credential},
                    headers={"Origin": origin},
                    cookies=jar,
                )
            )[0] == 204
            capabilities = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/providers/codex/capabilities",
                cookies=jar,
            )
            assert capabilities[0] == 200
            manifest = json.loads(capabilities[2])
            assert manifest["provider_key"] == "codex"
            assert manifest["adapter_version"] == "1.0.1"

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
                    "provider_key": "codex",
                    "friendly_name": "Owner selected Codex",
                    "organization_id": None,
                },
                headers=headers,
                cookies=jar,
            )
            assert created[0] == 201
            account = json.loads(created[2])
            assert account["provider_key"] == "codex"
            connection = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/accounts/" + account["account_id"] + "/connection",
                cookies=jar,
            )
            assert connection[0] == 200
            connection_view = json.loads(connection[2])
            assert connection_view["state"] == "idle"
            assert connection_view["can_connect"] is True
            identity = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/accounts/" + account["account_id"] + "/provider-identity",
                cookies=jar,
            )
            assert identity[0] == 200
            identity_view = json.loads(identity[2])
            assert identity_view["state"] == "unresolved"
            assert identity_view["provider_key"] == "codex"
            assert (
                identity_view["identity_source_id"]
                == "codex.app-server.account-read.v2"
            )
            assert identity_view["profile_protection"] == "unknown"

            legacy_identity = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/accounts/" + account["account_id"] + "/observed-identity",
                cookies=jar,
            )
            assert legacy_identity[0] == 409
            assert (
                json.loads(legacy_identity[2])["code"]
                == "provider_identity_legacy_unavailable"
            )

    asyncio.run(exercise())

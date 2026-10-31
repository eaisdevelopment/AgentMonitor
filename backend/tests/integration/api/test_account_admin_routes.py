"""ST-FLEET-001 pending account administration over real HTTP and SQLite."""

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


def test_owner_registers_pending_account(tmp_path: Path) -> None:
    """A real admin record is inert until separately verified provider identity."""
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
            created_org = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/organizations",
                body={"name": "Org1 - SDK"},
                headers=headers,
                cookies=jar,
            )
            assert created_org[0] == 201
            organization_id = json.loads(created_org[2])["organization_id"]
            account_name = "Account " + secrets.token_urlsafe(8)
            account_headers = {**headers, "Idempotency-Key": secrets.token_urlsafe(24)}
            body = {
                "provider_key": "claude",
                "friendly_name": account_name,
                "organization_id": organization_id,
            }
            created = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/accounts",
                body=body,
                headers=account_headers,
                cookies=jar,
            )
            assert created[0] == 201, json.loads(created[2])["code"]
            account = json.loads(created[2])
            assert account["friendly_name"] == account_name
            assert account["organization_id"] == organization_id
            assert account["lifecycle"] == "pending"
            assert account["identity_state"] == "unresolved"
            assert account["monitoring_preference"] == "disabled"
            assert account["is_effective_monitoring_enabled"] is False
            monitoring_path = f"/api/v1/accounts/{account['account_id']}/monitoring"
            refused = await asyncio.to_thread(
                _request,
                origin,
                "PUT",
                monitoring_path,
                body={"monitoring_preference": "enabled"},
                headers={**headers, "If-Match": created[1]["ETag"]},
                cookies=jar,
            )
            assert refused[0] == 409
            assert json.loads(refused[2])["code"] == "registry_monitoring_not_eligible"
            unchanged = await asyncio.to_thread(
                _request,
                origin,
                "PUT",
                monitoring_path,
                body={"monitoring_preference": "disabled"},
                headers={**headers, "If-Match": created[1]["ETag"]},
                cookies=jar,
            )
            assert unchanged[0] == 200
            assert json.loads(unchanged[2])["record_version"] == 1
            replay = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/accounts",
                body=body,
                headers=account_headers,
                cookies=jar,
            )
            assert replay[0] == 201
            assert json.loads(replay[2])["account_id"] == account["account_id"]
            listed = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/accounts",
                cookies=jar,
            )
            assert listed[0] == 200
            assert [item["account_id"] for item in json.loads(listed[2])["items"]] == [
                account["account_id"]
            ]

    asyncio.run(exercise())


def test_owner_edits_and_archives_pending_account(tmp_path: Path) -> None:
    """Account metadata CRUD uses optimistic versions and keeps identity inert."""
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
            base_headers = {
                "Origin": origin,
                "X-CSRF-Token": _session_cookies(jar)["agentmonitor_csrf"],
            }

            def creation_headers() -> dict[str, str]:
                return {**base_headers, "Idempotency-Key": secrets.token_urlsafe(24)}

            first_org = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/organizations",
                body={"name": "Org1 - SDK"},
                headers=creation_headers(),
                cookies=jar,
            )
            second_org = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/organizations",
                body={"name": "Org2 - EAIS"},
                headers=creation_headers(),
                cookies=jar,
            )
            assert first_org[0] == second_org[0] == 201
            first_id = json.loads(first_org[2])["organization_id"]
            second_id = json.loads(second_org[2])["organization_id"]
            created = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/accounts",
                body={
                    "provider_key": "claude",
                    "friendly_name": "Account " + secrets.token_urlsafe(8),
                    "organization_id": first_id,
                },
                headers=creation_headers(),
                cookies=jar,
            )
            assert created[0] == 201
            account_id = json.loads(created[2])["account_id"]
            path = f"/api/v1/accounts/{account_id}"
            stale_etag = created[1]["ETag"]
            renamed = await asyncio.to_thread(
                _request,
                origin,
                "PATCH",
                path,
                body={"friendly_name": "Renamed " + secrets.token_urlsafe(8)},
                headers={**base_headers, "If-Match": stale_etag},
                cookies=jar,
            )
            assert renamed[0] == 200
            assert json.loads(renamed[2])["record_version"] == 2
            stale = await asyncio.to_thread(
                _request,
                origin,
                "PUT",
                path + "/organization",
                body={"organization_id": second_id},
                headers={**base_headers, "If-Match": stale_etag},
                cookies=jar,
            )
            assert stale[0] == 412
            moved = await asyncio.to_thread(
                _request,
                origin,
                "PUT",
                path + "/organization",
                body={"organization_id": second_id},
                headers={**base_headers, "If-Match": renamed[1]["ETag"]},
                cookies=jar,
            )
            assert moved[0] == 200
            assert json.loads(moved[2])["organization_id"] == second_id
            archived = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                path + "/archivals",
                body={},
                headers={
                    **creation_headers(),
                    "If-Match": moved[1]["ETag"],
                },
                cookies=jar,
            )
            assert archived[0] == 200
            assert json.loads(archived[2])["lifecycle"] == "archived"
            restored = await asyncio.to_thread(
                _request,
                origin,
                "DELETE",
                path + "/archival",
                headers={**base_headers, "If-Match": archived[1]["ETag"]},
                cookies=jar,
            )
            assert restored[0] == 200
            restored_account = json.loads(restored[2])
            assert restored_account["lifecycle"] == "pending"
            assert restored_account["is_effective_monitoring_enabled"] is False
            fetched = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                path,
                cookies=jar,
            )
            assert fetched[0] == 200
            assert json.loads(fetched[2])["record_version"] == 5

    asyncio.run(exercise())

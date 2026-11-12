"""M7-REG/HTTP: owner pool metadata over actual IAM, HTTP and SQLite.

These commands create isolated owner configuration, not provider accounts,
credentials, reports or telemetry. No owner configuration is changed.
"""

from __future__ import annotations

import asyncio
import http.cookiejar
import json
import secrets
from email.message import Message
from pathlib import Path

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
    _session_cookies,
)


def test_owner_pool_workflow_and_http_guards(tmp_path: Path) -> None:
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
            }

            async def call(
                method: str,
                path: str,
                body: dict[str, object] | None = None,
                extra: dict[str, str] | None = None,
            ) -> tuple[int, Message[str, str], bytes]:
                return await asyncio.to_thread(
                    _request,
                    origin,
                    method,
                    path,
                    body=body,
                    headers=headers | (extra or {}),
                    cookies=jar,
                )

            path = "/api/v1/financial-pools?provider_key=claude"
            listing = await call("GET", path)
            assert listing[0] == 200, "financial_pool_http_missing"
            assert json.loads(listing[2])["items"] == []
            assert "no-store" in listing[1]["Cache-Control"]
            unauthenticated = await asyncio.to_thread(_request, origin, "GET", path)
            assert unauthenticated[0] == 401
            assert (await call("GET", path + "&api_key=forbidden"))[0] == 400

            async def account_connection(
                provider: str = "claude", scope: str | None = None
            ) -> str:
                create = await call(
                    "POST",
                    "/api/v1/accounts",
                    {
                        "provider_key": provider,
                        "friendly_name": "Owner billing " + secrets.token_hex(6),
                        "organization_id": None,
                        "initial_connection_purpose": "api",
                    },
                    {"Idempotency-Key": secrets.token_urlsafe(24)},
                )
                assert create[0] == 201
                account_id = json.loads(create[2])["account_id"]
                connection = await call(
                    "POST",
                    f"/api/v1/accounts/{account_id}/billing-connections",
                    {"scope_id": scope},
                    {
                        "If-Match": create[1]["ETag"],
                        "Idempotency-Key": secrets.token_urlsafe(24),
                    },
                )
                assert connection[0] == 201
                resource_id = json.loads(connection[2])["resource_id"]
                return (
                    f"/api/v1/accounts/{account_id}/financial-pools/"
                    f"{resource_id}/billing"
                )

            source_scope = "owner-scope-" + secrets.token_hex(6)
            first = await account_connection(scope=source_scope)
            status = await call("GET", first)
            assert status[0] == 200
            view = json.loads(status[2])
            assert view["can_assign"] is True
            assert view["pool"] is None
            assert view["scope_evidence"] == "owner_asserted"
            assert "binding_id" not in status[2].decode()
            assert "binding_generation" not in status[2].decode()
            create_headers = {
                "If-Match": status[1]["ETag"],
                "Idempotency-Key": secrets.token_urlsafe(24),
            }
            create_body: dict[str, object] = {
                "action": "create",
                "pool_id": None,
                "primary_organization_id": None,
            }
            assert (await call("POST", first, create_body))[0] == 428
            secret = await call(
                "POST", first, create_body | {"api_key": None}, create_headers
            )
            assert secret[0] == 422
            no_csrf = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                first,
                body=create_body,
                headers={"Origin": origin} | create_headers,
                cookies=jar,
            )
            assert no_csrf[0] == 403
            created = await call("POST", first, create_body, create_headers)
            assert created[0] == 200
            created_view = json.loads(created[2])
            pool = created_view["pool"]
            assert pool["provider_key"] == "claude"
            assert pool["display_name"]
            assert pool["primary_organization_id"] is None
            replay = await call("POST", first, create_body, create_headers)
            assert replay[0] == 200 and json.loads(replay[2]) == created_view
            conflict = await call(
                "POST",
                first,
                {"action": "unlink", "pool_id": None, "primary_organization_id": None},
                create_headers,
            )
            assert conflict[0] == 409

            second = await account_connection(scope=source_scope)
            second_status = await call("GET", second)
            joined = await call(
                "POST",
                second,
                {
                    "action": "join",
                    "pool_id": pool["pool_id"],
                    "primary_organization_id": None,
                },
                {
                    "If-Match": second_status[1]["ETag"],
                    "Idempotency-Key": secrets.token_urlsafe(24),
                },
            )
            assert joined[0] == 200
            assert json.loads(joined[2])["pool"]["pool_id"] == pool["pool_id"]
            assert len(json.loads((await call("GET", path))[2])["items"]) == 1
            # No provider verification or monitoring is implied by an association.
            owner_account = json.loads(
                (await call("GET", second.split("/financial-pools/")[0]))[2]
            )
            assert owner_account["identity_state"] == "unresolved"
            assert owner_account["monitoring_preference"] == "disabled"

            third = await account_connection(provider="codex", scope=source_scope)
            third_status = await call("GET", third)
            rejected = await call(
                "POST",
                third,
                {
                    "action": "join",
                    "pool_id": pool["pool_id"],
                    "primary_organization_id": None,
                },
                {
                    "If-Match": third_status[1]["ETag"],
                    "Idempotency-Key": secrets.token_urlsafe(24),
                },
            )
            assert rejected[0] == 409
            unresolved = await account_connection()
            missing = await call("GET", unresolved)
            assert missing[0] == 200
            assert json.loads(missing[2])["can_assign"] is False
            forbidden = await call(
                "POST",
                unresolved,
                create_body,
                {
                    "If-Match": missing[1]["ETag"],
                    "Idempotency-Key": secrets.token_urlsafe(24),
                },
            )
            assert forbidden[0] == 409
            # Attribution changes only owner metadata and invalidates stale reads.
            organization = await call(
                "POST",
                "/api/v1/organizations",
                {"name": "Owner group " + secrets.token_hex(6)},
                {"Idempotency-Key": secrets.token_urlsafe(24)},
            )
            assert organization[0] == 201
            organization_id = json.loads(organization[2])["organization_id"]
            current = await call("GET", first)
            current_pool = json.loads(current[2])["pool"]
            edit_path = f"/api/v1/financial-pools/{pool['pool_id']}/attribution"
            edit_body: dict[str, object] = {
                "expected_record_version": current_pool["record_version"],
                "primary_organization_id": organization_id,
            }
            edit_headers = {
                "If-Match": current[1]["ETag"],
                "Idempotency-Key": secrets.token_urlsafe(24),
            }
            changed = await call("PUT", edit_path, edit_body, edit_headers)
            assert changed[0] == 200
            assert json.loads(changed[2])["primary_organization_id"] == organization_id
            assert (
                json.loads(changed[2])["record_version"]
                == current_pool["record_version"] + 1
            )
            edit_replay = await call("PUT", edit_path, edit_body, edit_headers)
            assert edit_replay[0] == 200 and edit_replay[2] == changed[2]
            stale = await call(
                "PUT",
                edit_path,
                edit_body,
                edit_headers | {"Idempotency-Key": secrets.token_urlsafe(24)},
            )
            assert stale[0] == 412
            observed = await call("GET", second)
            assert (
                json.loads(observed[2])["pool"]["primary_organization_id"]
                == organization_id
            )
            revision = json.loads(observed[2])["registry_revision"]
            assert (
                await call("GET", path + f"&expected_registry_revision={revision - 1}")
            )[0] == 412
            page = await call(
                "GET", path + f"&limit=1&expected_registry_revision={revision}"
            )
            assert page[0] == 200
            assert len(json.loads(page[2])["items"]) == 1
            assert json.loads(page[2])["next_pool_id"] is None
            # A removed association stays a metadata operation, not a disconnect.
            fresh_second = await call("GET", second)
            removed = await call(
                "POST",
                second,
                {"action": "unlink", "pool_id": None, "primary_organization_id": None},
                {
                    "If-Match": fresh_second[1]["ETag"],
                    "Idempotency-Key": secrets.token_urlsafe(24),
                },
            )
            assert removed[0] == 200 and json.loads(removed[2])["pool"] is None

    asyncio.run(exercise())

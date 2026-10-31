"""ST-FLEET-001 organization routes over real loopback HTTP and file SQLite."""

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


def test_organization_list_is_authenticated_and_reports_real_empty_registry(
    tmp_path: Path,
) -> None:
    """M02-HTTP-001: an empty migrated registry remains an explicit empty view."""
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            denied = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/organizations"
            )
            assert denied[0] == 401
            assert json.loads(denied[2])["code"] == "dashboard_authentication_required"

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
            response = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/organizations", cookies=jar
            )
            assert response[0] == 200
            payload = json.loads(response[2])
            assert payload["items"] == []
            assert payload["availability"]["state"] == "available"
            assert payload["page"]["has_more"] is False

    asyncio.run(exercise())


def test_owner_renames_archives_and_restores_empty_organization(
    tmp_path: Path,
) -> None:
    """Organization changes are versioned and reversible in the real registry."""
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
                "/api/v1/organizations",
                body={"name": "Org1 - SDK"},
                headers=headers,
                cookies=jar,
            )
            assert created[0] == 201
            organization_id = json.loads(created[2])["organization_id"]
            path = f"/api/v1/organizations/{organization_id}"
            renamed = await asyncio.to_thread(
                _request,
                origin,
                "PATCH",
                path,
                body={"name": "SDK"},
                headers={**headers, "If-Match": created[1]["ETag"]},
                cookies=jar,
            )
            assert renamed[0] == 200
            assert json.loads(renamed[2])["name"] == "SDK"
            archived = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                path + "/archivals",
                body={},
                headers={
                    **headers,
                    "Idempotency-Key": secrets.token_urlsafe(24),
                    "If-Match": renamed[1]["ETag"],
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
                headers={**headers, "If-Match": archived[1]["ETag"]},
                cookies=jar,
            )
            assert restored[0] == 200
            assert json.loads(restored[2])["lifecycle"] == "active"
            fetched = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                path,
                cookies=jar,
            )
            assert fetched[0] == 200
            assert json.loads(fetched[2])["record_version"] == 4

    asyncio.run(exercise())


def test_owner_reorders_complete_active_organization_set(tmp_path: Path) -> None:
    """A whole-set order mutation has one registry revision and rejects stale input."""
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
            ids: list[str] = []
            for name in ("Org1 - SDK", "Org2 - EAIS"):
                created = await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/organizations",
                    body={"name": name},
                    headers={**headers, "Idempotency-Key": secrets.token_urlsafe(24)},
                    cookies=jar,
                )
                assert created[0] == 201
                ids.append(json.loads(created[2])["organization_id"])
            before = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/organizations",
                cookies=jar,
            )
            assert before[0] == 200
            revision = json.loads(before[2])["items"][0]["registry_revision"]
            key = secrets.token_urlsafe(24)
            reorder_headers = {**headers, "Idempotency-Key": key}
            body = {
                "ordered_organization_ids": list(reversed(ids)),
                "expected_registry_revision": revision,
            }
            reordered = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/organization-orderings",
                body=body,
                headers=reorder_headers,
                cookies=jar,
            )
            assert reordered[0] == 200
            result = json.loads(reordered[2])
            assert result["organization_ids"] == list(reversed(ids))
            assert result["registry_revision"] == revision + 1
            replay = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/organization-orderings",
                body=body,
                headers=reorder_headers,
                cookies=jar,
            )
            assert replay[0] == 200
            assert json.loads(replay[2]) == result
            stale = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/organization-orderings",
                body={**body, "ordered_organization_ids": ids},
                headers={**headers, "Idempotency-Key": secrets.token_urlsafe(24)},
                cookies=jar,
            )
            assert stale[0] == 412
            listed = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/organizations",
                cookies=jar,
            )
            listed_ids = [
                item["organization_id"] for item in json.loads(listed[2])["items"]
            ]
            assert listed_ids == list(reversed(ids))

    asyncio.run(exercise())


def test_organization_list_has_versioned_openapi_policy() -> None:
    """CTR-REG-001/CTR-API-001: generated clients see the exact safe query."""
    from agentmonitor.composition.bootstrap import create_iam_schema_application

    operation = create_iam_schema_application().openapi()["paths"][
        "/api/v1/organizations"
    ]["get"]
    assert operation["operationId"] == "registry_list_organizations_v1"
    assert operation["x-agentmonitor-required-permission"] == "read:accounts"
    assert operation["x-agentmonitor-application-port"] == "ListOrganizationsV1"
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/OrganizationPageV1"
    }


def test_owner_creates_two_organizations_with_csrf_and_idempotency(
    tmp_path: Path,
) -> None:
    """M02-HTTP-001: owner-supplied groups persist through real HTTP/SQLite."""
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
            csrf = _session_cookies(jar)["agentmonitor_csrf"]
            key = secrets.token_urlsafe(24)
            absent_proof = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/organizations",
                body={"name": "Org1 - SDK", "description": None},
                headers={"Origin": origin, "Idempotency-Key": key},
                cookies=jar,
            )
            assert absent_proof[0] == 403
            first = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/organizations",
                body={"name": "Org1 - SDK", "description": None},
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": csrf,
                    "Idempotency-Key": key,
                },
                cookies=jar,
            )
            assert first[0] == 201
            replay = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/organizations",
                body={"name": "Org1 - SDK", "description": None},
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": csrf,
                    "Idempotency-Key": key,
                },
                cookies=jar,
            )
            assert replay[0] == 201
            assert json.loads(first[2]) == json.loads(replay[2])
            second = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/organizations",
                body={"name": "Org2 - EAIS", "description": None},
                headers={
                    "Origin": origin,
                    "X-CSRF-Token": csrf,
                    "Idempotency-Key": secrets.token_urlsafe(24),
                },
                cookies=jar,
            )
            assert second[0] == 201
            listed = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/organizations", cookies=jar
            )
            assert listed[0] == 200
            assert [row["name"] for row in json.loads(listed[2])["items"]] == [
                "Org1 - SDK",
                "Org2 - EAIS",
            ]

    asyncio.run(exercise())

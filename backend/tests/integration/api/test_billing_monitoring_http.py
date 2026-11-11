"""Monitoring transport with real owner-created metadata and no provider proof."""

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


def test_billing_monitoring_http_missing_credential_and_write_guards(
    tmp_path: Path,
) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            missing_path = (
                f"/api/v1/accounts/{secrets.token_urlsafe(24)}/billing-connections/"
                f"{secrets.token_urlsafe(24)}/monitoring"
            )
            unauthenticated = await asyncio.to_thread(
                _request, origin, "GET", missing_path, headers={"Origin": origin}
            )
            assert unauthenticated[0] == 401
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
            account = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/accounts",
                body={
                    "provider_key": "claude",
                    "friendly_name": "Billing setup " + secrets.token_urlsafe(8),
                    "organization_id": None,
                    "initial_connection_purpose": "api",
                },
                headers=headers,
                cookies=jar,
            )
            assert account[0] == 201
            account_id = json.loads(account[2])["account_id"]
            connection = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                f"/api/v1/accounts/{account_id}/billing-connections",
                body={"scope_id": None},
                headers={
                    **headers,
                    "Idempotency-Key": secrets.token_urlsafe(24),
                    "If-Match": account[1]["ETag"],
                },
                cookies=jar,
            )
            assert connection[0] == 201
            metadata = json.loads(connection[2])
            resource_id = metadata["resource_id"]
            path = (
                f"/api/v1/accounts/{account_id}/billing-connections/"
                f"{resource_id}/monitoring"
            )
            status = await asyncio.to_thread(_request, origin, "GET", path, cookies=jar)
            assert status[0] == 200
            result = json.loads(status[2])
            assert result["account_id"] == account_id
            assert result["resource_id"] == resource_id
            assert result["connection_record_version"] == metadata["record_version"]
            assert result["scope_generation"] == metadata["scope_generation"]
            assert result["binding_generation"] is None
            assert result["monitoring_preference"] == "disabled"
            assert result["lifecycle"] == "pending"
            assert result["can_enable"] is False
            assert result["can_disable"] is False
            assert result["verified_run_id"] is None
            assert result["verified_at"] is None
            assert "binding_id" not in result
            assert "no-store" in status[1].get("Cache-Control", "")
            mutation_headers = {
                **headers,
                "Idempotency-Key": secrets.token_urlsafe(24),
                "If-Match": f'"{account_id}.{result["account_record_version"]}"',
            }
            body: dict[str, object] = {
                "expected_connection_version": result["connection_record_version"],
                "expected_scope_generation": result["scope_generation"],
                "expected_binding_generation": None,
                "monitoring_preference": "disabled",
                "verified_run_id": None,
            }
            for omitted, expected in (
                ("X-CSRF-Token", 403),
                ("If-Match", 428),
                ("Idempotency-Key", 400),
            ):
                rejected = await asyncio.to_thread(
                    _request,
                    origin,
                    "PUT",
                    path,
                    body=body,
                    headers={k: v for k, v in mutation_headers.items() if k != omitted},
                    cookies=jar,
                )
                assert rejected[0] == expected
            invalid_cases: tuple[dict[str, object], ...] = (
                {**body, "expected_connection_version": True},
                {**body, "expected_scope_generation": "1"},
                {**body, "expected_binding_generation": 0},
                {**body, "api_key": None},
            )
            for invalid in invalid_cases:
                rejected = await asyncio.to_thread(
                    _request,
                    origin,
                    "PUT",
                    path,
                    body=invalid,
                    headers=mutation_headers,
                    cookies=jar,
                )
                assert rejected[0] == 422
            enable = await asyncio.to_thread(
                _request,
                origin,
                "PUT",
                path,
                body={**body, "monitoring_preference": "enabled"},
                headers=mutation_headers,
                cookies=jar,
            )
            assert enable[0] == 409
            assert (
                json.loads(enable[2])["code"]
                == "billing_monitoring_verification_required"
            )
            filtered = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                path + "?scope=other",
                cookies=jar,
            )
            assert filtered[0] == 400
            missing = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                missing_path,
                cookies=jar,
            )
            assert missing[0] == 404
            assert (
                json.loads(missing[2])["code"]
                == "billing_monitoring_target_unavailable"
            )
            unchanged = await asyncio.to_thread(
                _request, origin, "GET", path, cookies=jar
            )
            assert (
                json.loads(unchanged[2])["connection_record_version"]
                == result["connection_record_version"]
            )
            assert json.loads(unchanged[2])["monitoring_preference"] == "disabled"

            stale_account_version = result["account_record_version"] + 1
            for changed_body, changed_headers in (
                (
                    body,
                    {
                        **mutation_headers,
                        "If-Match": f'"{account_id}.{stale_account_version}"',
                    },
                ),
                (
                    {
                        **body,
                        "expected_connection_version": result[
                            "connection_record_version"
                        ]
                        + 1,
                    },
                    mutation_headers,
                ),
                (
                    {
                        **body,
                        "expected_scope_generation": result["scope_generation"] + 1,
                    },
                    mutation_headers,
                ),
            ):
                stale = await asyncio.to_thread(
                    _request,
                    origin,
                    "PUT",
                    path,
                    body=changed_body,
                    headers=changed_headers,
                    cookies=jar,
                )
                assert stale[0] == 412
            # Disabling actual pending metadata needs no invented provider proof.
            disabled = await asyncio.to_thread(
                _request,
                origin,
                "PUT",
                path,
                body=body,
                headers=mutation_headers,
                cookies=jar,
            )
            assert disabled[0] == 200
            disabled_body = json.loads(disabled[2])
            assert disabled_body["monitoring_preference"] == "disabled"
            assert disabled_body["lifecycle"] == "pending"
            assert (
                disabled_body["connection_record_version"]
                == result["connection_record_version"]
            )
            replay = await asyncio.to_thread(
                _request,
                origin,
                "PUT",
                path,
                body=body,
                headers=mutation_headers,
                cookies=jar,
            )
            assert replay[0] == 200
            assert json.loads(replay[2]) == disabled_body
            conflict = await asyncio.to_thread(
                _request,
                origin,
                "PUT",
                path,
                body={
                    **body,
                    "expected_connection_version": result["connection_record_version"]
                    + 1,
                },
                headers=mutation_headers,
                cookies=jar,
            )
            assert conflict[0] == 409
            assert json.loads(conflict[2])["code"] == "registry_idempotency_conflict"

    asyncio.run(exercise())


def test_monitoring_proof_failures_map_to_safe_conflicts() -> None:
    from agentmonitor.api.v1.routers.billing_actions import _monitoring_error

    for internal in (
        "billing_monitoring_proof_required",
        "billing_monitoring_proof_conflict",
        "registry_timestamp_conflict",
    ):
        error = _monitoring_error(ValueError(internal))
        assert error.status == 409
        assert error.code in {
            "billing_monitoring_verification_required",
            "billing_monitoring_target_changed",
        }

"""M4-ALERT-HTTP: real migrated IAM and M07 rules through Uvicorn."""

import asyncio
import http.cookiejar
import json
import secrets
from pathlib import Path

from agentmonitor.composition.bootstrap import create_iam_application
from agentmonitor.foundation.application import LifecycleHooksV1

from backend.tests.integration.alerting.test_real_capacity_consumer import (
    _provision_actual_alerts,
)
from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
)


def test_alert_rule_crud_requires_auth_and_preserves_receipts(tmp_path: Path) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            denied = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/alert-rules",
                headers={"Origin": origin},
            )
            assert denied[0] == 401
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
            empty = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/alert-rules", cookies=jar
            )
            assert empty[0] == 200 and json.loads(empty[2])["items"] == []
            key = secrets.token_urlsafe(24)
            body: dict[str, object] = {
                "condition_type": "capacity_remaining",
                "scope_kind": "global",
                "scope_id": None,
                "enabled": True,
                "configuration": {
                    "schema_major": 1,
                    "warning_remaining_basis_points": 2000,
                    "critical_remaining_basis_points": 1000,
                },
            }
            csrf = {cookie.name: cookie.value for cookie in jar}["agentmonitor_csrf"]
            assert csrf is not None
            headers: dict[str, str] = {
                "Origin": origin,
                "X-CSRF-Token": csrf,
                "Idempotency-Key": key,
            }
            created = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/alert-rules",
                body=body,
                headers=headers,
                cookies=jar,
            )
            assert created[0] == 201
            rule = json.loads(created[2])["rule"]
            assert rule["condition_type"] == "capacity_remaining"
            assert rule["configuration"]["warning_remaining_basis_points"] == 2000
            assert rule["record_version"] == 1
            repeated = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/alert-rules",
                body=body,
                headers=headers,
                cookies=jar,
            )
            assert (
                repeated[0] == 201
                and json.loads(repeated[2])["receipt_id"]
                == json.loads(created[2])["receipt_id"]
            )
            listing = await asyncio.to_thread(
                _request, origin, "GET", "/api/v1/alert-rules", cookies=jar
            )
            assert listing[0] == 200 and len(json.loads(listing[2])["items"]) == 1
            changed = dict(
                body,
                configuration={
                    "schema_major": 1,
                    "warning_remaining_basis_points": 2500,
                    "critical_remaining_basis_points": 1200,
                },
            )
            update_headers = dict(
                headers,
                **{
                    "Idempotency-Key": secrets.token_urlsafe(24),
                    "If-Match": f'"{rule["rule_id"]}.1"',
                },
            )
            updated = await asyncio.to_thread(
                _request,
                origin,
                "PUT",
                f"/api/v1/alert-rules/{rule['rule_id']}",
                body=changed,
                headers=update_headers,
                cookies=jar,
            )
            assert (
                updated[0] == 200
                and json.loads(updated[2])["rule"]["record_version"] == 2
            )
            stale_headers = dict(
                update_headers, **{"Idempotency-Key": secrets.token_urlsafe(24)}
            )
            stale = await asyncio.to_thread(
                _request,
                origin,
                "PUT",
                f"/api/v1/alert-rules/{rule['rule_id']}",
                body=changed,
                headers=stale_headers,
                cookies=jar,
            )
            assert stale[0] == 412
            wire = listing[2].decode()
            assert credential not in wire and str(tmp_path) not in wire

    asyncio.run(exercise())


def test_alert_console_reads_real_empty_store_with_authenticated_http(
    tmp_path: Path,
) -> None:
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
            for path in ("/api/v1/alerts", "/api/v1/alert-notifications"):
                result = await asyncio.to_thread(
                    _request, origin, "GET", path, cookies=jar
                )
                assert result[0] == 200
                assert json.loads(result[2])["items"] == []
            counts = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/alert-notifications/counts",
                cookies=jar,
            )
            assert counts[0] == 200
            assert json.loads(counts[2])["active_critical"] == 0

    asyncio.run(exercise())


def test_genuine_derived_alert_can_be_read_and_acknowledged_over_http(
    tmp_path: Path,
) -> None:
    credential = secrets.token_urlsafe(32)
    _, _, alert_id = _provision_actual_alerts(tmp_path, credential)
    config = tmp_path / "isolated.env"
    config.write_text("")
    config.chmod(0o600)
    app = create_iam_application(config, tmp_path, lifecycle=LifecycleHooksV1())

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
            detail = await asyncio.to_thread(
                _request, origin, "GET", f"/api/v1/alerts/{alert_id.value}", cookies=jar
            )
            assert detail[0] == 200
            alert = json.loads(detail[2])
            assert alert["alert_id"] == alert_id.value and alert["lifecycle"] == "open"
            history = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                f"/api/v1/alerts/{alert_id.value}/history",
                cookies=jar,
            )
            assert history[0] == 200 and json.loads(history[2])["items"]
            csrf = {cookie.name: cookie.value for cookie in jar}["agentmonitor_csrf"]
            assert csrf is not None
            headers: dict[str, str] = {
                "Origin": origin,
                "X-CSRF-Token": csrf,
                "Idempotency-Key": secrets.token_urlsafe(24),
                "If-Match": f'"{alert_id.value}.{alert["record_version"]}"',
            }
            acknowledged = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                f"/api/v1/alerts/{alert_id.value}/acknowledgements",
                headers=headers,
                cookies=jar,
            )
            assert acknowledged[0] == 200
            payload = json.loads(acknowledged[2])
            assert payload["alert"]["acknowledged_at"] is not None
            repeated = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                f"/api/v1/alerts/{alert_id.value}/acknowledgements",
                headers=headers,
                cookies=jar,
            )
            assert (
                repeated[0] == 200
                and json.loads(repeated[2])["receipt_id"] == payload["receipt_id"]
            )
            current = payload["alert"]
            snooze_headers = dict(
                headers,
                **{
                    "Idempotency-Key": secrets.token_urlsafe(24),
                    "If-Match": (f'"{alert_id.value}.{current["record_version"]}"'),
                },
            )
            snoozed = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                f"/api/v1/alerts/{alert_id.value}/snoozes",
                body={"duration_seconds": 900},
                headers=snooze_headers,
                cookies=jar,
            )
            assert snoozed[0] == 200
            current = json.loads(snoozed[2])["alert"]
            assert current["snoozed_until"] is not None
            unsnooze_headers = dict(
                headers,
                **{
                    "Idempotency-Key": secrets.token_urlsafe(24),
                    "If-Match": (f'"{alert_id.value}.{current["record_version"]}"'),
                },
            )
            unsnoozed = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                f"/api/v1/alerts/{alert_id.value}/unsnoozes",
                headers=unsnooze_headers,
                cookies=jar,
            )
            assert unsnoozed[0] == 200
            current = json.loads(unsnoozed[2])["alert"]
            assert current["snoozed_until"] is None
            assert unsnoozed[1]["ETag"] == (
                f'"{alert_id.value}.{current["record_version"]}"'
            )
            assert current["record_version"] > current["notification_revision"]
            stale_read_headers = dict(
                headers,
                **{
                    "Idempotency-Key": secrets.token_urlsafe(24),
                    "If-Match": (f'"{alert_id.value}.{current["record_version"]}"'),
                },
            )
            stale_read = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                f"/api/v1/alerts/{alert_id.value}/read-receipts",
                headers=stale_read_headers,
                cookies=jar,
            )
            assert stale_read[0] == 412
            read_headers = dict(
                headers,
                **{
                    "Idempotency-Key": secrets.token_urlsafe(24),
                    "If-Match": (
                        f'"{alert_id.value}.{current["notification_revision"]}"'
                    ),
                },
            )
            marked_read = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                f"/api/v1/alerts/{alert_id.value}/read-receipts",
                headers=read_headers,
                cookies=jar,
            )
            assert marked_read[0] == 200
            current = json.loads(marked_read[2])["alert"]
            assert current["unread"] is False
            reloaded = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                f"/api/v1/alerts/{alert_id.value}",
                cookies=jar,
            )
            assert reloaded[0] == 200 and json.loads(reloaded[2]) == current

    asyncio.run(exercise())

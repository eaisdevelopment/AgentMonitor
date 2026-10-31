"""CTR-CAP-006 history over real loopback HTTP and file-backed SQLite."""

from __future__ import annotations

import asyncio
import http.cookiejar
import json
import secrets
import urllib.parse
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agentmonitor.adapters.identity_access.argon2_password import Argon2PasswordV1
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.repository import (
    SqliteIdentityAccessRepositoryV1,
)
from agentmonitor.composition.bootstrap import create_iam_application
from agentmonitor.contracts.identity_access_v1 import SecretInputV1
from agentmonitor.foundation.application import LifecycleHooksV1
from agentmonitor.modules.identity_access.application.bootstrap import (
    BootstrapAdministratorV1,
)

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
)

if TYPE_CHECKING:
    from backend.tests.integration.conftest import RealClaudeMonitoringContextV1


def _quota_observation_count(root: Path) -> int:
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            return int(
                connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM capacity_quota_observation"
                ).scalar_one()
            )


def _history_path(**overrides: str) -> str:
    parameters = {
        "subject_id": "not-enrolled",
        "metric": "remaining_ratio",
        "series_kind": "poll_snapshot",
        "from": "2026-01-01T00:00:00Z",
        "before": "2026-01-02T00:00:00Z",
        **overrides,
    }
    return "/api/v1/capacity/history?" + urllib.parse.urlencode(parameters)


def test_capacity_history_authenticates_and_get_never_collects(tmp_path: Path) -> None:
    """M05-HTTP-001/009: the bounded history query is side-effect free."""
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            assert _quota_observation_count(tmp_path) == 0
            denied = await asyncio.to_thread(_request, origin, "GET", _history_path())
            assert denied[0] == 401

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
                _request, origin, "GET", _history_path(), cookies=jar
            )
            assert response[0] == 200, response[2]
            payload = json.loads(response[2])
            assert payload["subject_id"] == "not-enrolled"
            assert payload["metric"] == "remaining_ratio"
            assert payload["series_kind"] == "poll_snapshot"
            assert payload["items"] == []
            assert payload["page"] == {
                "limit": 50,
                "next_cursor": None,
                "has_more": False,
            }
            assert payload["availability"]["state"] == "unavailable"

    asyncio.run(exercise())
    assert _quota_observation_count(tmp_path) == 0


def test_capacity_history_openapi_has_exact_read_policy() -> None:
    """API-OAPI: history publishes the approved auth, port, and response model."""
    from agentmonitor.composition.bootstrap import create_iam_schema_application

    operation = create_iam_schema_application().openapi()["paths"][
        "/api/v1/capacity/history"
    ]["get"]
    assert operation["operationId"] == "capacity_list_history_v1"
    assert operation["x-agentmonitor-required-permission"] == "read:telemetry"
    assert operation["x-agentmonitor-application-port"] == "ListCapacityHistoryV1"
    assert operation["x-agentmonitor-replay-policy"] == "safe_query_repeat"
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/CapacityHistoryPageV1"
    }


def test_real_claude_history_reaches_authenticated_loopback_http(
    real_claude_monitoring_context: RealClaudeMonitoringContextV1,
) -> None:
    """AC-HIST-001/M05-HTTP-009: persisted live points cross the real API."""
    context = real_claude_monitoring_context
    root = context.reference._approved_root
    credential = secrets.token_urlsafe(32)
    outcome = BootstrapAdministratorV1(
        SqliteIdentityAccessRepositoryV1(context.reference), Argon2PasswordV1()
    )(
        SecretInputV1(credential),
        correlation_id="capacity-history-live-http-setup",
    )
    assert outcome.code == "created"
    config = root / "capacity-history-http.env"
    config.write_text("")
    config.chmod(0o600)
    app = create_iam_application(config, root, lifecycle=LifecycleHooksV1())
    observation_times = tuple(
        item.observed_at or item.collected_at for item in context.result.quota_windows
    )
    parameters = {
        "subject_id": context.result.graph.account.account_id.value,
        "metric": "remaining_ratio",
        "series_kind": "poll_snapshot",
        "from": (min(observation_times) - timedelta(minutes=1)).isoformat(),
        "before": (max(observation_times) + timedelta(minutes=1)).isoformat(),
        "limit": "1",
    }
    expected_count = len(context.result.capacity_receipt.observation_ids)

    async def exercise() -> None:
        async with _running(app) as origin:
            assert _quota_observation_count(root) == expected_count
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
            points: list[Any] = []
            cursor: str | None = None
            while True:
                query = parameters | ({"cursor": cursor} if cursor is not None else {})
                response = await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    "/api/v1/capacity/history?" + urllib.parse.urlencode(query),
                    cookies=jar,
                )
                assert response[0] == 200, response[2]
                payload = json.loads(response[2])
                assert payload["availability"]["state"] == "available"
                points.extend(payload["items"])
                cursor = payload["page"]["next_cursor"]
                if cursor is None:
                    assert payload["page"]["has_more"] is False
                    break
                assert payload["page"]["has_more"] is True
            assert len(points) == expected_count
            assert len({point["observation_id"] for point in points}) == len(points)
            assert [
                (point["observed_at"], point["observation_id"]) for point in points
            ] == sorted(
                (point["observed_at"], point["observation_id"]) for point in points
            )
            for point in points:
                assert point["subject"]["account_id"] == parameters["subject_id"]
                assert point["metric"] == "remaining_ratio"
                assert point["series_kind"] == "poll_snapshot"
                assert point["provenance"]["source_id"]
                assert point["semantic_role"]
                assert point["native_unit"]
                assert point["window_definition_id"]
                assert point["value"]["availability"]
            assert _quota_observation_count(root) == expected_count

    asyncio.run(exercise())
    assert _quota_observation_count(root) == expected_count

"""Read a genuine pre-dispatch expiry through SQLite and authenticated HTTP."""

from __future__ import annotations

import asyncio
import http.cookiejar
import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.composition.cloud_usage_actions import CloudUsageActionsV1
from agentmonitor.contracts.collection_control_v1 import BudgetCollectionRunViewV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.collection_control.application.queries import (
    ListCollectionRunsV1,
)

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
)
from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)


def test_genuine_queued_expiry_remains_readable_without_recollection(
    tmp_path: Path,
) -> None:
    """M7-A05/A09: preserve null start, original context and terminal failure."""
    data_path = tmp_path / "genuine-history"
    data_path.mkdir(mode=0o700)
    reference = _private_real_copy(data_path)
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            row = (
                connection.exec_driver_sql(
                    "SELECT run_id,account_id,resource_id,requested_at,completed_at "
                    "FROM collection_run WHERE provider_key='ollama' "
                    "AND capability_id='api.usage' "
                    "AND payload_schema='budget.report.v1' "
                    "AND state='failed' AND error_code='collection_queued_expired' "
                    "AND started_at IS NULL ORDER BY requested_at DESC LIMIT 1"
                )
                .mappings()
                .one_or_none()
            )
    assert row is not None, "genuine_queued_expiry_required"
    runs = SqliteCollectionRepositoryV1(reference)
    run_id = OpaqueIdV1(str(row["run_id"]))
    current = runs.get_run(run_id)
    assert isinstance(current, BudgetCollectionRunViewV1)
    assert current.state == "failed"
    assert current.started_at is None and current.duration_ms is None
    assert current.payload_digest is None and current.report_id is None
    assert current.observation_ids == ()
    assert current.completed_at == datetime.fromisoformat(str(row["completed_at"]))
    page = runs.list_runs("ollama", current.account_id, current.requested_at, 1)
    assert len(page) == 1 and page[0] == current

    iam_path = tmp_path / "isolated-iam"
    iam_path.mkdir(mode=0o700)
    app, credential = _installation(iam_path)
    app.state.observation_ports = replace(
        app.state.observation_ports,
        list_collection_runs=ListCollectionRunsV1(runs),
        cloud_usage=CloudUsageActionsV1(reference),
    )

    async def exercise() -> None:
        jar = http.cookiejar.CookieJar()
        async with _running(app) as origin:
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
            history = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/collection-runs?provider_key=ollama&limit=200",
                cookies=jar,
            )
            assert history[0] == 200
            assert json.loads(history[2])["availability"]["state"] == "available"
            status = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                f"/api/v1/accounts/{row['account_id']}/cloud-usage/"
                f"{row['resource_id']}/runs/{run_id.value}",
                cookies=jar,
            )
            assert status[0] == 200
            result = json.loads(status[2])
            assert result["state"] == "failed"
            assert result["error_code"] == "collection_queued_expired"
            assert result["started_at"] is None and result["report_id"] is None
            assert result["report_context"]["range_key"] in {"7d", "30d"}

    asyncio.run(exercise())

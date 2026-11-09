"""Read-only proof against the real owner-selected scheduled collection."""

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.contracts.capacity_v1 import CapacityHistoryQueryV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.capacity.application.queries import (
    ListCapacityHistoryV1,
    ListQuotaWindowsV1,
)
from agentmonitor.modules.collection_control.application.queries import (
    ListCollectionRunsV1,
)


def test_real_unknown_session_replaces_current_and_preserves_history() -> None:
    """M6-A07/FR-COL-007: no seeded data, enrollment or collection dispatch."""
    selected = os.environ.get("AGENTMONITOR_TEST_OWNER_DATA_ROOT")
    selected_account = os.environ.get("AGENTMONITOR_TEST_MANAGED_ACCOUNT_ID")
    if selected is None or selected_account is None:
        pytest.skip("NOT RUN: explicit real owner data root/account required")
    root = Path(selected)
    baseline_path = root / "m6-claude-before-20261109.json"
    assert (
        not baseline_path.is_symlink() and baseline_path.stat().st_mode & 0o777 == 0o600
    )
    baseline = json.loads(baseline_path.read_text())
    previous = next(
        row for row in baseline["windows"] if row["key"] == "current_session"
    )
    assert previous["used_availability"] == "available" and previous["used"] is not None
    account = OpaqueIdV1(selected_account)
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    repository = SqliteCapacityRepositoryV1(reference)
    now = datetime.now(UTC)
    windows = ListQuotaWindowsV1(repository)(account, as_of=now)
    session = next(row for row in windows if row.window_key == "current_session")
    weekly = next(row for row in windows if row.window_key == "current_week_all_models")
    assert session.used.availability.state == "unknown" and session.used.value is None
    assert session.remaining_ratio.value is None
    assert session.current_observation_id.value != previous["observation_id"]
    assert (
        weekly.used.availability.state == "available" and weekly.used.value is not None
    )
    assert session.collection_run_id == weekly.collection_run_id
    assert session.freshness == weekly.freshness == "fresh"
    runs = ListCollectionRunsV1(SqliteCollectionRepositoryV1(reference))(
        provider_key="claude",
        account_id=account,
        as_of=now,
        page_size=100,
    )
    run = next(row for row in runs if row.run_id == session.collection_run_id)
    assert run.state == "partial" and run.adapter_version == "1.0.4"
    assert run.payload_digest is not None and run.error_code is None
    assert {session.current_observation_id, weekly.current_observation_id}.issubset(
        run.observation_ids
    )
    history = ListCapacityHistoryV1(repository)(
        CapacityHistoryQueryV1(
            subject_id=account,
            resource_id=None,
            window_id=None,
            metric="used",
            series_kind="poll_snapshot",
            range_start=now - timedelta(days=30),
            range_before=now,
            as_of=now,
            limit=200,
            after_key=None,
            bucket_method=None,
            bucket_seconds=None,
        )
    )
    old_point = next(
        row
        for row in history.items
        if row.observation_id.value == previous["observation_id"]
    )
    new_point = next(
        row
        for row in history.items
        if row.observation_id == session.current_observation_id
    )
    assert old_point.value.value is not None
    assert str(old_point.value.value.as_decimal()) == previous["used"]
    assert (
        new_point.value.availability.state == "unknown"
        and new_point.value.value is None
    )

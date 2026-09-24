"""Real retained Claude observations through CTR-CAP-006 history."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from backend.tests.integration.conftest import RealClaudeMonitoringContextV1


def _selected_real_data_root() -> Path:
    value = os.environ.get("AGENTMONITOR_TEST_DATA_ROOT")
    if value is None:
        pytest.skip("NOT RUN: AGENTMONITOR_TEST_DATA_ROOT is not selected")
    root = Path(value)
    if not root.is_absolute():
        pytest.fail("AGENTMONITOR_TEST_DATA_ROOT must be absolute")
    return root


def test_real_persisted_history_freshness_uses_query_as_of() -> None:
    """M05-PURE-011/DB-030: retained freshness is evaluated at query time."""
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
    )
    from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
        SqliteCapacityRepositoryV1,
    )
    from agentmonitor.adapters.persistence.registry.sqlite.repository import (
        SqliteRegistryRepositoryV1,
    )
    from agentmonitor.contracts.capacity_v1 import CapacityHistoryQueryV1
    from agentmonitor.modules.capacity.application.queries import ListCapacityHistoryV1
    from agentmonitor.modules.registry.application.accounts import ListAccountsV1

    root = _selected_real_data_root()
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    accounts = tuple(
        account
        for account in ListAccountsV1(SqliteRegistryRepositoryV1(reference))("claude")
        if account.lifecycle == "active" and account.identity_state == "owner_confirmed"
    )
    if len(accounts) != 1:
        pytest.skip("BLOCKED: selected real database lacks one active Claude account")

    as_of = datetime.now(UTC)
    query = CapacityHistoryQueryV1(
        subject_id=accounts[0].account_id,
        resource_id=None,
        window_id=None,
        metric="remaining_ratio",
        series_kind="poll_snapshot",
        range_start=as_of - timedelta(days=365),
        range_before=as_of,
        as_of=as_of,
        limit=200,
        after_key=None,
        bucket_method=None,
        bucket_seconds=None,
    )
    page = ListCapacityHistoryV1(SqliteCapacityRepositoryV1(reference))(query)
    if not page.items:
        pytest.skip("BLOCKED: selected real database has no retained Claude history")

    for point in page.items:
        deadline = point.provenance.freshness_deadline
        expected = (
            "freshness_unknown"
            if deadline is None
            else "stale"
            if deadline <= as_of
            else "fresh"
        )
        assert point.freshness == expected


def test_real_claude_history_is_exact_stable_and_cursor_bounded(
    real_claude_monitoring_context: RealClaudeMonitoringContextV1,
) -> None:
    """M05-DB-030..032: query persisted facts; never construct telemetry."""
    from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
        SqliteCapacityRepositoryV1,
    )
    from agentmonitor.contracts.capacity_v1 import CapacityHistoryQueryV1
    from agentmonitor.modules.capacity.application.queries import ListCapacityHistoryV1

    context = real_claude_monitoring_context
    result = context.result
    observation_times = tuple(
        item.observed_at or item.collected_at for item in result.quota_windows
    )
    query = CapacityHistoryQueryV1(
        subject_id=result.graph.account.account_id,
        resource_id=None,
        window_id=None,
        metric="remaining_ratio",
        series_kind="poll_snapshot",
        range_start=min(observation_times) - timedelta(minutes=1),
        range_before=max(observation_times) + timedelta(minutes=1),
        as_of=datetime.now(UTC),
        limit=1,
        after_key=None,
        bucket_method=None,
        bucket_seconds=None,
    )
    list_history = ListCapacityHistoryV1(SqliteCapacityRepositoryV1(context.reference))

    pages = []
    next_key = None
    while True:
        page = list_history(query.with_cursor(next_key))
        pages.append(page)
        if not page.has_more:
            break
        assert page.next_key is not None
        next_key = page.next_key

    points = tuple(point for page in pages for point in page.items)
    assert points
    assert len(points) == len(result.capacity_receipt.observation_ids)
    assert {point.observation_id for point in points} == set(
        result.capacity_receipt.observation_ids
    )
    assert tuple(
        (point.observed_at, point.observation_id.value) for point in points
    ) == tuple(
        sorted((point.observed_at, point.observation_id.value) for point in points)
    )
    assert len({point.observation_id for point in points}) == len(points)

    current_by_window = {item.window_id: item for item in result.quota_windows}
    for point in points:
        current = current_by_window[point.window_id]
        assert point.subject == current.subject
        assert point.value == current.remaining_ratio
        assert point.collection_run_id == result.completed_run.run_id
        assert point.series_kind == "poll_snapshot"
        assert point.metric == "remaining_ratio"
        assert point.provenance == current.provenance
        assert point.native_unit is not None
        assert point.semantic_role
        assert point.window_definition_id.value
        assert point.observed_at is not None
        assert point.collected_at <= point.stored_at

    repeat = list_history(query.with_cursor(None))
    assert repeat.items == pages[0].items

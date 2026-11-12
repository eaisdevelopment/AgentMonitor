"""Pure immutable dispatch metadata; no constructed values cross I/O."""

from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def test_dispatch_queue_metadata_is_all_or_none() -> None:
    from agentmonitor.contracts.collection_control_v1 import BudgetDispatchStateV1

    now = datetime(2026, 11, 12, tzinfo=UTC)
    empty = BudgetDispatchStateV1("a" * 64, "billing.cost.7d", None, None, None, None)
    assert empty.last_started_at is None
    with pytest.raises(ValueError, match="budget_dispatch_state_invalid"):
        BudgetDispatchStateV1(
            "a" * 64, "billing.cost.7d", None, OpaqueIdV1("queued"), now, None
        )
    with pytest.raises(ValueError, match="budget_dispatch_state_invalid"):
        BudgetDispatchStateV1(
            "a" * 64, "billing.cost.7d", None, OpaqueIdV1("queued"), now, now
        )
    assert BudgetDispatchStateV1(
        "a" * 64,
        "billing.cost.7d",
        now,
        OpaqueIdV1("queued"),
        now,
        now + timedelta(seconds=120),
    ).queued_run_id == OpaqueIdV1("queued")


def test_dispatch_snapshot_rejects_duplicate_identity() -> None:
    from agentmonitor.contracts.collection_control_v1 import (
        BudgetDispatchSnapshotV1,
        BudgetDispatchStateV1,
    )

    item = BudgetDispatchStateV1("a" * 64, "billing.cost.7d", None, None, None, None)
    assert BudgetDispatchSnapshotV1((item,), ()).states == (item,)
    with pytest.raises(ValueError, match="budget_dispatch_snapshot_invalid"):
        BudgetDispatchSnapshotV1((item, item), ())


def test_sustained_manual_work_cannot_starve_older_due_resource() -> None:
    from agentmonitor.composition.budget_dispatch import (
        BudgetWorkV1,
        ordered_budget_work,
    )

    now = datetime(2026, 11, 12, 12, tzinfo=UTC)
    manual = BudgetWorkV1(
        ("claude", "a", "7d"),
        now - timedelta(seconds=30),
        now - timedelta(seconds=5),
        OpaqueIdV1("manual"),
        False,
    )
    due = BudgetWorkV1(
        ("ollama", "b", "30d"),
        now - timedelta(hours=1),
        now - timedelta(minutes=5),
        None,
        True,
    )
    assert ordered_budget_work((manual, due))[0] == due
    # After the previously starved resource gets a real start, the other wins.
    from dataclasses import replace

    assert ordered_budget_work((manual, replace(due, last_started_at=now)))[0] == manual


def test_never_served_resource_and_stable_ties_ignore_input_order() -> None:
    from agentmonitor.composition.budget_dispatch import (
        BudgetWorkV1,
        ordered_budget_work,
    )

    now = datetime(2026, 11, 12, 12, tzinfo=UTC)
    first = BudgetWorkV1(("codex", "a", "7d"), None, now, None, True)
    second = BudgetWorkV1(("ollama", "b", "30d"), None, now, None, True)
    recent = BudgetWorkV1(
        ("claude", "c", "7d"),
        now,
        now - timedelta(hours=1),
        OpaqueIdV1("manual"),
        False,
    )
    assert ordered_budget_work((recent, second, first)) == (first, second, recent)
    assert ordered_budget_work((first, second, recent)) == (first, second, recent)

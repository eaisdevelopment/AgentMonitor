"""Retention cursor and cutoff policy are pure; no invented external observations."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.operations_v1 import OperationsParticipantRequestV1


def request() -> OperationsParticipantRequestV1:
    return OperationsParticipantRequestV1(
        OpaqueIdV1("retention-cycle"),
        OpaqueIdV1("retention-correlation"),
        datetime(2090, 1, 1, tzinfo=UTC),
        1,
        datetime(2080, 1, 1, tzinfo=UTC),
        1,
        None,
        None,
        None,
        None,
    )


def test_cursor_binds_fixed_operation_cutoff_and_scan_bounds() -> None:
    from agentmonitor.modules.capacity.domain.budget_retention import (
        retention_cursor,
        retention_position,
    )

    original = request()
    assert original.cutoff is not None
    cursor = retention_cursor(original, 150, 100)
    assert len(cursor) <= 128
    assert retention_position(replace(original, cursor=cursor)) == (150, 100)
    for changed in (
        replace(original, operation_id=OpaqueIdV1("another-cycle")),
        replace(original, cutoff=original.cutoff + timedelta(days=1)),
    ):
        with pytest.raises(ValueError, match="budget_retention_cursor_invalid"):
            retention_position(replace(changed, cursor=cursor))


def test_cutoff_is_strict_and_newly_stored_old_reports_survive() -> None:
    from agentmonitor.modules.capacity.domain.budget_retention import expired_report

    cutoff = datetime(2080, 1, 1, tzinfo=UTC)
    old = cutoff - timedelta(days=1)
    assert expired_report(old, old, cutoff)
    assert not expired_report(cutoff, old, cutoff)
    assert not expired_report(old, cutoff, cutoff)


def test_any_referenced_fact_protects_the_entire_report_bundle() -> None:
    from agentmonitor.modules.capacity.domain.budget_retention import referenced_report

    costs, usage = OpaqueIdV1("cost-fact"), OpaqueIdV1("usage-fact")
    unrelated = OpaqueIdV1("another-report-fact")
    assert referenced_report((costs, usage), (usage,))
    assert referenced_report((costs, usage), (unrelated, costs))
    assert not referenced_report((costs, usage), (unrelated,))
    assert not referenced_report((), (costs,))

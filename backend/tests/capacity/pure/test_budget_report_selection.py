"""M7-MATH-04/05/12: pure report replacement, never provider fixtures."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from agentmonitor.contracts import capacity_v1 as contracts
from agentmonitor.contracts.common_quantity_v1 import CanonicalDecimalV1, ExactMoneyV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import ProviderTargetRefV1
from agentmonitor.modules.capacity.domain.budget_reports import select_current_report

START = datetime(2026, 11, 1, tzinfo=UTC)
END = START + timedelta(days=1)


def _report(sequence: int, value: str | None) -> contracts.BudgetReportViewV1:
    assert hasattr(contracts, "BudgetReportViewV1"), "M7 immutable report view absent"
    period = contracts.BudgetPeriodV1(START, END)
    rows = (
        ()
        if value is None
        else (
            contracts.BudgetCostBucketV1(
                bucket_key="bucket",
                period=period,
                amount=ExactMoneyV1(
                    CanonicalDecimalV1.from_decimal(Decimal(value)), "USD"
                ),
                dimensions=(),
                kind="charge",
            ),
        )
    )
    payload = contracts.BudgetReportInputV1(
        subject=contracts.CapacitySubjectV2(
            provider_key="claude",
            provider_target=ProviderTargetRefV1(
                "cloud_service", OpaqueIdV1("amat_" + "c" * 32)
            ),
            account_id=OpaqueIdV1("pure-account"),
            resource_id=OpaqueIdV1("pure-pool"),
        ),
        binding_id=OpaqueIdV1("pure-binding"),
        binding_generation=1,
        scope_generation=1,
        scope_id=OpaqueIdV1("pure-scope"),
        scope_evidence="provider_verified",
        source_id="pure-contract-cost",
        source_category="costs",
        cost_basis="after_discount_before_credit",
        grouping=(),
        requested_period=period,
        covered_period=period,
        source_data_through=END,
        collected_at=END + timedelta(hours=sequence),
        completeness="complete",
        omission_codes=(),
        currency="USD",
        empty_means_zero=True,
        cost_buckets=rows,
        usage_buckets=(),
    )
    return contracts.BudgetReportViewV1(
        report_id=OpaqueIdV1(f"pure-report-{sequence}"),
        report=payload,
        stored_at=payload.collected_at,
    )


def test_new_complete_report_replaces_cost_instead_of_adding_versions() -> None:
    old, new = _report(1, "8"), _report(2, "6")
    result = select_current_report((new, old))
    assert result.current == new
    assert result.current.report.cost_buckets[0].amount.amount.as_decimal() == Decimal(
        "6"
    )
    assert old.report.cost_buckets[0].amount.amount.as_decimal() == Decimal("8")


def test_complete_empty_revision_removes_old_charge() -> None:
    result = select_current_report((_report(1, "8"), _report(2, None)))
    assert result.current is not None
    assert result.current.report.cost_buckets == ()
    assert result.current.report.empty_means_zero


def test_later_partial_report_preserves_complete_total_and_latest_attempt() -> None:
    old, attempted = _report(1, "8"), _report(2, "100")
    partial = replace(
        attempted,
        report=replace(
            attempted.report,
            completeness="partial",
            omission_codes=("missing_page",),
            empty_means_zero=False,
        ),
    )
    result = select_current_report((old, partial))
    assert result.current == old
    assert result.latest_attempt == partial
    assert result.current.report.source_data_through == END


@pytest.mark.parametrize("change", ["currency", "scope", "period", "generation"])
def test_incompatible_reports_are_not_combined(change: str) -> None:
    old, new = _report(1, None), _report(2, None)
    if change == "currency":
        payload = replace(new.report, currency="GBP")
    elif change == "scope":
        payload = replace(new.report, scope_id=OpaqueIdV1("different-scope"))
    elif change == "generation":
        payload = replace(new.report, scope_generation=2)
    else:
        period = contracts.BudgetPeriodV1(START - timedelta(days=1), END)
        payload = replace(new.report, requested_period=period, covered_period=period)
    with pytest.raises(ValueError, match="incompatible_report_context"):
        select_current_report((old, replace(new, report=payload)))


def test_binding_rotation_does_not_erase_same_scope_history() -> None:
    old, new = _report(1, "8"), _report(2, "6")
    rotated = replace(
        new,
        report=replace(
            new.report,
            binding_id=OpaqueIdV1("rotated-binding"),
            binding_generation=2,
        ),
    )
    assert select_current_report((old, rotated)).current == rotated


def test_no_reports_means_no_values_and_partial_alone_is_not_current() -> None:
    assert select_current_report(()).current is None
    report = _report(1, None)
    partial = replace(
        report,
        report=replace(
            report.report,
            completeness="unknown",
            omission_codes=("source_delayed",),
            covered_period=None,
            source_data_through=None,
            empty_means_zero=False,
        ),
    )
    result = select_current_report((partial,))
    assert result.current is None and result.latest_attempt == partial

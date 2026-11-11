"""Per-report spend remains exact and never treats breakdowns as total spend."""

from dataclasses import replace
from decimal import Decimal

from agentmonitor.contracts.capacity_v1 import BudgetReportSelectionV1

from backend.tests.capacity.pure.test_budget_report_selection import _report


def test_selected_complete_report_yields_exact_spend_without_other_attempts() -> None:
    from agentmonitor.modules.capacity.domain.budget_account_spend import reported_spend

    current = _report(1, "0.10")
    second = replace(
        current.report.cost_buckets[0],
        bucket_key="second",
        amount=replace(
            current.report.cost_buckets[0].amount,
            amount=current.report.cost_buckets[0].amount.amount.from_decimal(
                Decimal("0.20")
            ),
        ),
    )
    period = current.report.requested_period
    midpoint = period.start + (period.end - period.start) / 2
    first = replace(
        current.report.cost_buckets[0], period=replace(period, end=midpoint)
    )
    second = replace(second, period=replace(period, start=midpoint))
    current = replace(
        current, report=replace(current.report, cost_buckets=(first, second))
    )
    result = reported_spend(BudgetReportSelectionV1(current, _report(2, "999")))
    assert result is not None and result.total is not None
    assert result.total.amount.as_decimal() == Decimal("0.30")
    assert result.report_id == current.report_id


def test_incomplete_empty_and_grouped_reports_do_not_invent_totals() -> None:
    from agentmonitor.modules.capacity.domain.budget_account_spend import reported_spend

    report = _report(1, None)
    genuine_empty = reported_spend(BudgetReportSelectionV1(report, report))
    assert genuine_empty is not None and genuine_empty.total is not None
    assert genuine_empty.total.amount.as_decimal() == 0
    unknown = replace(report, report=replace(report.report, empty_means_zero=False))
    no_zero = reported_spend(BudgetReportSelectionV1(unknown, unknown))
    assert no_zero is not None and no_zero.total is None
    partial_only = reported_spend(BudgetReportSelectionV1(None, unknown))
    assert partial_only is not None and partial_only.total is None
    grouped = replace(report, report=replace(report.report, grouping=("model",)))
    no_double_count = reported_spend(BudgetReportSelectionV1(grouped, grouped))
    assert no_double_count is not None and no_double_count.total is None


def test_counts_only_report_explains_absent_cost_instead_of_missing_currency() -> None:
    from agentmonitor.modules.capacity.domain.budget_account_spend import reported_spend

    stored = _report(1, None)
    counts_only = replace(
        stored,
        report=replace(stored.report, currency=None, empty_means_zero=False),
    )
    result = reported_spend(BudgetReportSelectionV1(counts_only, counts_only))
    assert result is not None and result.total is None
    assert result.reason_code == "cost_not_reported"

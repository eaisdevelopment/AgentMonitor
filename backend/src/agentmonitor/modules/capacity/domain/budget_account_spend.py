"""Exact selected-report spend, independent from cross-resource pool aggregation."""

from agentmonitor.contracts.budget_query_v1 import BudgetReportedSpendV1
from agentmonitor.contracts.capacity_v1 import BudgetReportSelectionV1
from agentmonitor.contracts.common_quantity_v1 import CanonicalDecimalV1, ExactMoneyV1
from agentmonitor.modules.capacity.domain.budget_money import (
    BudgetMoneyError,
    sum_money,
)


def reported_spend(selection: BudgetReportSelectionV1) -> BudgetReportedSpendV1 | None:
    selected = selection.current or selection.latest_attempt
    if selected is None:
        return None
    report = selected.report
    reason = None
    if selection.current is None or report.completeness != "complete":
        reason = "report_incomplete"
    elif report.covered_period != report.requested_period:
        reason = "report_coverage_incomplete"
    elif report.grouping:
        reason = "breakdown_not_total"
    elif report.currency is None:
        reason = "currency_unavailable"
    elif not report.cost_buckets and not report.empty_means_zero:
        reason = "cost_not_reported"
    if reason:
        return BudgetReportedSpendV1(selected.report_id, None, reason)
    assert report.currency is not None
    try:
        total = (
            sum_money(tuple(bucket.amount for bucket in report.cost_buckets))
            if report.cost_buckets
            else ExactMoneyV1(CanonicalDecimalV1("0", 0), report.currency)
        )
    except (BudgetMoneyError, ValueError):
        return BudgetReportedSpendV1(selected.report_id, None, "cost_total_unavailable")
    return BudgetReportedSpendV1(selected.report_id, total, "reported_spend_calculated")

"""Exact selected-period identity for the admitted ungrouped billing cost read."""

from datetime import timedelta

from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1
from agentmonitor.contracts.collection_control_v1 import BillingBudgetReportContextV1


def billing_cost_context(period: BudgetPeriodV1) -> BillingBudgetReportContextV1:
    """Preserve the selection; the published context rejects unsupported bounds."""
    return BillingBudgetReportContextV1(
        "7d" if period.end - period.start == timedelta(days=7) else "30d",
        period.start,
        period.end,
        "cost",
        (),
    )

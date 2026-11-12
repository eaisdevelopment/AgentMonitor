"""Capture the existing default cost interval once, before durable admission."""

from datetime import datetime, timedelta

from agentmonitor.contracts.collection_control_v1 import BillingBudgetReportContextV1


def completed_billing_cost_context(
    requested_at: datetime,
) -> BillingBudgetReportContextV1:
    end = requested_at.replace(hour=0, minute=0, second=0, microsecond=0)
    return BillingBudgetReportContextV1("7d", end - timedelta(days=7), end, "cost")

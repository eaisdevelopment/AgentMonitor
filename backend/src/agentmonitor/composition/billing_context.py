"""Capture the existing default cost interval once, before durable admission."""

from datetime import datetime, timedelta
from typing import Literal, cast

from agentmonitor.contracts.collection_control_v1 import BillingBudgetReportContextV1


def completed_billing_cost_context(
    requested_at: datetime,
    *,
    range_key: str = "7d",
) -> BillingBudgetReportContextV1:
    if range_key not in {"7d", "30d"}:
        raise ValueError("billing_context_range_invalid")
    end = requested_at.replace(hour=0, minute=0, second=0, microsecond=0)
    return BillingBudgetReportContextV1(
        cast(Literal["7d", "30d"], range_key),
        end - timedelta(days=7 if range_key == "7d" else 30),
        end,
        "cost",
    )


def billing_cost_operation_families(provider_key: str) -> tuple[str, ...]:
    """Closed claim allowlist shared by legacy and captured cost admissions."""
    from agentmonitor.composition.billing_run import (
        ANTHROPIC_COST_30D_OPERATION_FAMILY_V1,
        ANTHROPIC_COST_OPERATION_FAMILY_V1,
    )
    from agentmonitor.composition.openai_billing_run import (
        OPENAI_COST_30D_OPERATION_FAMILY_V1,
        OPENAI_COST_OPERATION_FAMILY_V1,
    )

    if provider_key == "claude":
        return (
            ANTHROPIC_COST_OPERATION_FAMILY_V1,
            ANTHROPIC_COST_30D_OPERATION_FAMILY_V1,
        )
    if provider_key == "codex":
        return OPENAI_COST_OPERATION_FAMILY_V1, OPENAI_COST_30D_OPERATION_FAMILY_V1
    raise ValueError("billing_cost_provider_invalid")

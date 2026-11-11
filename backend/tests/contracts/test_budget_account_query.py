"""Account financial query identity and exact reported-spend boundary."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.contracts import capacity_v1 as capacity
from agentmonitor.contracts.common_v1 import OpaqueIdV1, QueryAvailabilityV1


def test_account_query_pins_period_and_availability_time() -> None:
    from agentmonitor.contracts.budget_query_v1 import AccountBudgetCurrentV1

    now = datetime(2026, 11, 11, tzinfo=UTC)
    result = AccountBudgetCurrentV1(
        account_id=OpaqueIdV1("account"),
        period=capacity.BudgetPeriodV1(now - timedelta(days=7), now),
        as_of=now,
        availability=QueryAvailabilityV1("available", "billing_not_configured", now),
        resources=(),
    )
    with pytest.raises(ValueError, match="budget_account_query_invalid"):
        replace(result, as_of=now - timedelta(days=8))
    with pytest.raises(ValueError, match="budget_account_query_invalid"):
        replace(result, as_of=now + timedelta(seconds=1))

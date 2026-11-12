"""Pure selected-period billing status context; no provider or repository I/O."""

from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1


@pytest.mark.parametrize("days", [7, 30])
@pytest.mark.parametrize("age", [0, 45])
def test_billing_collection_context_preserves_exact_selected_interval(
    days: int, age: int
) -> None:
    from agentmonitor.modules.capacity.domain.budget_collection_context import (
        billing_cost_context,
    )

    end = datetime(2026, 11, 12, tzinfo=UTC) - timedelta(days=age)
    period = BudgetPeriodV1(end - timedelta(days=days), end)
    context = billing_cost_context(period)
    assert context.range_key == f"{days}d"
    assert (context.interval_start, context.interval_end) == (period.start, period.end)
    assert context.source_category == "cost"
    assert context.grouping == ()


@pytest.mark.parametrize("days", [1, 8, 29, 31])
def test_unadmitted_billing_width_has_no_collection_context(days: int) -> None:
    from agentmonitor.modules.capacity.domain.budget_collection_context import (
        billing_cost_context,
    )

    end = datetime(2026, 11, 12, tzinfo=UTC)
    with pytest.raises(ValueError):
        billing_cost_context(BudgetPeriodV1(end - timedelta(days=days), end))


def test_non_midnight_interval_is_not_shifted_to_a_different_selection() -> None:
    from agentmonitor.modules.capacity.domain.budget_collection_context import (
        billing_cost_context,
    )

    end = datetime(2026, 11, 12, 12, tzinfo=UTC)
    with pytest.raises(ValueError):
        billing_cost_context(BudgetPeriodV1(end - timedelta(days=7), end))

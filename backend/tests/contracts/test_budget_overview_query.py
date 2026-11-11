"""Pure Overview selection contract; no constructed data crosses I/O."""

from datetime import UTC, datetime, timedelta
from importlib import import_module

import pytest
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1


def test_overview_selection_is_bounded_and_distinguishes_all_from_no_groups() -> None:
    module = import_module("agentmonitor.contracts.budget_query_v1")
    query = getattr(module, "BudgetOverviewQueryV1", None)
    assert query is not None, "budget_overview_selection_contract_missing"
    now = datetime(2026, 11, 11, tzinfo=UTC)
    period = BudgetPeriodV1(now - timedelta(days=7), now)
    assert query(period, now).organization_ids is None
    assert query(period, now, organization_ids=()).organization_ids == ()
    for limit in (0, 201, True):
        with pytest.raises(ValueError, match="budget_overview_query_invalid"):
            query(period, now, limit=limit)
    with pytest.raises(ValueError, match="budget_overview_query_invalid"):
        query(period, now - timedelta(seconds=1))

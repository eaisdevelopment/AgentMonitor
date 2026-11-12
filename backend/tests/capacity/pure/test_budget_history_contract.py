"""History request bounds are pure contract behavior, without external fixtures."""

from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.contracts import budget_query_v1 as contracts
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1


@pytest.mark.parametrize("limit", [0, 201, True])
def test_history_contract_rejects_invalid_page_size(limit: int) -> None:
    end = datetime(2026, 11, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match="budget_history_query_invalid"):
        contracts.BudgetHistoryQueryV1(
            OpaqueIdV1("account"),
            OpaqueIdV1("resource"),
            OpaqueIdV1("report"),
            BudgetPeriodV1(end - timedelta(days=7), end),
            end,
            limit=limit,
        )


def test_history_contract_rejects_period_after_snapshot() -> None:
    end = datetime(2026, 11, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match="budget_history_query_invalid"):
        contracts.BudgetHistoryQueryV1(
            OpaqueIdV1("account"),
            OpaqueIdV1("resource"),
            OpaqueIdV1("report"),
            BudgetPeriodV1(end - timedelta(days=7), end),
            end - timedelta(seconds=1),
        )


def test_history_row_requires_the_fact_of_its_declared_kind() -> None:
    with pytest.raises(ValueError, match="budget_history_row_invalid"):
        contracts.BudgetHistoryRowV1(kind="cost", cost=None, usage=None)

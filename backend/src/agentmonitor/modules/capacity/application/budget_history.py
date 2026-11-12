"""Read a bounded page from an authorized immutable financial selection."""

from agentmonitor.contracts.budget_query_v1 import (
    BudgetHistoryQueryV1,
    BudgetHistoryResultV1,
    BudgetSelectedReportPortV1,
)
from agentmonitor.modules.capacity.domain.budget_history import history_result


class ListBudgetHistoryV1:
    def __init__(self, selected: BudgetSelectedReportPortV1) -> None:
        self._selected = selected

    def __call__(self, query: BudgetHistoryQueryV1) -> BudgetHistoryResultV1 | None:
        selected = self._selected(
            query.account_id,
            query.resource_id,
            query.report_id,
            period=query.period,
            as_of=query.as_of,
        )
        if selected is None:
            return None
        return history_result(selected, query)

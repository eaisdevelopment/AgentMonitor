"""Read a bounded page from an authorized immutable financial selection."""

from agentmonitor.contracts.budget_forecast_v1 import BudgetSourceEvidencePortV1
from agentmonitor.contracts.budget_query_v1 import (
    BudgetHistoryQueryV1,
    BudgetHistoryResultV1,
    BudgetSelectedReportPortV1,
)
from agentmonitor.modules.capacity.domain.budget_history import history_result


class ListBudgetHistoryV1:
    def __init__(
        self,
        selected: BudgetSelectedReportPortV1,
        source_evidence: BudgetSourceEvidencePortV1 | None = None,
    ) -> None:
        self._selected = selected
        self._source_evidence = source_evidence

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
        evidence = (
            self._source_evidence(selected.report) if self._source_evidence else None
        )
        result = history_result(selected, query, evidence=evidence)
        if (
            self._source_evidence is not None
            and self._selected(
                query.account_id,
                query.resource_id,
                query.report_id,
                period=query.period,
                as_of=query.as_of,
            )
            != selected
        ):
            return None
        return result

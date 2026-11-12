"""Discover retained original-scope reports through public repository ports."""

from collections.abc import Callable

from agentmonitor.contracts.capacity_v1 import (
    BudgetReportHistoryQueryV1,
    BudgetReportRepositoryV1,
    BudgetReportViewV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1, QueryPageV1
from agentmonitor.contracts.registry_v1 import AccountViewV1
from agentmonitor.modules.capacity.application.queries import CapacityQueryUnavailableV1


class ListBudgetReportsV1:
    def __init__(
        self,
        accounts: Callable[[OpaqueIdV1], AccountViewV1 | None],
        reports: BudgetReportRepositoryV1,
    ) -> None:
        self._accounts = accounts
        self._reports = reports

    def __call__(
        self, query: BudgetReportHistoryQueryV1
    ) -> QueryPageV1[BudgetReportViewV1] | None:
        account = self._accounts(query.account_id)
        if account is None:
            return None
        result = self._reports.list_reports(query)
        if self._accounts(query.account_id) != account:
            raise CapacityQueryUnavailableV1("budget_report_registry_changed")
        return result

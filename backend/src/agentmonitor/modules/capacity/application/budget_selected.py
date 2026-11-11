"""Read an explicit retained financial report through public ports only."""

from collections.abc import Callable
from datetime import datetime

from agentmonitor.contracts.budget_query_v1 import BudgetSelectedReportV1
from agentmonitor.contracts.capacity_v1 import (
    BudgetPeriodV1,
    BudgetReportRepositoryV1,
    BudgetReportSelectionV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import AccountViewV1
from agentmonitor.modules.capacity.domain.budget_account_spend import (
    matches_selected_report,
    reported_spend,
)


class GetSelectedBudgetReportV1:
    def __init__(
        self,
        accounts: Callable[[OpaqueIdV1], AccountViewV1 | None],
        reports: BudgetReportRepositoryV1,
    ) -> None:
        self._accounts = accounts
        self._reports = reports

    def __call__(
        self,
        account_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
        report_id: OpaqueIdV1,
        *,
        period: BudgetPeriodV1,
        as_of: datetime,
    ) -> BudgetSelectedReportV1 | None:
        # Retained history may belong to an earlier scope or binding. It is
        # explicitly selected history, never proof of current access or funds.
        account = self._accounts(account_id)
        if account is None:
            return None
        stored = self._reports.get_report(account_id, report_id)
        if not matches_selected_report(
            stored,
            account_id=account_id,
            resource_id=resource_id,
            report_id=report_id,
            period=period,
            as_of=as_of,
        ):
            return None
        assert stored is not None
        spend = reported_spend(
            BudgetReportSelectionV1(
                stored if stored.report.completeness == "complete" else None, stored
            )
        )
        assert spend is not None
        if self._accounts(account_id) != account:
            return None
        return BudgetSelectedReportV1(stored, spend, as_of)

"""Read financial account state through published metadata/report/run ports."""

from datetime import datetime

from agentmonitor.contracts.budget_query_v1 import (
    AccountBudgetCurrentV1,
    BudgetCollectionStatePortV1,
    BudgetResourceCurrentV1,
)
from agentmonitor.contracts.capacity_v1 import (
    BudgetCurrentQueryV1,
    BudgetCurrentReportsPortV1,
    BudgetPeriodV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1, QueryAvailabilityV1
from agentmonitor.contracts.registry_billing_v1 import BillingConnectionPortV1
from agentmonitor.modules.capacity.domain.budget_account_spend import reported_spend


class GetAccountBudgetCurrentV1:
    def __init__(
        self,
        registry: BillingConnectionPortV1,
        reports: BudgetCurrentReportsPortV1,
        collection: BudgetCollectionStatePortV1,
    ) -> None:
        self._registry = registry
        self._reports = reports
        self._collection = collection

    def __call__(
        self,
        account_id: OpaqueIdV1,
        *,
        period: BudgetPeriodV1,
        as_of: datetime,
    ) -> AccountBudgetCurrentV1 | None:
        # Validate the public selection before invoking any I/O port.
        empty = AccountBudgetCurrentV1(
            account_id,
            period,
            as_of,
            QueryAvailabilityV1(
                "unavailable", "budget_account_query_unavailable", as_of
            ),
            (),
        )
        try:
            status = self._registry.get(account_id)
        except ValueError:
            return empty
        if status is None:
            return None
        resources = []
        for connection in status.connections:
            result = self._reports.get_current_reports(
                BudgetCurrentQueryV1(
                    account_id,
                    connection.resource_id,
                    connection.scope_generation,
                    period,
                    as_of,
                )
            )
            try:
                latest = self._collection.get_latest_budget_run(
                    account_id,
                    connection.resource_id,
                    connection.scope_generation,
                    as_of,
                )
                collection_availability = QueryAvailabilityV1(
                    "available",
                    "budget_collection_read"
                    if latest
                    else "budget_collection_not_started",
                    as_of,
                )
            except ValueError:
                latest = None
                collection_availability = QueryAvailabilityV1(
                    "unavailable",
                    "budget_collection_query_unavailable",
                    as_of,
                )
            spend = tuple(
                value
                for selection in result.items
                if (value := reported_spend(selection)) is not None
            )
            resources.append(
                BudgetResourceCurrentV1(
                    connection,
                    result.items,
                    result.availability,
                    spend,
                    latest,
                    collection_availability,
                )
            )
        # A concurrent scope/archive/rotation change invalidates the assembled
        # metadata snapshot; it must not relabel old money as the new scope.
        try:
            if self._registry.get(account_id) != status:
                return AccountBudgetCurrentV1(
                    account_id,
                    period,
                    as_of,
                    QueryAvailabilityV1(
                        "unavailable",
                        "budget_registry_changed",
                        as_of,
                    ),
                    (),
                )
        except ValueError:
            return empty
        return AccountBudgetCurrentV1(
            account_id,
            period,
            as_of,
            QueryAvailabilityV1(
                "available",
                "budget_account_read" if resources else "billing_not_configured",
                as_of,
            ),
            tuple(resources),
        )

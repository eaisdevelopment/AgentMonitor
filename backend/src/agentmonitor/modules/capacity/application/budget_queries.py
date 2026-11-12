"""Read financial account state through published metadata/report/run ports."""

from collections.abc import Callable
from datetime import datetime

from agentmonitor.contracts.budget_query_v1 import (
    AccountBudgetCurrentV1,
    AccountBudgetFundsPortV1,
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
from agentmonitor.contracts.registry_v1 import (
    ActiveCredentialBindingRefV1,
    CloudMonitoringTargetV1,
)
from agentmonitor.modules.capacity.application.cloud_budget_query import (
    cloud_budget_current,
)
from agentmonitor.modules.capacity.domain.budget_account_spend import reported_spend
from agentmonitor.modules.capacity.domain.budget_collection_context import (
    billing_cost_context,
)


class GetAccountBudgetCurrentV1:
    def __init__(
        self,
        registry: BillingConnectionPortV1,
        reports: BudgetCurrentReportsPortV1,
        collection: BudgetCollectionStatePortV1,
        funds: AccountBudgetFundsPortV1 | None = None,
        active_binding: Callable[[OpaqueIdV1], ActiveCredentialBindingRefV1 | None]
        | None = None,
        cloud_target: Callable[[OpaqueIdV1], CloudMonitoringTargetV1 | None]
        | None = None,
    ) -> None:
        self._registry = registry
        self._reports = reports
        self._collection = collection
        self._funds = funds
        self._active_binding = active_binding
        self._cloud_target = cloud_target

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
        try:
            binding = (
                None
                if self._active_binding is None
                else self._active_binding(account_id)
            )
            cloud = (
                None if self._cloud_target is None else self._cloud_target(account_id)
            )
        except ValueError:
            return empty
        if cloud is not None and (
            cloud.account_id != account_id
            or cloud.lifecycle == "active"
            and cloud.binding != binding
        ):
            return empty
        resources = []
        try:
            collection_context = billing_cost_context(period)
        except ValueError:
            collection_context = None
        for connection in status.connections:
            result = self._reports.get_current_reports(
                BudgetCurrentQueryV1(
                    account_id,
                    connection.resource_id,
                    connection.scope_generation,
                    period,
                    as_of,
                    active_binding=binding,
                )
            )
            try:
                if collection_context is None:
                    raise ValueError("budget_billing_context_unavailable")
                latest = self._collection.get_latest_budget_run(
                    account_id,
                    connection.resource_id,
                    connection.scope_generation,
                    as_of,
                    report_context=collection_context,
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
                    "budget_billing_context_unavailable"
                    if collection_context is None
                    else "budget_collection_query_unavailable",
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
        cloud_resources = (
            (
                cloud_budget_current(
                    cloud, self._reports, self._collection, period=period, as_of=as_of
                ),
            )
            if cloud is not None and cloud.lifecycle == "active"
            else ()
        )
        funds = None if self._funds is None else self._funds(account_id, as_of=as_of)
        # A concurrent scope/archive/rotation change invalidates the assembled
        # metadata snapshot; it must not relabel old money as the new scope.
        try:
            current_binding = (
                None
                if self._active_binding is None
                else self._active_binding(account_id)
            )
            current_cloud = (
                None if self._cloud_target is None else self._cloud_target(account_id)
            )
            if (
                self._registry.get(account_id) != status
                or current_binding != binding
                or current_cloud != cloud
            ):
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
                "budget_account_read"
                if resources
                or cloud_resources
                or funds is not None
                and funds.availability.reason_code != "funds_source_unavailable"
                else "billing_not_configured",
                as_of,
            ),
            tuple(resources),
            funds,
            cloud_resources,
        )

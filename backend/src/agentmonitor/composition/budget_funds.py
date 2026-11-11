"""Read existing funds through public registry/capacity ports, without collection."""

from datetime import datetime

from agentmonitor.adapters.providers.ollama.api.funds_projection import project_funds
from agentmonitor.contracts.budget_query_v1 import AccountBudgetFundsV1
from agentmonitor.contracts.capacity_v1 import QuotaWindowViewV2
from agentmonitor.contracts.common_v1 import OpaqueIdV1, QueryAvailabilityV1
from agentmonitor.contracts.registry_v1 import CapacityScopeMembershipQueryV2
from agentmonitor.modules.capacity.application.queries import ListQuotaWindowsV1


class StoredAccountBudgetFundsV1:
    def __init__(
        self, registry: CapacityScopeMembershipQueryV2, windows: ListQuotaWindowsV1
    ) -> None:
        self._registry = registry
        self._windows = windows

    def __call__(
        self, account_id: OpaqueIdV1, *, as_of: datetime
    ) -> AccountBudgetFundsV1:
        # Validate time/identity before any I/O.
        empty = AccountBudgetFundsV1(
            account_id,
            as_of,
            QueryAvailabilityV1("unavailable", "funds_query_unavailable", as_of),
            (),
            0,
        )
        try:
            membership = self._registry("account", account_id)
            if membership.completeness_state != "complete":
                return empty
            components = []
            sources = 0
            for resource in membership.cloud_resources:
                if (
                    resource.account_id != account_id
                    or resource.provider_key != "ollama"
                ):
                    continue
                sources += 1
                for window in self._windows.for_scope(
                    account_id, resource.resource_id, "subscription.quota", as_of=as_of
                ):
                    if not isinstance(window, QuotaWindowViewV2):
                        continue
                    if (
                        window.subject.account_id != account_id
                        or window.subject.resource_id != resource.resource_id
                        or window.subject.provider_target != resource.provider_target
                    ):
                        return empty
                    component = project_funds(window, as_of=as_of)
                    if component is not None:
                        components.append(component)
            if self._registry("account", account_id) != membership:
                return AccountBudgetFundsV1(
                    account_id,
                    as_of,
                    QueryAvailabilityV1("unavailable", "funds_registry_changed", as_of),
                    (),
                    membership.registry_revision,
                )
            return AccountBudgetFundsV1(
                account_id,
                as_of,
                QueryAvailabilityV1(
                    "partial" if components else "unavailable",
                    "funds_scope_unresolved"
                    if components
                    else (
                        "funds_observations_absent"
                        if sources
                        else "funds_source_unavailable"
                    ),
                    as_of,
                ),
                tuple(components),
                membership.registry_revision,
            )
        except ValueError:
            return empty

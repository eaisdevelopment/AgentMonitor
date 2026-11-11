"""Read existing funds through public registry/capacity ports, without collection."""

from collections.abc import Callable
from datetime import datetime

from agentmonitor.adapters.providers.ollama.api.funds_projection import project_funds
from agentmonitor.contracts.budget_query_v1 import (
    AccountBudgetFundsV1,
    BudgetFundComponentV1,
)
from agentmonitor.contracts.capacity_v1 import QuotaWindowViewV2
from agentmonitor.contracts.collection_control_v1 import CollectionRunViewV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1, QueryAvailabilityV1
from agentmonitor.contracts.registry_v1 import (
    ActiveCredentialBindingRefV1,
    CapacityScopeMembershipQueryV2,
)
from agentmonitor.modules.capacity.application.queries import ListQuotaWindowsV1


def funds_match_active_binding(
    component: BudgetFundComponentV1,
    binding: ActiveCredentialBindingRefV1 | None,
    run: CollectionRunViewV1 | None,
    *,
    as_of: datetime,
) -> bool:
    """Prove the stored observation belongs to the current cloud generation.

    M02 advances the account generation on activation. M6 cloud admission binds
    that generation to this account/resource; M04 retains it and the committed
    observation IDs. A generation is access lineage, never financial identity.
    """
    return (
        binding is not None
        and run is not None
        and component.subject.account_id == binding.account_id
        and run.run_id == component.collection_run_id
        and run.account_id == binding.account_id
        and run.resource_id == component.subject.resource_id
        and run.provider_key == component.subject.provider_key
        and run.source_id == component.provenance.source_id
        and run.capability_id == component.provenance.capability_id
        and run.target_generation == binding.generation
        and run.state in {"succeeded", "partial"}
        and run.completed_at is not None
        and run.completed_at <= as_of
        and component.observation_id in run.observation_ids
    )


class StoredAccountBudgetFundsV1:
    def __init__(
        self,
        registry: CapacityScopeMembershipQueryV2,
        windows: ListQuotaWindowsV1,
        *,
        active_binding: Callable[[OpaqueIdV1], ActiveCredentialBindingRefV1 | None]
        | None = None,
        get_run: Callable[[OpaqueIdV1], CollectionRunViewV1 | None] | None = None,
    ) -> None:
        self._registry = registry
        self._windows = windows
        self._active_binding = active_binding
        self._get_run = get_run

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
            binding = (
                None
                if self._active_binding is None
                else self._active_binding(account_id)
            )
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
                        run = (
                            None
                            if self._get_run is None
                            else self._get_run(component.collection_run_id)
                        )
                        if not funds_match_active_binding(
                            component, binding, run, as_of=as_of
                        ):
                            return AccountBudgetFundsV1(
                                account_id,
                                as_of,
                                QueryAvailabilityV1(
                                    "unavailable", "funds_lineage_unavailable", as_of
                                ),
                                (),
                                membership.registry_revision,
                            )
                        components.append(component)
            current_binding = (
                None
                if self._active_binding is None
                else self._active_binding(account_id)
            )
            if (
                self._registry("account", account_id) != membership
                or current_binding != binding
            ):
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

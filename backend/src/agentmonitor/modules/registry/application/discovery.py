"""Provider-neutral discovery reconciliation application boundary."""

from datetime import datetime
from typing import Protocol

from agentmonitor.contracts.common_v1 import QueryAvailabilityV1, QueryPageV1
from agentmonitor.contracts.provider_system_v1 import DiscoveryOutcomeV1
from agentmonitor.contracts.registry_v1 import (
    DiscoveryCandidateViewV1 as DiscoveryCandidateViewV1,
)
from agentmonitor.contracts.registry_v1 import (
    DiscoveryReconciliationViewV1 as DiscoveryReconciliationViewV1,
)
from agentmonitor.contracts.registry_v1 import (
    ProviderInstallationViewV1 as ProviderInstallationViewV1,
)
from agentmonitor.contracts.registry_v1 import (
    ReconcileProviderDiscoveryV1 as ReconcileProviderDiscoveryPortV1,
)
from agentmonitor.modules.registry.application.accounts import (
    RegistryQueryUnavailableV1,
)


class DiscoveryRepositoryPortV1(Protocol):
    def reconcile_discovery(
        self, outcome: DiscoveryOutcomeV1, *, reconciled_at: datetime
    ) -> DiscoveryReconciliationViewV1: ...

    def list_discovery_candidates(
        self, provider_key: str | None = None
    ) -> tuple[DiscoveryCandidateViewV1, ...]: ...

    def list_provider_installations(
        self,
        provider_key: str | None = None,
        page_size: int = 100,
        after_key: str | None = None,
    ) -> tuple[ProviderInstallationViewV1, ...]: ...


class ReconcileProviderDiscoveryV1(ReconcileProviderDiscoveryPortV1):
    """Accept only successful/partial typed M03 outcomes; never raw payloads."""

    def __init__(self, repository: DiscoveryRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(
        self, outcome: DiscoveryOutcomeV1, *, reconciled_at: datetime
    ) -> DiscoveryReconciliationViewV1:
        if not isinstance(outcome, DiscoveryOutcomeV1) or outcome.state not in {
            "success",
            "partial",
        }:
            raise ValueError("registry_discovery_outcome_invalid")
        if outcome.value is None:
            raise ValueError("registry_discovery_outcome_invalid")
        return self._repository.reconcile_discovery(
            outcome, reconciled_at=reconciled_at
        )


class ListDiscoveryCandidatesV1:
    def __init__(self, repository: DiscoveryRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(
        self, provider_key: str | None = None
    ) -> tuple[DiscoveryCandidateViewV1, ...]:
        return self._repository.list_discovery_candidates(provider_key)


class ListProviderInstallationsV1:
    """Expose only the M02 safe installation view through a published port."""

    def __init__(self, repository: DiscoveryRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(
        self, provider_key: str | None = None
    ) -> tuple[ProviderInstallationViewV1, ...]:
        return self._repository.list_provider_installations(provider_key)

    def page(
        self,
        provider_key: str | None,
        *,
        as_of: datetime,
        limit: int,
        after_key: str | None = None,
    ) -> QueryPageV1[ProviderInstallationViewV1]:
        try:
            rows = self._repository.list_provider_installations(
                provider_key, limit + 1, after_key
            )
        except ValueError:
            raise RegistryQueryUnavailableV1("registry_query_unavailable") from None
        has_more = len(rows) > limit
        items = rows[:limit]
        return QueryPageV1(
            items,
            limit,
            has_more,
            items[-1].provider_installation_id.value if has_more else None,
            QueryAvailabilityV1("available", "registry_query_complete", as_of),
        )

"""Reconcile the exact real Ollama CLI installation into M02 registry state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.ollama.installation_discovery import (
    discover_ollama_installation_v1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import DiscoveryOutcomeV1
from agentmonitor.modules.registry.application.discovery import (
    DiscoveryCandidateViewV1,
    DiscoveryReconciliationViewV1,
    ProviderInstallationViewV1,
    ReconcileProviderDiscoveryV1,
)


class OllamaInstallationReconciliationErrorV1(RuntimeError):
    """Closed installation reconciliation failure without provider output."""


@dataclass(frozen=True, slots=True)
class OllamaInstallationReconciliationResultV1:
    provider_installation_id: OpaqueIdV1
    provider_version: str
    replay_verified: bool


class _InstallationOnlyDiscoveryRepositoryV1:
    def __init__(self, repository: SqliteRegistryRepositoryV1) -> None:
        self._repository = repository

    def reconcile_discovery(
        self, outcome: DiscoveryOutcomeV1, *, reconciled_at: datetime
    ) -> DiscoveryReconciliationViewV1:
        return self._repository.reconcile_installation_only_discovery(
            outcome, reconciled_at=reconciled_at
        )

    def list_discovery_candidates(
        self, provider_key: str | None = None
    ) -> tuple[DiscoveryCandidateViewV1, ...]:
        return self._repository.list_discovery_candidates(provider_key)

    def list_provider_installations(
        self,
        provider_key: str | None = None,
        page_size: int = 100,
        after_key: str | None = None,
    ) -> tuple[ProviderInstallationViewV1, ...]:
        return self._repository.list_provider_installations(
            provider_key, page_size, after_key
        )


def reconcile_ollama_installation_v1(
    reference: DatabaseRefV1,
) -> OllamaInstallationReconciliationResultV1:
    """Reconcile one current real installation through the strict M02 port."""

    reference.validate()
    outcome = discover_ollama_installation_v1()
    if (
        outcome.state != "success"
        or outcome.value is None
        or outcome.provenance is None
        or outcome.value.accounts != ()
        or len(outcome.value.installations) != 1
    ):
        raise OllamaInstallationReconciliationErrorV1(
            "ollama_installation_discovery_invalid"
        )
    discovered = outcome.value.installations[0]
    if (
        discovered.provider_key != "ollama"
        or discovered.installation_ref.value != "ollama-installation-primary"
        or discovered.product_version is None
        or discovered.product_version != outcome.provenance.provider_version
    ):
        raise OllamaInstallationReconciliationErrorV1(
            "ollama_installation_discovery_invalid"
        )
    repository = _InstallationOnlyDiscoveryRepositoryV1(
        SqliteRegistryRepositoryV1(reference)
    )
    reconciled = ReconcileProviderDiscoveryV1(repository)(
        outcome, reconciled_at=datetime.now(UTC)
    )
    if len(reconciled.installations) != 1:
        raise OllamaInstallationReconciliationErrorV1(
            "ollama_installation_reconciliation_invalid"
        )
    return OllamaInstallationReconciliationResultV1(
        reconciled.installations[0].provider_installation_id,
        discovered.product_version,
        True,
    )

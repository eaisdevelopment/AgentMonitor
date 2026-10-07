"""Fail-closed reconciliation of the admitted Claude installation into M02."""

import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.claude.installation import (
    ClaudeInstallationUnavailable,
)
from agentmonitor.adapters.providers.claude.installation_discovery import (
    discover_claude_installation_v1,
)
from agentmonitor.composition.iam_operator import (
    OperatorQuiescenceError,
    exclusive_service_quiescence,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import DiscoveryOutcomeV1
from agentmonitor.modules.registry.application.discovery import (
    DiscoveryCandidateViewV1,
    DiscoveryReconciliationViewV1,
    ProviderInstallationViewV1,
    ReconcileProviderDiscoveryV1,
)


class ClaudeInstallationReconciliationErrorV1(RuntimeError):
    """Closed operator failure without paths, identities, or provider output."""


@dataclass(frozen=True, slots=True)
class ClaudeInstallationReconciliationResultV1:
    provider_installation_id: OpaqueIdV1
    provider_version: str
    replay_verified: bool


class _InstallationOnlyDiscoveryRepositoryV1:
    """Route the published use case to M02's stricter internal transaction."""

    def __init__(self, repository: SqliteRegistryRepositoryV1) -> None:
        self._repository = repository

    def reconcile_discovery(
        self, outcome: DiscoveryOutcomeV1, *, reconciled_at: datetime
    ) -> DiscoveryReconciliationViewV1:
        return self._repository.reconcile_installation_only_discovery(
            outcome,
            reconciled_at=reconciled_at,
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
            provider_key,
            page_size,
            after_key,
        )


def reconcile_claude_installation_v1(
    reference: DatabaseRefV1,
) -> ClaudeInstallationReconciliationResultV1:
    """Reconcile one real A01 installation outcome in one guarded transaction."""
    reference.validate()
    outcome = discover_claude_installation_v1()
    if (
        outcome.state != "success"
        or outcome.value is None
        or outcome.provenance is None
        or outcome.value.accounts != ()
        or len(outcome.value.installations) != 1
    ):
        raise ClaudeInstallationReconciliationErrorV1(
            "claude_installation_discovery_invalid"
        )
    discovered = outcome.value.installations[0]
    if (
        discovered.provider_key != "claude"
        or discovered.installation_ref.value != "claude-installation-default"
        or discovered.product_version is None
        or discovered.product_version != outcome.provenance.provider_version
    ):
        raise ClaudeInstallationReconciliationErrorV1(
            "claude_installation_discovery_invalid"
        )

    repository = _InstallationOnlyDiscoveryRepositoryV1(
        SqliteRegistryRepositoryV1(reference)
    )
    reconciled = ReconcileProviderDiscoveryV1(repository)(
        outcome,
        reconciled_at=datetime.now(UTC),
    )
    installation = reconciled.installations[0]
    return ClaudeInstallationReconciliationResultV1(
        installation.provider_installation_id,
        discovered.product_version,
        True,
    )


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 2 or arguments[0] != "--data-root":
        print("invalid_operator_arguments")
        return 2
    root = Path(arguments[1])
    if not root.is_absolute():
        print(
            "CLAUDE INSTALLATION RECONCILIATION: BLOCKED — absolute data root required"
        )
        return 3
    try:
        reference = DatabaseRefV1(root / "agentmonitor.db", root)
        with exclusive_service_quiescence(root, reference):
            reconcile_claude_installation_v1(reference)
    except ClaudeInstallationUnavailable:
        print(
            "CLAUDE INSTALLATION RECONCILIATION: BLOCKED — "
            "admitted installation unavailable"
        )
        return 3
    except OperatorQuiescenceError:
        print(
            "CLAUDE INSTALLATION RECONCILIATION: BLOCKED — service quiescence required"
        )
        return 3
    except (OSError, RuntimeError, TypeError, ValueError):
        print(
            "CLAUDE INSTALLATION RECONCILIATION: FAILED — "
            "registry reconciliation unavailable"
        )
        return 1
    print(
        "CLAUDE INSTALLATION RECONCILIATION: PASSED — "
        "current admitted installation registered"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

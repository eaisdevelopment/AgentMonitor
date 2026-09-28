"""Real Claude fleet reconciliation over file-backed SQLite.

The fleet input is deliberately composed from real provider outcomes. This
test does not manufacture account or provider observations; absent owner
profiles remain a truthful Not Run condition in the live runbook.
"""

from datetime import UTC, datetime
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.claude.adapter import ClaudeAdapterV1
from agentmonitor.adapters.providers.claude.installation import (
    discover_default_installation,
)
from agentmonitor.modules.registry.application.discovery import (
    ReconcileProviderDiscoveryV1,
)


def test_real_claude_outcome_reconciles_into_real_registry(tmp_path: Path) -> None:
    """FR-ACC-005/FR-ORG-003: one available owner outcome is durable and safe."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    installation = discover_default_installation()
    outcome = ClaudeAdapterV1(installation).discover_owner_confirmed_default(
        operation_id="m4-fleet-real-discovery",
        correlation_id="m4-fleet-real-correlation",
        account_ref="claude-account-owner-confirmed",
        profile_ref="claude-profile-default-read-only",
        resource_ref="claude-subscription-current",
    )

    assert outcome.state in {"success", "partial"}
    assert outcome.value is not None
    reconciled = ReconcileProviderDiscoveryV1(SqliteRegistryRepositoryV1(reference))(
        outcome, reconciled_at=datetime.now(UTC)
    )

    assert len(reconciled.installations) == 1
    assert len(reconciled.candidates) == 1
    assert reconciled.candidates[0].owner_action_required is True
    assert SqliteRegistryRepositoryV1(reference).list_discovery_candidates("claude")

"""Real Claude discovery and M02 owner-confirmed registry persistence."""

import hashlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.composition.claude_live_monitoring import (
    OWNER_PRINCIPAL_ID,
    OWNER_PROFILE_REF,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    ConfirmIdentityAssociationCommandV1,
    PrivateProfileLocatorRefV1,
)
from agentmonitor.modules.registry.application.accounts import (
    ConfirmIdentityAssociationV1,
    EnrollMonitoringGraphCommandV1,
    EnrollMonitoringGraphV1,
)
from agentmonitor.modules.registry.application.organizations import (
    RegistryCommandConflictV1,
)

if TYPE_CHECKING:
    from backend.tests.integration.conftest import RealClaudeMonitoringContextV1


def test_real_claude_candidate_requires_owner_confirmation(
    real_claude_monitoring_context: "RealClaudeMonitoringContextV1",
) -> None:
    """M02-LIVE-005: real A01 evidence remains owner-assisted, not identity."""
    result = real_claude_monitoring_context.result

    assert result.discovery_state in {"success", "partial"}
    assert result.discovered_account_count == 1
    assert result.discovery_owner_confirmation_required is True
    assert result.discovery_evidence_strength == "owner_confirmation_required"
    assert result.graph.candidate_before_confirmation.association_state == (
        "owner_confirmation_required"
    )
    assert result.graph.candidate_before_confirmation.evidence_classes == (
        "corroborated",
    )
    assert result.graph.account.identity_state == "owner_confirmed"


def test_real_candidate_rejects_stale_version_or_changed_evidence(
    real_claude_monitoring_context: "RealClaudeMonitoringContextV1",
) -> None:
    """M02-LIVE-006: real candidate optimistic concurrency fails closed."""
    context = real_claude_monitoring_context
    candidate = context.result.graph.candidate_before_confirmation
    confirm = ConfirmIdentityAssociationV1(
        SqliteRegistryRepositoryV1(context.reference)
    )

    with pytest.raises(
        RegistryCommandConflictV1, match="registry_candidate_version_conflict"
    ):
        confirm(
            ConfirmIdentityAssociationCommandV1(
                command_id=OpaqueIdV1("claude-owner-stale-confirmation"),
                principal_id=OpaqueIdV1(OWNER_PRINCIPAL_ID),
                candidate_id=candidate.candidate_id,
                # This view was captured before the original confirmation. The
                # persisted candidate has advanced, so replaying this reviewed
                # version must fail closed as stale.
                expected_candidate_record_version=candidate.record_version,
                friendly_name="Claude owner account",
                organization_id=None,
                evidence_set_digest=candidate.evidence_set_digest,
                requested_at=datetime.now(UTC),
            )
        )


def test_real_monitoring_graph_enrollment_replays_receipt_and_history(
    real_claude_monitoring_context: "RealClaudeMonitoringContextV1",
) -> None:
    """M02-LIVE-004: real owner graph is idempotent through the public port."""
    context = real_claude_monitoring_context
    result = context.result
    locator = OWNER_PROFILE_REF
    replay = EnrollMonitoringGraphV1(SqliteRegistryRepositoryV1(context.reference))(
        EnrollMonitoringGraphCommandV1(
            command_id=OpaqueIdV1("claude-owner-default-enrollment-v1"),
            principal_id=OpaqueIdV1(OWNER_PRINCIPAL_ID),
            account_id=result.graph.account.account_id,
            provider_installation_id=(
                result.graph.candidate_before_confirmation.provider_installation_id
            ),
            purpose="subscription",
            profile_locator_ref=PrivateProfileLocatorRefV1(locator),
            locator_fingerprint=hashlib.sha256(locator.encode()).hexdigest(),
            management_state="provider_default",
            compatibility_state="compatible",
            is_protected_default=True,
            resource_kind="subscription_pool",
            parent_resource_id=None,
            requested_at=datetime.now(UTC),
        )
    )

    assert replay == (result.graph.profile, result.graph.resource)
    assert result.graph.profile.account_id == result.graph.account.account_id
    assert result.graph.profile.is_protected_default is True
    assert result.graph.resource.account_id == result.graph.account.account_id

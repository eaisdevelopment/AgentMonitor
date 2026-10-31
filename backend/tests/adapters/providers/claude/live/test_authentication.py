"""Real Claude authentication-health and managed-reauth boundary checks."""

from datetime import UTC, datetime

from agentmonitor.adapters.providers.claude.authentication.health import (
    ClaudeAuthenticationHealthV1,
)
from agentmonitor.adapters.providers.claude.authentication.reauthentication import (
    ClaudeReauthenticationTargetV1,
    request_reauthentication,
)
from agentmonitor.adapters.providers.claude.installation import (
    discover_default_installation,
)
from agentmonitor.adapters.providers.claude.manifest import (
    CLAUDE_AUTH_DECISION_REFERENCE,
    CLAUDE_USAGE_SOURCE_ID,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    CapabilitySchemaVersionV1,
    ProviderOperationRequestHeaderV1,
    ProviderTargetV1,
    SourcePolicyV1,
)


def _request() -> ProviderOperationRequestHeaderV1:
    return ProviderOperationRequestHeaderV1(
        operation_id=OpaqueIdV1("live-claude-auth-health-operation"),
        correlation_id=OpaqueIdV1("live-claude-auth-health-correlation"),
        provider_key="claude",
        capability_id="authentication.health",
        capability_schema_version=CapabilitySchemaVersionV1(1, 0),
        target=ProviderTargetV1(
            provider_key="claude",
            installation_ref=OpaqueIdV1("claude-installation-default"),
            account_ref=OpaqueIdV1("claude-account-owner-confirmed"),
            profile_ref=OpaqueIdV1("claude-profile-default-read-only"),
            resource_ref=None,
            profile_protection="protected_default",
        ),
        requested_at=datetime.now(UTC),
        deadline_ms=30_000,
        source_policy=SourcePolicyV1(
            policy_ref=OpaqueIdV1("claude-auth-health-source-policy"),
            source_ids=(CLAUDE_USAGE_SOURCE_ID,),
            approved_fallbacks=(),
            experimental_grant_ref=None,
        ),
        access_grant_refs=(OpaqueIdV1("claude-default-profile-read-only"),),
    )


def test_real_claude_auth_health_uses_a_bounded_read_only_observation() -> None:
    """CLA-LIVE-011: current auth state is derived from a real read-only source."""
    installation = discover_default_installation()
    outcome = ClaudeAuthenticationHealthV1(installation)(_request())

    assert outcome.state in {
        "success",
        "partial",
        "reauthentication_required",
        "authorization_insufficient",
        "provider_unavailable",
        "deadline_exceeded",
    }
    if outcome.state in {"success", "partial"}:
        assert outcome.value is not None
        assert outcome.provenance is not None
        assert outcome.value.state in {
            "healthy",
            "unknown",
            "reauthentication_required",
            "revoked_or_disabled",
            "wrong_account_detected",
        }
        assert outcome.value.identity.state == "unresolved"
        assert outcome.provenance.source_id == CLAUDE_USAGE_SOURCE_ID
        assert outcome.provenance.provider_version == installation.provider_version
        assert outcome.provenance.decision_reference == CLAUDE_AUTH_DECISION_REFERENCE


def test_default_profile_reauthentication_is_rejected_before_provider_io() -> None:
    """CLA-LIVE-015: protected default profile is never sent to a reauth flow."""
    result = request_reauthentication(
        ClaudeReauthenticationTargetV1(
            profile_ref=OpaqueIdV1("claude-profile-default-read-only"),
            profile_protection="protected_default",
            expected_identity_available=True,
            owner_interaction_granted=True,
        )
    )

    assert result.state == "unavailable"
    assert result.reason_code == "protected_default_profile"
    assert result.provider_io_started is False

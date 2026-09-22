"""Live Claude subscription-quota acceptance against the default profile."""

from datetime import UTC, datetime

from agentmonitor.adapters.providers.claude.adapter import ClaudeAdapterV1
from agentmonitor.adapters.providers.claude.installation import (
    discover_default_installation,
)
from agentmonitor.adapters.providers.claude.manifest import CLAUDE_USAGE_SOURCE_ID
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    CapabilitySchemaVersionV1,
    ProviderOperationRequestHeaderV1,
    ProviderTargetV1,
    SourcePolicyV1,
)


def test_real_subscription_observation_has_current_structural_semantics() -> None:
    """CLA-LIVE-004: collect current values without retaining dynamic evidence."""
    installation = discover_default_installation()
    adapter = ClaudeAdapterV1(installation)
    request = ProviderOperationRequestHeaderV1(
        operation_id=OpaqueIdV1("live-claude-quota-operation"),
        correlation_id=OpaqueIdV1("live-claude-quota-correlation"),
        provider_key="claude",
        capability_id="subscription.quota",
        capability_schema_version=CapabilitySchemaVersionV1(1, 0),
        target=ProviderTargetV1(
            provider_key="claude",
            installation_ref=OpaqueIdV1("claude-installation-default"),
            account_ref=OpaqueIdV1("claude-account-owner-confirmed"),
            profile_ref=OpaqueIdV1("claude-profile-default-read-only"),
            resource_ref=OpaqueIdV1("claude-subscription-current"),
            profile_protection="protected_default",
        ),
        requested_at=datetime.now(UTC),
        deadline_ms=30_000,
        source_policy=SourcePolicyV1(
            policy_ref=OpaqueIdV1("claude-usage-source-policy"),
            source_ids=(CLAUDE_USAGE_SOURCE_ID,),
            approved_fallbacks=(),
            experimental_grant_ref=None,
        ),
        access_grant_refs=(OpaqueIdV1("claude-default-profile-read-only"),),
    )

    outcome = adapter.collect_subscription_quota(request)

    assert outcome.state in {"success", "partial"}
    assert outcome.value is not None
    assert outcome.provenance is not None
    assert outcome.value.account_ref == request.target.account_ref
    assert outcome.value.resource_ref == request.target.resource_ref
    assert outcome.provenance.source_id == CLAUDE_USAGE_SOURCE_ID
    assert outcome.provenance.provider_version == installation.provider_version
    assert 2 <= len(outcome.value.windows) <= 4
    assert len({window.window_key for window in outcome.value.windows}) == len(
        outcome.value.windows
    )
    for window in outcome.value.windows:
        assert window.percent_used.unit == "percent"
        assert window.percent_used.value is not None
        assert 0 <= window.percent_used.value <= 100
        assert window.reset_display.value is not None
        assert 1 <= len(window.reset_display.value) <= 96

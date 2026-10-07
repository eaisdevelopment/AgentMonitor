"""Exact Claude Code quota and OTEL capability declarations."""

from typing import Literal

from agentmonitor.contracts.common_v1 import FieldAvailabilityV1
from agentmonitor.contracts.provider_system_v1 import (
    AdapterDescriptorV1,
    CapabilityDeclarationV1,
    CapabilityManifestV1,
    CapabilitySchemaRangeV1,
    CapabilitySchemaVersionV1,
    CollectionConstraintV1,
    ProtocolVersionRangeV1,
    ProviderSourceV1,
    ProviderVersionRuleV1,
)

SideEffectClass = Literal["read_only", "managed_profile_write", "unknown"]

CLAUDE_ADAPTER_ID = "agentmonitor.claude"
CLAUDE_ADAPTER_VERSION = "1.0.3"
CLAUDE_PARSER_VERSION = "1.0.3"
CLAUDE_PROVIDER_VERSION = "2.1.289"
CLAUDE_OTEL_PROVIDER_VERSION = "2.1.282"
CLAUDE_INSTALLATION_SOURCE_ID = "claude.version.banner.v1"
CLAUDE_USAGE_SOURCE_ID = "claude.usage.ax-screen-reader.v1"
CLAUDE_IDENTITY_SOURCE_ID = "claude.auth.status"
CLAUDE_REAUTH_SOURCE_ID = "claude.auth.login"
CLAUDE_OTEL_SOURCE_ID = "claude.otel.metrics.http-json.v1"
CLAUDE_OTEL_ADAPTER_ID = "agentmonitor.claude.otel"
CLAUDE_OTEL_ADAPTER_VERSION = "1.0.0"
CLAUDE_OTEL_MAPPING_ID = "M0-M03-CLAUDE-OTEL-001"
CLAUDE_OTEL_MAPPING_DIGEST = (
    "b04e80988eb2d7a6dd60b9a51eb2a809eaa8787f56bf828ebcbfb5c52b5ffd21"
)
M0_MAPPING_ID = "A01-M03-CLAUDE-2-1-289-001"
M0_MAPPING_DIGEST = "c2b08c0dff0a218f73e6c9fadb3529385a1b65e5c9de413b464880f226b06923"
CLAUDE_QUOTA_DECISION_REFERENCE = M0_MAPPING_ID
CLAUDE_AUTH_DECISION_REFERENCE = M0_MAPPING_ID


def _schema_v1() -> CapabilitySchemaRangeV1:
    return CapabilitySchemaRangeV1(
        CapabilitySchemaVersionV1(1, 0), CapabilitySchemaVersionV1(1, 0)
    )


def _constraints(
    *, deadline_ms: int, minimum_interval_ms: int
) -> CollectionConstraintV1:
    return CollectionConstraintV1(
        deadline_ms=deadline_ms,
        minimum_interval_ms=minimum_interval_ms,
        maximum_concurrency=1,
        automatic_retry_count=0,
        provider_request_count=None,
        provider_request_count_availability=FieldAvailabilityV1("unknown"),
    )


def _source(
    *,
    source_id: str,
    capability_id: str,
    credential_role: str,
    side_effect_class: SideEffectClass,
) -> ProviderSourceV1:
    return ProviderSourceV1(
        source_id=source_id,
        provider_key="claude",
        capability_id=capability_id,
        source_class="supported_cli",
        stability="supported",
        mechanism_version="1",
        credential_role=credential_role,
        side_effect_class=side_effect_class,
        evidence_reference=M0_MAPPING_ID,
        is_experimental=False,
    )


def _declaration(
    *,
    capability_id: str,
    source_id: str,
    credential_role: str,
    side_effect_class: SideEffectClass,
    port_type: str,
    output_schema: str,
    rule_suffix: str,
    deadline_ms: int,
    minimum_interval_ms: int,
) -> CapabilityDeclarationV1:
    source = _source(
        source_id=source_id,
        capability_id=capability_id,
        credential_role=credential_role,
        side_effect_class=side_effect_class,
    )
    return CapabilityDeclarationV1(
        capability_id=capability_id,
        schema_versions=_schema_v1(),
        decision="supported",
        stability="supported",
        reason_code="m0_supported_exact_tuple",
        evidence_reference=M0_MAPPING_ID,
        port_type=port_type,
        output_schema=output_schema,
        sources=(source,),
        provider_version_rule=ProviderVersionRuleV1(
            rule_id=f"claude-code-2-1-289-{rule_suffix}-exact",
            scheme="opaque_exact",
            verified_versions=(CLAUDE_PROVIDER_VERSION,),
        ),
        constraints=_constraints(
            deadline_ms=deadline_ms,
            minimum_interval_ms=minimum_interval_ms,
        ),
        side_effect_class=side_effect_class,
        platforms=("linux-x86_64",),
    )


def build_claude_manifest() -> CapabilityManifestV1:
    """Build the closed manifest; no version or source ranges are inferred."""
    quota = _declaration(
        capability_id="subscription.quota",
        source_id=CLAUDE_USAGE_SOURCE_ID,
        credential_role="provider_managed_default_profile",
        side_effect_class="read_only",
        port_type="SubscriptionQuotaPortV1",
        output_schema="ClaudeSubscriptionQuotaV1",
        rule_suffix="quota",
        deadline_ms=30_000,
        minimum_interval_ms=300_000,
    )
    installation = _declaration(
        capability_id="installation.discovery",
        source_id=CLAUDE_INSTALLATION_SOURCE_ID,
        credential_role="none",
        side_effect_class="read_only",
        port_type="InstallationDiscoveryPortV1",
        output_schema="DiscoveryOutcomeV1",
        rule_suffix="installation",
        deadline_ms=3_000,
        minimum_interval_ms=0,
    )
    authentication_health = _declaration(
        capability_id="authentication.health",
        source_id=CLAUDE_USAGE_SOURCE_ID,
        credential_role="provider_managed_default_profile",
        side_effect_class="read_only",
        port_type="AuthenticationHealthPortV1",
        output_schema="AuthHealthObservationV1",
        rule_suffix="auth-health",
        deadline_ms=30_000,
        minimum_interval_ms=300_000,
    )
    identity = _declaration(
        capability_id="identity.verification",
        source_id=CLAUDE_IDENTITY_SOURCE_ID,
        credential_role="provider_managed_profile",
        side_effect_class="read_only",
        port_type="ProviderCapabilityPortV1",
        output_schema="ObservedProfileIdentityV1",
        rule_suffix="identity",
        deadline_ms=3_000,
        minimum_interval_ms=0,
    )
    reauthentication = _declaration(
        capability_id="authentication.reauthenticate",
        source_id=CLAUDE_REAUTH_SOURCE_ID,
        credential_role="agentmonitor_managed_profile",
        side_effect_class="managed_profile_write",
        port_type="ProviderConnectionPortV1",
        output_schema="ProviderConnectionViewV1",
        rule_suffix="managed-reauth",
        deadline_ms=300_000,
        minimum_interval_ms=0,
    )
    return CapabilityManifestV1(
        descriptor=AdapterDescriptorV1(
            adapter_id=CLAUDE_ADAPTER_ID,
            adapter_version=CLAUDE_ADAPTER_VERSION,
            provider_key="claude",
            protocol_versions=ProtocolVersionRangeV1("1.0.0", "1.0.0"),
            build_identity="agentmonitor-claude-v1",
        ),
        manifest_schema_version="1.0.0",
        # Quota remains first for the existing V1 collection composition.
        declarations=(
            quota,
            installation,
            authentication_health,
            identity,
            reauthentication,
        ),
        m0_mapping_id=M0_MAPPING_ID,
        m0_mapping_version="1.0.0",
        m0_mapping_digest=M0_MAPPING_DIGEST,
    )


def build_claude_otel_manifest() -> CapabilityManifestV1:
    """Build the separately versioned exact official OTEL session lane."""
    otel_source = ProviderSourceV1(
        source_id=CLAUDE_OTEL_SOURCE_ID,
        provider_key="claude",
        capability_id="local.session.discovery",
        source_class="documented_api",
        stability="supported",
        mechanism_version="1.0.0",
        credential_role="provider_managed_default_profile",
        side_effect_class="read_only",
        evidence_reference="M0-M03-CLAUDE-OTEL-001",
        is_experimental=False,
    )
    local_session = CapabilityDeclarationV1(
        capability_id="local.session.discovery",
        schema_versions=CapabilitySchemaRangeV1(
            CapabilitySchemaVersionV1(1, 0), CapabilitySchemaVersionV1(1, 0)
        ),
        decision="supported",
        stability="supported",
        reason_code="official_authenticated_otel_exact_tuple",
        evidence_reference="M0-M03-CLAUDE-OTEL-001",
        port_type="ClaudeLocalSessionDiscoveryV1",
        output_schema="RuntimeObservationBatchV1",
        sources=(otel_source,),
        provider_version_rule=ProviderVersionRuleV1(
            rule_id="claude-code-2-1-282-otel-exact",
            scheme="opaque_exact",
            verified_versions=(CLAUDE_OTEL_PROVIDER_VERSION,),
        ),
        constraints=CollectionConstraintV1(
            deadline_ms=30_000,
            minimum_interval_ms=0,
            maximum_concurrency=1,
            automatic_retry_count=0,
            provider_request_count=None,
            provider_request_count_availability=FieldAvailabilityV1("unknown"),
        ),
        side_effect_class="read_only",
        platforms=("linux-x86_64",),
    )
    return CapabilityManifestV1(
        descriptor=AdapterDescriptorV1(
            adapter_id=CLAUDE_OTEL_ADAPTER_ID,
            adapter_version=CLAUDE_OTEL_ADAPTER_VERSION,
            provider_key="claude",
            protocol_versions=ProtocolVersionRangeV1("1.0.0", "1.0.0"),
            build_identity="agentmonitor-claude-otel-session-v1",
        ),
        manifest_schema_version="1.0.0",
        declarations=(local_session,),
        m0_mapping_id=CLAUDE_OTEL_MAPPING_ID,
        m0_mapping_version="1.0.0",
        m0_mapping_digest=CLAUDE_OTEL_MAPPING_DIGEST,
    )

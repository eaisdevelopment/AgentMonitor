"""Exact Claude Code 2.1.278 capability declaration."""

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

CLAUDE_ADAPTER_ID = "agentmonitor.claude"
CLAUDE_ADAPTER_VERSION = "1.0.2"
CLAUDE_PARSER_VERSION = "1.0.2"
CLAUDE_PROVIDER_VERSION = "2.1.278"
CLAUDE_USAGE_SOURCE_ID = "claude.usage.ax-screen-reader.v1"
CLAUDE_OTEL_SOURCE_ID = "claude.otel.metrics.http-json.v1"
CLAUDE_OTEL_ADAPTER_ID = "agentmonitor.claude.otel"
CLAUDE_OTEL_ADAPTER_VERSION = "1.0.0"
CLAUDE_OTEL_MAPPING_ID = "M0-M03-CLAUDE-OTEL-001"
CLAUDE_OTEL_MAPPING_DIGEST = (
    "88f558e169fb1a5f278e760ae501b79dc7455cd1d4e6ac488bc3b2bd019d0cb2"
)
M0_MAPPING_ID = "M0-M03-CLAUDE-001"
M0_MAPPING_DIGEST = "8ad7dfb49415f7ebc0460511625d6c4766836ddbdc55c38f5b9af89bd8de4c8b"


def build_claude_manifest() -> CapabilityManifestV1:
    """Build the closed manifest; no version or source ranges are inferred."""
    source = ProviderSourceV1(
        source_id=CLAUDE_USAGE_SOURCE_ID,
        provider_key="claude",
        capability_id="subscription.quota",
        source_class="supported_cli",
        stability="supported",
        mechanism_version="1",
        credential_role="provider_managed_default_profile",
        side_effect_class="read_only",
        evidence_reference="M0-M3-CLAUDE-EVIDENCE-001",
        is_experimental=False,
    )
    quota = CapabilityDeclarationV1(
        capability_id="subscription.quota",
        schema_versions=CapabilitySchemaRangeV1(
            CapabilitySchemaVersionV1(1, 0), CapabilitySchemaVersionV1(1, 0)
        ),
        decision="supported",
        stability="supported",
        reason_code="m0_supported_exact_tuple",
        evidence_reference="M0-M3-CLAUDE-EVIDENCE-001",
        port_type="SubscriptionQuotaPortV1",
        output_schema="ClaudeSubscriptionQuotaV1",
        sources=(source,),
        provider_version_rule=ProviderVersionRuleV1(
            rule_id="claude-code-2-1-278-exact",
            scheme="opaque_exact",
            verified_versions=(CLAUDE_PROVIDER_VERSION,),
        ),
        constraints=CollectionConstraintV1(
            deadline_ms=30_000,
            minimum_interval_ms=300_000,
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
            adapter_id=CLAUDE_ADAPTER_ID,
            adapter_version=CLAUDE_ADAPTER_VERSION,
            provider_key="claude",
            protocol_versions=ProtocolVersionRangeV1("1.0.0", "1.0.0"),
            build_identity="agentmonitor-claude-subscription-v1",
        ),
        manifest_schema_version="1.0.0",
        declarations=(quota,),
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
            rule_id="claude-code-2-1-278-otel-exact",
            scheme="opaque_exact",
            verified_versions=(CLAUDE_PROVIDER_VERSION,),
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

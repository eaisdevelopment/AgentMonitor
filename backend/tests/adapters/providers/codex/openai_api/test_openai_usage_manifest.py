"""Pure A02 usage admission metadata, with no claim of actual source approval."""

from agentmonitor.adapters.providers.codex.openai_api.manifest import (
    USAGE_PROVIDER_VERSION,
    build_openai_cost_manifest,
    build_openai_usage_manifest,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    CapabilitySchemaVersionV1,
    SourcePolicyV1,
)
from agentmonitor.modules.provider_system.domain.protocol import resolve_capability


def test_openai_usage_requires_separate_actual_mapping_and_source_admission() -> None:
    # Constructed metadata is only input to the pure domain resolver.
    usage = build_openai_usage_manifest(
        evidence_reference="pure-usage-evidence", mapping_digest="a" * 64
    )
    cost = build_openai_cost_manifest()
    assert usage.descriptor.adapter_id != cost.descriptor.adapter_id
    assert usage.m0_mapping_id == "pure-usage-evidence"
    assert usage.m0_mapping_digest != cost.m0_mapping_digest
    declaration = usage.declarations[0]
    assert declaration.capability_id == "api.usage"
    assert declaration.port_type == "OpenAIUsageSourceV1"
    assert declaration.decision == "experimental"
    assert declaration.reason_code == "documented_source_live_verification_pending"
    source = declaration.sources[0]
    assert source.source_id == "openai.organization.usage.v1"
    assert source.source_class == "documented_api"
    assert source.side_effect_class == "read_only"
    assert declaration.constraints.automatic_retry_count == 0
    for grant, expected in (
        (None, "capability_disabled"),
        (OpaqueIdV1("pure-grant"), "resolved"),
    ):
        resolved = resolve_capability(
            usage,
            approved_mapping_digest=usage.m0_mapping_digest,
            host_protocol_version="1.0.0",
            capability_id="api.usage",
            capability_schema_version=CapabilitySchemaVersionV1(2, 0),
            provider_version=USAGE_PROVIDER_VERSION,
            platform_id="linux-x86_64",
            source_policy=SourcePolicyV1(
                OpaqueIdV1("pure-policy"), (source.source_id,), (), grant
            ),
        )
        assert resolved.code == expected

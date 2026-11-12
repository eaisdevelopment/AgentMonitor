"""Pure OpenAI source metadata; no credential, transport or live claims."""

from agentmonitor.adapters.providers.codex.openai_api.manifest import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    EVIDENCE_REFERENCE,
    PROVIDER_VERSION,
    build_openai_cost_manifest,
)
from agentmonitor.adapters.providers.codex.openai_api.policy import SOURCE_ID
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    CapabilitySchemaVersionV1,
    SourcePolicyV1,
)
from agentmonitor.modules.provider_system.domain.protocol import resolve_capability


def test_manifest_describes_only_bounded_unverified_cost_source() -> None:
    manifest = build_openai_cost_manifest()
    assert manifest.descriptor.adapter_id == ADAPTER_ID
    assert manifest.descriptor.adapter_version == ADAPTER_VERSION
    assert manifest.descriptor.provider_key == "codex"
    assert len(manifest.declarations) == 1
    declaration = manifest.declarations[0]
    assert declaration.capability_id == "api.cost"
    assert declaration.decision == "experimental"
    assert declaration.reason_code == "documented_source_live_verification_pending"
    assert declaration.port_type == "OpenAICostSourceV1"
    source = declaration.sources[0]
    assert source.source_id == SOURCE_ID and source.provider_key == "codex"
    assert source.source_class == "documented_api"
    assert source.credential_role == "owner_entered_admin_api_key"
    assert source.side_effect_class == "read_only"
    assert source.evidence_reference == EVIDENCE_REFERENCE
    assert declaration.provider_version_rule.scheme == "opaque_exact"
    assert declaration.provider_version_rule.verified_versions == (PROVIDER_VERSION,)
    assert declaration.constraints.deadline_ms == 120000
    assert declaration.constraints.minimum_interval_ms == 900000
    assert declaration.constraints.maximum_concurrency == 1
    assert declaration.constraints.automatic_retry_count == 0
    assert declaration.constraints.provider_request_count == 20


def test_manifest_cannot_grant_itself_experimental_runtime_access() -> None:
    manifest = build_openai_cost_manifest()
    for grant, expected in (
        (None, "capability_disabled"),
        (OpaqueIdV1("grant"), "resolved"),
    ):
        result = resolve_capability(
            manifest,
            approved_mapping_digest=manifest.m0_mapping_digest,
            host_protocol_version="1.0.0",
            capability_id="api.cost",
            capability_schema_version=CapabilitySchemaVersionV1(2, 0),
            provider_version=PROVIDER_VERSION,
            platform_id="linux-x86_64",
            source_policy=SourcePolicyV1(OpaqueIdV1("policy"), (SOURCE_ID,), (), grant),
        )
        assert result.code == expected

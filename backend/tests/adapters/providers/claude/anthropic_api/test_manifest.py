"""Actual source metadata must distinguish documented beta from private scraping."""

from agentmonitor.adapters.providers.claude.anthropic_api.manifest import (
    build_anthropic_cost_manifest,
)
from agentmonitor.adapters.providers.claude.anthropic_api.policy import API_VERSION
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    CapabilitySchemaVersionV1,
    SourcePolicyV1,
)
from agentmonitor.modules.provider_system.domain.protocol import resolve_capability


def test_documented_beta_does_not_claim_private_or_live_support() -> None:
    manifest = build_anthropic_cost_manifest()
    assert len(manifest.declarations) == 1
    declaration = manifest.declarations[0]
    assert declaration.capability_id == "api.cost"
    assert declaration.decision == "experimental"
    assert declaration.reason_code == "documented_beta_live_verification_pending"
    assert declaration.sources[0].source_class == "documented_api"
    assert declaration.sources[0].is_experimental
    assert declaration.constraints.automatic_retry_count == 0
    assert declaration.constraints.maximum_concurrency == 1


def test_documented_beta_still_requires_its_scoped_experimental_grant() -> None:
    manifest = build_anthropic_cost_manifest()
    source = manifest.declarations[0].sources[0]
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
            provider_version=API_VERSION,
            platform_id="linux-x86_64",
            source_policy=SourcePolicyV1(
                OpaqueIdV1("policy"), (source.source_id,), (), grant
            ),
        )
        assert result.code == expected

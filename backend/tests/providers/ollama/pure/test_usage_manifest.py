"""Pure usage descriptor/admission checks; no provider payloads or I/O."""

from importlib import import_module
from types import ModuleType
from typing import cast

import pytest
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    CapabilityManifestV1,
    CapabilitySchemaVersionV1,
    SourcePolicyV1,
)
from agentmonitor.modules.provider_system.domain.protocol import resolve_capability


def _module() -> ModuleType:
    try:
        return import_module("agentmonitor.adapters.providers.ollama.api.manifest")
    except ModuleNotFoundError as error:
        if error.name != "agentmonitor.adapters.providers.ollama.api.manifest":
            raise
        raise AssertionError("Ollama usage-only manifest is absent") from None


def _manifest() -> CapabilityManifestV1:
    return cast(CapabilityManifestV1, _module().build_ollama_usage_manifest())


def test_usage_candidate_has_separate_identity_and_honest_evidence() -> None:
    module = _module()
    manifest = _manifest()
    assert manifest.descriptor.adapter_id == module.ADAPTER_ID
    assert module.ADAPTER_ID == "agentmonitor.ollama.api-usage"
    assert manifest.descriptor.adapter_version == module.ADAPTER_VERSION == "1.0.0"
    assert manifest.descriptor.provider_key == "ollama"
    assert len(manifest.declarations) == 1
    declaration = manifest.declarations[0]
    assert declaration.capability_id == "api.usage"
    assert declaration.decision == "experimental"
    assert declaration.reason_code == "documented_source_live_verification_pending"
    assert declaration.port_type == "OllamaUsageSourceV1"
    assert declaration.output_schema == "BudgetReportInputV1"
    assert declaration.evidence_reference == module.EVIDENCE_REFERENCE
    assert manifest.m0_mapping_id == module.EVIDENCE_REFERENCE
    assert manifest.m0_mapping_digest == (
        "c51868e3f798f9b4a2ef27c1237a8ed61fee85996bf8851610c2dc32f9885e91"
    )
    assert len(declaration.sources) == 1
    source = declaration.sources[0]
    assert source.source_id == "ollama.cloud.usage.v1"
    assert source.provider_key == "ollama"
    assert source.capability_id == "api.usage"
    assert source.source_class == "documented_api"
    assert source.stability == "experimental" and source.is_experimental
    assert source.credential_role == "owner_entered_api_key_self_or_team_admin"
    assert source.side_effect_class == declaration.side_effect_class == "read_only"
    assert source.mechanism_version == module.PROVIDER_VERSION
    assert source.evidence_reference == module.EVIDENCE_REFERENCE
    assert declaration.provider_version_rule.scheme == "opaque_exact"
    assert declaration.provider_version_rule.verified_versions == (
        module.PROVIDER_VERSION,
    )


def test_usage_descriptor_limits_match_the_existing_source_policy() -> None:
    declaration = _manifest().declarations[0]
    constraints = declaration.constraints
    assert constraints.deadline_ms == 10_000
    assert constraints.minimum_interval_ms == 900_000
    assert constraints.maximum_concurrency == 1
    assert constraints.automatic_retry_count == 0
    assert constraints.provider_request_count == 1
    assert constraints.provider_request_count_availability.state == "available"
    assert declaration.schema_versions.minimum == CapabilitySchemaVersionV1(2, 0)
    assert declaration.schema_versions.maximum == CapabilitySchemaVersionV1(2, 0)
    assert declaration.platforms == ("linux-x86_64",)


@pytest.mark.parametrize(
    "capability,schema,version,grant,expected",
    [
        ("api.usage", (2, 0), None, False, "capability_disabled"),
        ("api.usage", (2, 0), None, True, "resolved"),
        ("api.usage", (1, 0), None, True, "capability_schema_incompatible"),
        ("api.usage", (2, 1), None, True, "capability_schema_incompatible"),
        ("api.usage", (2, 0), "unknown-version", True, "provider_version_unverified"),
        ("api.cost", (2, 0), None, True, "capability_not_declared"),
        ("api.budget", (2, 0), None, True, "capability_not_declared"),
        ("subscription.quota", (2, 0), None, True, "capability_not_declared"),
    ],
)
def test_candidate_negotiation_never_implies_balance_or_live_admission(
    capability: str,
    schema: tuple[int, int],
    version: str | None,
    grant: bool,
    expected: str,
) -> None:
    module = _module()
    manifest = _manifest()
    result = resolve_capability(
        manifest,
        approved_mapping_digest=manifest.m0_mapping_digest,
        host_protocol_version="1.0.0",
        capability_id=capability,
        capability_schema_version=CapabilitySchemaVersionV1(*schema),
        provider_version=module.PROVIDER_VERSION if version is None else version,
        platform_id="linux-x86_64",
        source_policy=SourcePolicyV1(
            OpaqueIdV1("pure-usage-policy"),
            ("ollama.cloud.usage.v1",),
            (),
            OpaqueIdV1("pure-usage-grant") if grant else None,
        ),
    )
    assert result.code == expected


def test_candidate_cannot_bypass_reviewed_mapping_binding() -> None:
    module = _module()
    manifest = _manifest()
    result = resolve_capability(
        manifest,
        approved_mapping_digest="0" * 64,
        host_protocol_version="1.0.0",
        capability_id="api.usage",
        capability_schema_version=CapabilitySchemaVersionV1(2, 0),
        provider_version=module.PROVIDER_VERSION,
        platform_id="linux-x86_64",
        source_policy=SourcePolicyV1(
            OpaqueIdV1("pure-usage-policy"),
            ("ollama.cloud.usage.v1",),
            (),
            OpaqueIdV1("pure-usage-grant"),
        ),
    )
    assert result.code == "mapping_binding_invalid"

"""Ollama local capabilities awaiting M6 technical admission."""

from agentmonitor.contracts.common_v1 import FieldAvailabilityV1
from agentmonitor.contracts.provider_system_v1 import (
    AdapterDescriptorV1,
    CapabilityDeclarationV1,
    CapabilityManifestV1,
    CapabilitySchemaRangeV1,
    CapabilitySchemaVersionV1,
    CollectionConstraintV1,
    ProtocolVersionRangeV1,
    ProviderVersionRuleV1,
)

OLLAMA_PROVIDER_VERSION = "0.24.0"
OLLAMA_ADAPTER_ID = "agentmonitor.ollama"
OLLAMA_ADAPTER_VERSION = "1.1.0"
_PLAN_ID = "M6-OLL-LOCAL-PLAN-001"
# Digest of the owner-approved plan as it stood on 1 November 2026; this is
# provenance for a pending decision, not an admission or completion receipt.
_PLAN_DIGEST = "79ee24b05b4d4ee71aade4fdaa96ab8b1af88050614e28aa7195524f4742591c"


def _pending(capability_id: str) -> CapabilityDeclarationV1:
    schema = CapabilitySchemaVersionV1(1, 0)
    return CapabilityDeclarationV1(
        capability_id=capability_id,
        schema_versions=CapabilitySchemaRangeV1(schema, schema),
        decision="unknown",
        stability="unknown",
        reason_code="technical_admission_pending",
        evidence_reference=_PLAN_ID,
        port_type=None,
        output_schema=None,
        sources=(),
        provider_version_rule=ProviderVersionRuleV1(
            rule_id="ollama-0-24-0-local-exact",
            scheme="semantic_exact",
            verified_versions=(OLLAMA_PROVIDER_VERSION,),
        ),
        constraints=CollectionConstraintV1(
            deadline_ms=12000,
            minimum_interval_ms=0,
            maximum_concurrency=1,
            automatic_retry_count=0,
            provider_request_count=None,
            provider_request_count_availability=FieldAvailabilityV1("unknown"),
        ),
        side_effect_class="read_only",
        platforms=("linux-x86_64",),
    )


def build_ollama_manifest() -> CapabilityManifestV1:
    """Expose provider identity without claiming uncompleted admission."""
    return CapabilityManifestV1(
        descriptor=AdapterDescriptorV1(
            adapter_id=OLLAMA_ADAPTER_ID,
            adapter_version=OLLAMA_ADAPTER_VERSION,
            provider_key="ollama",
            protocol_versions=ProtocolVersionRangeV1("1.0.0", "1.0.0"),
            build_identity="agentmonitor-ollama-local-v1",
        ),
        manifest_schema_version="1.0.0",
        declarations=(_pending("installation.discovery"), _pending("model.catalog")),
        m0_mapping_id=_PLAN_ID,
        m0_mapping_version="1.0.0",
        m0_mapping_digest=_PLAN_DIGEST,
    )

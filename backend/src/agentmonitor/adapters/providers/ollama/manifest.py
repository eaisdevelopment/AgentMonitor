"""Exact Ollama 0.24.0 local capabilities admitted by the approved M6 plan."""

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

OLLAMA_PROVIDER_VERSION = "0.24.0"
OLLAMA_ADAPTER_ID = "agentmonitor.ollama"
OLLAMA_ADAPTER_VERSION = "1.1.0"
_PLAN_ID = "M6-OLL-LOCAL-PLAN-001"
# Digest of the owner-approved local implementation plan on 1 November 2026.
_PLAN_DIGEST = "79ee24b05b4d4ee71aade4fdaa96ab8b1af88050614e28aa7195524f4742591c"


def _constraints(deadline_ms: int) -> CollectionConstraintV1:
    return CollectionConstraintV1(
        deadline_ms=deadline_ms,
        minimum_interval_ms=0,
        maximum_concurrency=1,
        automatic_retry_count=0,
        provider_request_count=None,
        provider_request_count_availability=FieldAvailabilityV1("unknown"),
    )


def _installation() -> CapabilityDeclarationV1:
    schema = CapabilitySchemaVersionV1(1, 0)
    source = ProviderSourceV1(
        source_id="ollama.cli.version.v1",
        provider_key="ollama",
        capability_id="installation.discovery",
        source_class="supported_cli",
        stability="supported",
        mechanism_version="ollama-cli@0.24.0",
        credential_role="none",
        side_effect_class="read_only",
        evidence_reference=_PLAN_ID,
        is_experimental=False,
    )
    return CapabilityDeclarationV1(
        capability_id="installation.discovery",
        schema_versions=CapabilitySchemaRangeV1(schema, schema),
        decision="supported",
        stability="supported",
        reason_code="owner_approved_local_exact_tuple",
        evidence_reference=_PLAN_ID,
        port_type="InstallationDiscoveryPortV1",
        output_schema="DiscoveryOutcomeV1",
        sources=(source,),
        provider_version_rule=ProviderVersionRuleV1(
            rule_id="ollama-0-24-0-installation-exact",
            scheme="semantic_exact",
            verified_versions=(OLLAMA_PROVIDER_VERSION,),
        ),
        constraints=_constraints(3_000),
        side_effect_class="read_only",
        platforms=("linux-x86_64",),
    )


def _model_catalog() -> CapabilityDeclarationV1:
    schema = CapabilitySchemaVersionV1(1, 0)
    source = ProviderSourceV1(
        source_id="ollama.local.catalog.v1",
        provider_key="ollama",
        capability_id="model.catalog",
        source_class="documented_api",
        stability="documented",
        mechanism_version="ollama-local-http@0.24.0",
        credential_role="none",
        side_effect_class="read_only",
        evidence_reference=_PLAN_ID,
        is_experimental=False,
    )
    return CapabilityDeclarationV1(
        capability_id="model.catalog",
        schema_versions=CapabilitySchemaRangeV1(schema, schema),
        decision="supported",
        stability="documented",
        reason_code="owner_approved_local_exact_tuple",
        evidence_reference=_PLAN_ID,
        port_type="LocalCatalogPortV1",
        output_schema="LocalCatalogViewV1",
        sources=(source,),
        provider_version_rule=ProviderVersionRuleV1(
            rule_id="ollama-0-24-0-local-catalog-exact",
            scheme="semantic_exact",
            verified_versions=(OLLAMA_PROVIDER_VERSION,),
        ),
        constraints=_constraints(12_000),
        side_effect_class="read_only",
        platforms=("linux-x86_64",),
    )


def build_ollama_manifest() -> CapabilityManifestV1:
    """Publish only the two approved fixed-host, read-only local lanes."""
    return CapabilityManifestV1(
        descriptor=AdapterDescriptorV1(
            adapter_id=OLLAMA_ADAPTER_ID,
            adapter_version=OLLAMA_ADAPTER_VERSION,
            provider_key="ollama",
            protocol_versions=ProtocolVersionRangeV1("1.0.0", "1.0.0"),
            build_identity="agentmonitor-ollama-local-v1",
        ),
        manifest_schema_version="1.0.0",
        declarations=(_installation(), _model_catalog()),
        m0_mapping_id=_PLAN_ID,
        m0_mapping_version="1.0.0",
        m0_mapping_digest=_PLAN_DIGEST,
    )

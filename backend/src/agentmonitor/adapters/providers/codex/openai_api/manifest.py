"""Documented A02 cost candidate; live and scheduling admission remain separate."""

from agentmonitor.adapters.providers.codex.openai_api.policy import (
    MAX_REQUESTS,
    REPORT_SECONDS,
    SOURCE_ID,
)
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

ADAPTER_ID = "agentmonitor.codex.openai-api"
ADAPTER_VERSION = "1.0.0"
# Exact documentation/mechanism identity, not a claimed provider server release.
PROVIDER_VERSION = "openai-organization-costs-docs-2026-11-11"
EVIDENCE_REFERENCE = "M7-A02-OPENAI-COST-DOCS-2026-11-11"


def build_openai_cost_manifest() -> CapabilityManifestV1:
    """Describe costs only; neither usage nor balance or live success is implied.

    Experimental classifies this unverified implementation candidate, not the
    official endpoint as private or beta. Existing source-policy admission is
    required before invocation; the descriptor itself authorizes no request.
    """
    source = ProviderSourceV1(
        source_id=SOURCE_ID,
        provider_key="codex",
        capability_id="api.cost",
        source_class="documented_api",
        stability="experimental",
        mechanism_version=PROVIDER_VERSION,
        credential_role="owner_entered_admin_api_key",
        side_effect_class="read_only",
        evidence_reference=EVIDENCE_REFERENCE,
        is_experimental=True,
    )
    return CapabilityManifestV1(
        descriptor=AdapterDescriptorV1(
            ADAPTER_ID,
            ADAPTER_VERSION,
            "codex",
            ProtocolVersionRangeV1("1.0.0", "1.0.0"),
            "agentmonitor-openai-organization-costs-v1",
        ),
        manifest_schema_version="1.0.0",
        declarations=(
            CapabilityDeclarationV1(
                capability_id="api.cost",
                schema_versions=CapabilitySchemaRangeV1(
                    CapabilitySchemaVersionV1(2, 0), CapabilitySchemaVersionV1(2, 0)
                ),
                decision="experimental",
                stability="experimental",
                reason_code="documented_source_live_verification_pending",
                evidence_reference=EVIDENCE_REFERENCE,
                port_type="OpenAICostSourceV1",
                output_schema="BudgetReportInputV1",
                sources=(source,),
                provider_version_rule=ProviderVersionRuleV1(
                    "openai-organization-costs-docs-exact",
                    "opaque_exact",
                    (PROVIDER_VERSION,),
                ),
                constraints=CollectionConstraintV1(
                    deadline_ms=REPORT_SECONDS * 1000,
                    minimum_interval_ms=15 * 60 * 1000,
                    maximum_concurrency=1,
                    automatic_retry_count=0,
                    provider_request_count=MAX_REQUESTS,
                    provider_request_count_availability=FieldAvailabilityV1(
                        "available"
                    ),
                ),
                side_effect_class="read_only",
                platforms=("linux-x86_64",),
            ),
        ),
        m0_mapping_id=EVIDENCE_REFERENCE,
        m0_mapping_version="1.0.0",
        # Reviewed documentation artifact only, never live-read evidence.
        m0_mapping_digest=(
            "c51868e3f798f9b4a2ef27c1237a8ed61fee85996bf8851610c2dc32f9885e91"
        ),
    )

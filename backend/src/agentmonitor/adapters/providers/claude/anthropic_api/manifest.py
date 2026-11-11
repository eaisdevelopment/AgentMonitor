"""Experimental A01 cost-source descriptor; live/scheduling admission is separate."""

from agentmonitor.adapters.providers.claude.anthropic_api.policy import (
    API_VERSION,
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

ADAPTER_ID = "agentmonitor.claude.anthropic-api"
ADAPTER_VERSION = "1.0.0"
EVIDENCE_REFERENCE = "M7-A01-ANTHROPIC-DOCS-2026-11-11"


def build_anthropic_cost_manifest() -> CapabilityManifestV1:
    """Describe one cost-only candidate; no usage/balance capability is implied."""
    source = ProviderSourceV1(
        source_id=SOURCE_ID,
        provider_key="claude",
        capability_id="api.cost",
        source_class="documented_api",
        stability="experimental",
        mechanism_version=API_VERSION,
        credential_role="owner_entered_admin_api_key",
        side_effect_class="read_only",
        evidence_reference=EVIDENCE_REFERENCE,
        is_experimental=True,
    )
    return CapabilityManifestV1(
        descriptor=AdapterDescriptorV1(
            ADAPTER_ID,
            ADAPTER_VERSION,
            "claude",
            ProtocolVersionRangeV1("1.0.0", "1.0.0"),
            "agentmonitor-anthropic-analytics-cost-v1",
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
                reason_code="documented_beta_live_verification_pending",
                evidence_reference=EVIDENCE_REFERENCE,
                port_type="AnthropicCostSourceV1",
                output_schema="BudgetReportInputV1",
                sources=(source,),
                provider_version_rule=ProviderVersionRuleV1(
                    "anthropic-analytics-2026-10-21", "date_exact", (API_VERSION,)
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
        # Exact reviewed documentation-discovery artifact, not live-read evidence.
        m0_mapping_digest=(
            "c51868e3f798f9b4a2ef27c1237a8ed61fee85996bf8851610c2dc32f9885e91"
        ),
    )

"""Documented A02 reports; live and scheduling admission remain separate.

The finite endpoint/field/unit/grouping inventory is usage_mapping.USAGE_MAPPINGS
and the official organization Usage reference checked 2026-11-12. Usage requires
owner-entered organization Admin API credentials under the existing runtime
grant. Cost supports only project/key views here, never inferred model/token
categories. New usage sources remain experimental until verified and admitted.
"""

from dataclasses import replace

from agentmonitor.adapters.providers.codex.openai_api.policy import (
    MAX_REQUESTS,
    REPORT_SECONDS,
    SOURCE_ID,
    USAGE_SOURCE_ID,
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
ADAPTER_VERSION = "1.0.3"
# Exact documentation/mechanism identity, not a claimed provider server release.
PROVIDER_VERSION = "openai-organization-costs-docs-2026-11-11"
EVIDENCE_REFERENCE = "M7-A02-OPENAI-COST-DOCS-2026-11-11"
USAGE_PROVIDER_VERSION = "openai-organization-usage-docs-2026-11-12"
ANALYTICS_VERSION = "1.1.3"
ANALYTICS_REFERENCE = "OPENAI-ANALYTICS-1.1"
ANALYTICS_MAPPING_DIGEST = (
    "cafbafe1707fe52f20e5bd82c7fc9f1bfca7d6696136feec879914123496adc1"
)


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


def build_openai_usage_manifest(
    *,
    evidence_reference: str,
    mapping_digest: str,
) -> CapabilityManifestV1:
    """Root must supply the real reviewed usage mapping artifact, not cost proof."""
    cost = build_openai_cost_manifest()
    declaration = cost.declarations[0]
    source = replace(
        declaration.sources[0],
        source_id=USAGE_SOURCE_ID,
        capability_id="api.usage",
        mechanism_version=USAGE_PROVIDER_VERSION,
        evidence_reference=evidence_reference,
    )
    return replace(
        cost,
        descriptor=replace(
            cost.descriptor,
            adapter_id=ADAPTER_ID + ".usage",
            build_identity="agentmonitor-openai-organization-usage-v1",
        ),
        declarations=(
            replace(
                declaration,
                capability_id="api.usage",
                port_type="OpenAIUsageSourceV1",
                evidence_reference=evidence_reference,
                sources=(source,),
                provider_version_rule=ProviderVersionRuleV1(
                    "openai-organization-usage-docs-exact",
                    "opaque_exact",
                    (USAGE_PROVIDER_VERSION,),
                ),
            ),
        ),
        m0_mapping_id=evidence_reference,
        m0_mapping_digest=mapping_digest,
    )


def build_openai_analytics_manifest() -> CapabilityManifestV1:
    """Expand the existing adapter with separately versioned usage admission.

    The reviewed mapping describes the finite views; it does not establish live
    source verification or grant runtime permission. Legacy builders stay fixed.
    """
    legacy = build_openai_cost_manifest()
    usage = build_openai_usage_manifest(
        evidence_reference=ANALYTICS_REFERENCE,
        mapping_digest=ANALYTICS_MAPPING_DIGEST,
    )
    cost = legacy.declarations[0]
    return replace(
        legacy,
        descriptor=replace(
            legacy.descriptor,
            adapter_version=ANALYTICS_VERSION,
            build_identity="agentmonitor-openai-analytics-v1.1.3",
        ),
        declarations=(
            replace(
                cost,
                evidence_reference=ANALYTICS_REFERENCE,
                sources=(
                    replace(cost.sources[0], evidence_reference=ANALYTICS_REFERENCE),
                ),
            ),
            usage.declarations[0],
        ),
        m0_mapping_id=ANALYTICS_REFERENCE,
        m0_mapping_version="1.1.0",
        m0_mapping_digest=ANALYTICS_MAPPING_DIGEST,
    )

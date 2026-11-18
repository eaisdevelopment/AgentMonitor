"""Experimental A01 analytics descriptors; live/scheduling admission is separate.

Finite mapping (2026-10-21 API, analytics-usage-cost-2026-08-24 beta):
- Cost: USD discounted cents -> exact USD; group workspace_id/api_key_id/model.
- Cost token_category: group token_type, token costs only; never the total.
- Usage: native typed token counts, requests (possibly execution spans), and
  web_search_requests; group workspace_id/api_key_id/model.
- Usage token_category: five native token fields, no server group_by parameter.
Both endpoints require read:analytics scope or an Admin API key. Existing
credential policy remains the owner-entered Admin API key. Null dimensions
remain null. Actor/user dimensions and arbitrary cross-products are excluded.
"""

from dataclasses import replace

from agentmonitor.adapters.providers.claude.anthropic_api.policy import (
    API_VERSION,
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

ADAPTER_ID = "agentmonitor.claude.anthropic-api"
ADAPTER_VERSION = "1.0.1"
EVIDENCE_REFERENCE = "M7-A01-ANTHROPIC-DOCS-2026-11-11"
ANALYTICS_VERSION = "1.1.1"
ANALYTICS_REFERENCE = "ANTHROPIC-ANALYTICS-1.1"
ANALYTICS_MAPPING_DIGEST = (
    "7cd61c517dff6870a35c737a68b43fd10b3dac235b0c69d2ed134823201b2515"
)


def build_anthropic_cost_manifest() -> CapabilityManifestV1:
    """Admit cost-only completed 7/30-day reads under the typed request policy.

    Source/request budgets and the serialized manifest remain unchanged; selected
    past intervals require the same policy and are not live-verified here.
    """
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


def build_anthropic_usage_manifest(
    *,
    evidence_reference: str,
    mapping_digest: str,
) -> CapabilityManifestV1:
    """Usage admission requires root's actual reviewed discovery artifact.

    The existing cost manifest/fingerprint is unchanged. This distinct additive
    descriptor never borrows cost-only discovery evidence or claims live access.
    """
    cost = build_anthropic_cost_manifest()
    declaration = cost.declarations[0]
    source = replace(
        declaration.sources[0],
        source_id=USAGE_SOURCE_ID,
        capability_id="api.usage",
        evidence_reference=evidence_reference,
    )
    return replace(
        cost,
        descriptor=replace(
            cost.descriptor,
            adapter_id=ADAPTER_ID + ".usage",
            build_identity="agentmonitor-anthropic-analytics-usage-v1",
        ),
        declarations=(
            replace(
                declaration,
                capability_id="api.usage",
                port_type="AnthropicUsageSourceV1",
                evidence_reference=evidence_reference,
                sources=(source,),
            ),
        ),
        m0_mapping_id=evidence_reference,
        m0_mapping_digest=mapping_digest,
    )


def build_anthropic_analytics_manifest() -> CapabilityManifestV1:
    """Current complete analytics source admission on the existing authority."""
    legacy = build_anthropic_cost_manifest()
    usage = build_anthropic_usage_manifest(
        evidence_reference=ANALYTICS_REFERENCE,
        mapping_digest=ANALYTICS_MAPPING_DIGEST,
    )
    cost = legacy.declarations[0]
    return replace(
        legacy,
        descriptor=replace(
            legacy.descriptor,
            adapter_version=ANALYTICS_VERSION,
            build_identity="agentmonitor-anthropic-analytics-v1.1.1",
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
        m0_mapping_version=ANALYTICS_VERSION,
        m0_mapping_digest=ANALYTICS_MAPPING_DIGEST,
    )

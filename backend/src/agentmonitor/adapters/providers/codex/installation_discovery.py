"""Typed discovery for the exact admitted local Codex installation."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from agentmonitor.adapters.providers.codex.installation import (
    discover_default_installation,
)
from agentmonitor.adapters.providers.codex.manifest import (
    CODEX_ADAPTER_ID,
    CODEX_ADAPTER_VERSION,
    CODEX_INSTALLATION_SOURCE_ID,
    M0_MAPPING_ID,
)
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    DiscoveredInstallationV1,
    DiscoveryCandidatesV1,
    DiscoveryOutcomeV1,
)

CODEX_INSTALLATION_PARSER_VERSION = "1.0.0"


def discover_codex_installation_v1() -> DiscoveryOutcomeV1:
    """Read only the bounded native version banner; emit no account candidate."""
    installation = discover_default_installation()
    collected_at = datetime.now(UTC)
    token = uuid4().hex
    provenance = ObservationProvenanceV1(
        provider_key="codex",
        capability_id="installation.discovery",
        capability_schema_version="1.0",
        adapter_id=CODEX_ADAPTER_ID,
        adapter_version=CODEX_ADAPTER_VERSION,
        provider_protocol_version="1.0.0",
        source_id=CODEX_INSTALLATION_SOURCE_ID,
        source_class="supported_cli",
        mechanism_version=f"codex-cli@{installation.provider_version}",
        parser_version=CODEX_INSTALLATION_PARSER_VERSION,
        provider_version=installation.provider_version,
        provider_version_availability=FieldAvailabilityV1("available"),
        observed_at=collected_at,
        observed_at_availability=FieldAvailabilityV1("available"),
        collected_at=collected_at,
        freshness_deadline=None,
        freshness_availability=FieldAvailabilityV1("unknown"),
        freshness_policy_id="codex-installation-point-in-time-v1",
        precision="exact",
        confidence="confirmed",
        confidence_reason_code="bounded_version_banner",
        value_kind="provider_reported",
        is_experimental=False,
        fallback_lineage=(),
        warnings=(),
        operation_id=OpaqueIdV1("codex-installation-" + token),
        correlation_id=OpaqueIdV1("codex-installation-corr-" + token),
        decision_reference=M0_MAPPING_ID,
        derivation_method=None,
        input_observation_ids=(),
    )
    value = DiscoveryCandidatesV1(
        installations=(
            DiscoveredInstallationV1(
                provider_key="codex",
                installation_ref=installation.installation_ref,
                product_version=installation.provider_version,
                platform_id=installation.platform_id,
                provenance=provenance,
            ),
        ),
        accounts=(),
    )
    return DiscoveryOutcomeV1.success(value, provenance)

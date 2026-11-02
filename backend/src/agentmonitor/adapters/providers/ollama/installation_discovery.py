"""Typed installation-only discovery for the exact admitted Ollama CLI."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from agentmonitor.adapters.providers.ollama.installation import (
    OllamaInstallationUnavailable,
    discover_installation,
)
from agentmonitor.adapters.providers.ollama.manifest import (
    OLLAMA_ADAPTER_ID,
    OLLAMA_ADAPTER_VERSION,
)
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    DiscoveredInstallationV1,
    DiscoveryCandidatesV1,
    DiscoveryOutcomeV1,
)

OLLAMA_INSTALLATION_SOURCE_ID = "ollama.cli.version.v1"
OLLAMA_INSTALLATION_PARSER_VERSION = "1.0.0"
OLLAMA_PROCESS_PLAN_ID = "M6-OLL-PROCESS-PLAN-001"


def discover_ollama_installation_v1() -> DiscoveryOutcomeV1:
    """Emit one exact real installation and no account candidate."""

    installation = discover_installation()
    if (
        installation.outcome != "success"
        or installation.installation_ref is None
        or installation.cli_version is None
    ):
        raise OllamaInstallationUnavailable("ollama_installation_unavailable")
    # Revalidate the same image before publishing its installation evidence.
    installation.executable_for_process_observation()
    collected_at = datetime.now(UTC)
    token = uuid4().hex
    provenance = ObservationProvenanceV1(
        provider_key="ollama",
        capability_id="installation.discovery",
        capability_schema_version="1.0",
        adapter_id=OLLAMA_ADAPTER_ID,
        adapter_version=OLLAMA_ADAPTER_VERSION,
        provider_protocol_version="1.0.0",
        source_id=OLLAMA_INSTALLATION_SOURCE_ID,
        source_class="supported_cli",
        mechanism_version=f"ollama-cli@{installation.cli_version}",
        parser_version=OLLAMA_INSTALLATION_PARSER_VERSION,
        provider_version=installation.cli_version,
        provider_version_availability=FieldAvailabilityV1("available"),
        observed_at=installation.observed_at,
        observed_at_availability=FieldAvailabilityV1("available"),
        collected_at=collected_at,
        freshness_deadline=None,
        freshness_availability=FieldAvailabilityV1("unknown"),
        freshness_policy_id="ollama-installation-point-in-time-v1",
        precision="exact",
        confidence="confirmed",
        confidence_reason_code="bounded_version_banner_and_executable_identity",
        value_kind="provider_reported",
        is_experimental=False,
        fallback_lineage=(),
        warnings=(),
        operation_id=OpaqueIdV1("ollama-installation-" + token),
        correlation_id=OpaqueIdV1("ollama-installation-corr-" + token),
        decision_reference=OLLAMA_PROCESS_PLAN_ID,
        derivation_method=None,
        input_observation_ids=(),
    )
    value = DiscoveryCandidatesV1(
        installations=(
            DiscoveredInstallationV1(
                provider_key="ollama",
                installation_ref=installation.installation_ref,
                product_version=installation.cli_version,
                platform_id=installation.platform_id,
                provenance=provenance,
            ),
        ),
        accounts=(),
    )
    return DiscoveryOutcomeV1.success(value, provenance)

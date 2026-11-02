"""Non-secret source metadata for the owner-initiated balance probe.

This describes the documented endpoint and does not admit it to the scheduled
provider manifest. A successful, generation-bound verification is separate.
"""

import hashlib

from agentmonitor.contracts.provider_system_v1 import ProviderSourceV1


def ollama_cloud_probe_source() -> ProviderSourceV1:
    return ProviderSourceV1(
        source_id="ollama.cloud.balance.v1",
        provider_key="ollama",
        capability_id="subscription.quota",
        source_class="documented_api",
        stability="documented",
        mechanism_version="1.0.0",
        credential_role="owner_supplied_api_key",
        side_effect_class="read_only",
        evidence_reference="ollama-balance-api-2026-11",
        is_experimental=False,
    )


def ollama_cloud_probe_fingerprint() -> str:
    """Bind a first verification to its documented source descriptor."""
    source = ollama_cloud_probe_source()
    values = (
        "agentmonitor-ollama-cloud-probe-v1",
        source.source_id,
        source.provider_key,
        source.capability_id,
        source.source_class,
        source.mechanism_version,
        source.credential_role,
        source.side_effect_class,
        source.evidence_reference,
    )
    return hashlib.sha256("\0".join(values).encode()).hexdigest()

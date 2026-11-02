"""Non-secret source metadata for the owner-initiated balance probe.

This describes the documented endpoint and does not admit it to the scheduled
provider manifest. A successful, generation-bound verification is separate.
"""

import hashlib
import json
from dataclasses import asdict

from agentmonitor.adapters.providers.ollama.cloud_balance.source import (
    CLOUD_BALANCE_POLICY_V1,
)
from agentmonitor.adapters.providers.ollama.manifest import OLLAMA_ADAPTER_VERSION
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    ProviderSourceV1,
    ScheduledSourceAdmissionPolicyV1,
    ScheduledSourceAdmissionProofV1,
)
from agentmonitor.contracts.registry_v1 import ActiveCredentialBindingRefV1
from agentmonitor.modules.provider_system.domain.protocol import (
    scheduled_source_policy_digest_v1,
)


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
    """Bind verification to source, adapter, parser and transport policy."""
    material = {
        "version": "agentmonitor-ollama-cloud-probe-v2",
        "adapter_version": OLLAMA_ADAPTER_VERSION,
        "payload_schema": "ProviderQuotaInputV2@2",
        "source": asdict(ollama_cloud_probe_source()),
        "transport": asdict(CLOUD_BALANCE_POLICY_V1),
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def ollama_cloud_scheduled_policy() -> ScheduledSourceAdmissionPolicyV1:
    """Describe scoped scheduled bounds; actual admission requires real lineage."""
    return ScheduledSourceAdmissionPolicyV1(
        policy_ref=OpaqueIdV1("ollama-cloud-scheduled-v1"),
        provider_key="ollama",
        authority_id="ollama.com",
        capability_id="subscription.quota",
        source_id="ollama.cloud.balance.v1",
        adapter_version=OLLAMA_ADAPTER_VERSION,
        source_fingerprint=ollama_cloud_probe_fingerprint(),
        payload_schema="ProviderQuotaInputV2@2",
        minimum_interval_seconds=60,
        maximum_concurrency=1,
        automatic_retry_count=0,
        provider_request_count=1,
        collection_policy_id="ollama-cloud-collection",
        collection_policy_version="1.0.0",
        rate_policy_id="ollama-cloud-global-rate",
        rate_policy_version="1.0.0",
        fairness_policy_id="ollama-cloud-round-robin",
        fairness_policy_version="1.0.0",
        invalidation_policy_id="ollama-cloud-generation-and-outcome",
        invalidation_policy_version="1.0.0",
    )


def require_matching_scheduled_proof(
    binding: ActiveCredentialBindingRefV1, proof: ScheduledSourceAdmissionProofV1
) -> None:
    """A scheduled source accepts only the current binding and exact policy."""
    policy = ollama_cloud_scheduled_policy()
    if (
        not isinstance(binding, ActiveCredentialBindingRefV1)
        or not isinstance(proof, ScheduledSourceAdmissionProofV1)
        or proof.account_id != binding.account_id
        or proof.binding_id != binding.binding_id
        or proof.binding_generation != binding.generation
        or proof.policy_ref != policy.policy_ref
        or proof.policy_digest != scheduled_source_policy_digest_v1(policy)
        or proof.provider_key != policy.provider_key
        or proof.authority_id != policy.authority_id
        or proof.capability_id != policy.capability_id
        or proof.source_id != policy.source_id
        or proof.adapter_version != policy.adapter_version
        or proof.source_fingerprint != policy.source_fingerprint
        or proof.payload_schema != policy.payload_schema
        or proof.identity_provenance != "owner_asserted"
        or proof.authorization_signal
        in {
            "credential_unauthorized",
            "provider_schema_incompatible",
            "outcome_unresolved",
        }
    ):
        raise ValueError("ollama_cloud_scheduled_proof_invalid")

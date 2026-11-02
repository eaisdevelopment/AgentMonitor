"""Pure construction of an owner-requested, exact-target M04 verification run."""

import hashlib
from datetime import datetime, timedelta

from agentmonitor.adapters.providers.ollama.manifest import OLLAMA_ADAPTER_VERSION
from agentmonitor.contracts.collection_control_v1 import (
    CollectionRunAdmissionV2,
    OllamaCloudRequestLeaseV1,
    OllamaCloudVerificationJobClaimV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    CloudMonitoringTargetV1,
    ProviderTargetRefV1,
)


def _digest(*values: str) -> str:
    return hashlib.sha256("\0".join(values).encode()).hexdigest()


def build_verification_run(
    claim: OllamaCloudVerificationJobClaimV1,
    graph: CloudMonitoringTargetV1,
    lease: OllamaCloudRequestLeaseV1,
    registry_revision: int,
    manifest_fingerprint: str,
    now: datetime,
) -> CollectionRunAdmissionV2:
    """Preserve the durable request's provenance and reject target relabelling."""
    if (
        claim.account_id != graph.account_id
        or claim.account_id != lease.account_id
        or claim.access_target_id != graph.access_target_id
        or claim.binding_generation != graph.binding.generation
        or claim.schedule_id != lease.schedule_id
        or claim.worker_instance_id != lease.scheduler_instance_id
        or graph.lifecycle != "active"
        or graph.identity_state != "owner_confirmed"
        or not claim.claimed_at <= now < claim.claim_expires_at
        or not lease.started_at <= now < lease.lease_expires_at
    ):
        raise ValueError("ollama_cloud_verification_target_mismatch")
    target = _digest(
        "ollama",
        graph.access_target_id.value,
        graph.account_id.value,
        graph.profile_id.value,
        graph.resource_id.value,
        graph.binding.binding_id.value,
        str(graph.binding.generation),
    )
    request_digest = _digest(claim.job_id.value, target, claim.idempotency_key_digest)
    suffix = _digest(claim.job_id.value, lease.admission_id.value)[:32]
    deadline = min(lease.lease_expires_at, now + timedelta(seconds=30))
    return CollectionRunAdmissionV2(
        run_id=OpaqueIdV1("ollama-cloud-run-" + suffix),
        schedule_id=claim.schedule_id,
        request_id=claim.job_id,
        trigger="reauth_verification",
        operation_family="collect.subscription.quota",
        requested_capability_ids=("subscription.quota",),
        capability_set_version="1.0.0",
        request_auth_method="dashboard_session",
        request_principal_id=claim.request_principal_id,
        correlation_id=claim.job_id,
        causation_id=claim.job_id,
        target_key_digest=target,
        provider_key="ollama",
        provider_target=ProviderTargetRefV1("cloud_service", graph.access_target_id),
        account_id=graph.account_id,
        profile_id=graph.profile_id,
        resource_id=graph.resource_id,
        capability_id="subscription.quota",
        source_id="ollama.cloud.balance.v1",
        adapter_version=OLLAMA_ADAPTER_VERSION,
        provider_version=None,
        adapter_protocol_version="1.0.0",
        manifest_fingerprint=manifest_fingerprint,
        collection_policy_version="1.0.0",
        registry_revision=registry_revision,
        retry_chain_id=claim.job_id,
        attempt_ordinal=1,
        target_generation=claim.binding_generation,
        scheduler_instance_id=claim.worker_instance_id,
        lease_policy_version="1.0.0",
        budget_policy_id="ollama-cloud-verification-v1",
        budget_policy_version="1.0.0",
        budget_scope_digest=_digest("ollama-cloud-global"),
        budget_dimension="provider_requests",
        budget_unit="request",
        budget_units=1,
        budget_limit_units=1,
        budget_window_start=now,
        budget_window_end=now + timedelta(seconds=60),
        payload_schema="ProviderQuotaInputV2@2",
        idempotency_key_digest=claim.idempotency_key_digest,
        request_digest=request_digest,
        requested_at=now,
        deadline_at=deadline,
    )

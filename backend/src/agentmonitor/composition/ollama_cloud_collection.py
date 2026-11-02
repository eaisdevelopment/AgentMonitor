"""Unwired cloud collection primitives; no service scheduler is enabled."""

# ruff: noqa: E501 -- the canonical M04 import path is intentionally explicit.

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.collection_control.sqlite.ollama_cloud_admission import (
    SqliteOllamaCloudAdmissionRepositoryV1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.collection import (
    admission_outcome_for_source,
    cloud_balance_to_capacity,
    validate_cloud_target,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.source import (
    CLOUD_BALANCE_POLICY_V1,
    CloudBalanceSourceResultV1,
)
from agentmonitor.composition.ollama_capacity_commit import ollama_capacity_repository
from agentmonitor.contracts.capacity_v1 import (
    CapacityCommitRequestV1,
    CapacitySubjectV1,
)
from agentmonitor.contracts.collection_control_v1 import (
    CollectionRunAdmissionV1,
    OllamaCloudAdmissionDecisionV1,
    OllamaCloudRequestAcquireV1,
    OllamaCloudRequestCompletionV1,
    OllamaCloudRequestLeaseV1,
)
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import ActiveCredentialBindingRefV1
from agentmonitor.modules.capacity.domain.payload_digest import capacity_payload_digest


class OllamaCloudCollectionV1:
    """Acquire the durable fair gate and commit only fully fenced observations.

    This object is deliberately not registered in the service. Source I/O,
    registry target selection and keyring grants must be provided by the future
    authorized caller; acquisition remains disabled until source admission.
    """

    def __init__(self, reference: DatabaseRefV1) -> None:
        self._reference = reference
        self._admission = SqliteOllamaCloudAdmissionRepositoryV1(reference)
        self._instance = OpaqueIdV1("ollama-cloud-" + uuid.uuid4().hex)

    def acquire_next(self, now: datetime) -> OllamaCloudAdmissionDecisionV1:
        """Use M04's durable round-robin schedule selector, once admitted."""
        policy = CLOUD_BALANCE_POLICY_V1
        if not (
            policy.authenticated_collection_admitted
            and policy.operation_deadline_strict
            and policy.dns_deadline_strict
            and policy.wire_header_limit_strict
        ):
            raise ValueError("ollama_cloud_source_not_admitted")
        return self._admission.acquire(
            OllamaCloudRequestAcquireV1(
                admission_id=OpaqueIdV1("ollama-cloud-attempt-" + uuid.uuid4().hex),
                scheduler_instance_id=self._instance,
                requested_at=now,
                lease_expires_at=now + timedelta(seconds=60),
                jitter_seconds=secrets.randbelow(11),
            )
        )

    def commit_reading(
        self,
        lease: OllamaCloudRequestLeaseV1,
        binding: ActiveCredentialBindingRefV1,
        run: CollectionRunAdmissionV1,
        subject: CapacitySubjectV1,
        registry_revision: int,
        source: CloudBalanceSourceResultV1,
        provenance: ObservationProvenanceV1,
    ):
        """Project a real result then commit under both M04 and M02 fences."""
        validate_cloud_target(
            lease.account_id.value,
            binding.account_id.value,
            subject.account_id.value,
            subject.provider_key,
        )
        if (
            source.state != "success"
            or source.http_status != 200
            or source.balance is None
            or source.source_id != "ollama.cloud.balance.v1"
            or provenance.provider_key != "ollama"
            or provenance.capability_id != "subscription.quota"
            or provenance.source_id != source.source_id
            or run.schedule_id != lease.schedule_id
            or run.account_id != lease.account_id
            or run.provider_key != "ollama"
            or run.capability_id != "subscription.quota"
            or run.source_id != source.source_id
            or run.installation_id != subject.installation_id
            or run.resource_id != subject.resource_id
            or run.registry_revision != registry_revision
            or provenance.operation_id != run.run_id
            or provenance.correlation_id != run.correlation_id
            or provenance.observed_at != source.observed_at
        ):
            raise ValueError("ollama_cloud_source_binding_invalid")
        payload = cloud_balance_to_capacity(source.balance, subject, registry_revision)
        request = CapacityCommitRequestV1(
            run_id=run.run_id,
            target_generation=run.target_generation,
            capability_id="subscription.quota",
            payload_schema=run.payload_schema,
            payload_digest=capacity_payload_digest(payload),
            terminal_state="partial",
            payload=payload,
            provenance=provenance,
        )
        receipt = ollama_capacity_repository(
            self._reference, lease, run, request.payload_digest
        ).commit_fenced(request, binding)
        self._complete(lease, source)
        return receipt

    def complete_failure(
        self, lease: OllamaCloudRequestLeaseV1, source: CloudBalanceSourceResultV1
    ):
        """Record only a failed source; successful reads require a durable commit."""
        if source.state == "success":
            raise ValueError("ollama_cloud_success_requires_commit")
        return self._complete(lease, source)

    def _complete(
        self, lease: OllamaCloudRequestLeaseV1, source: CloudBalanceSourceResultV1
    ):
        """Persist cooldown; unrepresentable retry or expired lease stays blocked."""
        if source.retry_after_state == "unrepresentable":
            raise ValueError("ollama_cloud_retry_after_unrepresentable")
        now = datetime.now(UTC)
        if now > lease.lease_expires_at:
            raise ValueError("ollama_cloud_lease_expired")
        state = admission_outcome_for_source(source.state)
        return self._admission.complete(
            OllamaCloudRequestCompletionV1(
                admission_id=lease.admission_id,
                scheduler_instance_id=lease.scheduler_instance_id,
                schedule_id=lease.schedule_id,
                fencing_token=lease.fencing_token,
                started_at=lease.started_at,
                response_received_at=now,
                outcome=state,
                retry_after_seconds=(
                    source.retry_after_seconds if state == "rate_limited" else None
                ),
                jitter_seconds=secrets.randbelow(11),
            )
        )

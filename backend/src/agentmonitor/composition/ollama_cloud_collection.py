"""Unwired cloud collection primitives; no service scheduler is enabled."""

# ruff: noqa: E501 -- the canonical M04 import path is intentionally explicit.

import secrets
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.ollama_cloud_admission import (
    SqliteOllamaCloudAdmissionRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCredentialBindingsV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.collection import (
    admission_outcome_for_source,
    cloud_balance_to_capacity,
    eligible_cloud_account,
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
    CollectionFailedV1,
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
from agentmonitor.modules.collection_control.application.executor import (
    ExecuteCollectionRunV1,
)
from agentmonitor.modules.registry.domain.credential_binding import (
    resolve_active_credential_binding,
)


def require_source_admitted() -> None:
    """Never schedule provider I/O without all approved source bounds."""
    policy = CLOUD_BALANCE_POLICY_V1
    if not (
        policy.authenticated_collection_admitted
        and policy.operation_deadline_strict
        and policy.dns_deadline_strict
        and policy.wire_header_limit_strict
    ):
        raise ValueError("ollama_cloud_source_not_admitted")


class OllamaCloudCollectionV1:
    """Acquire the durable fair gate and commit only fully fenced observations.

    This object is deliberately not registered in the service. Source I/O,
    registry target selection and keyring grants must be provided by the future
    authorized caller; acquisition remains disabled until source admission.
    """

    def __init__(self, reference: DatabaseRefV1) -> None:
        self._reference = reference
        self._admission = SqliteOllamaCloudAdmissionRepositoryV1(reference)
        self._runs = SqliteCollectionRepositoryV1(reference)
        self._registry = SqliteRegistryRepositoryV1(reference)
        self._bindings = SqliteCredentialBindingsV1(reference)
        self._instance = OpaqueIdV1("ollama-cloud-" + uuid.uuid4().hex)

    def _eligible_binding(
        self, run: CollectionRunAdmissionV1
    ) -> ActiveCredentialBindingRefV1:
        """Re-read exact account, profile, resource and current key ownership."""
        if (
            run.account_id is None
            or run.profile_id is None
            or run.resource_id is None
            or run.provider_key != "ollama"
            or run.capability_id != "subscription.quota"
            or run.source_id != "ollama.cloud.balance.v1"
        ):
            raise ValueError("ollama_cloud_target_ineligible")
        account = self._registry.get_account(run.account_id)
        if (
            account is None
            or not eligible_cloud_account(
                account.provider_key,
                account.lifecycle,
                account.is_effective_monitoring_enabled,
                account.identity_state,
            )
            or account.registry_revision != run.registry_revision
        ):
            raise ValueError("ollama_cloud_target_ineligible")
        profiles = self._registry.list_monitoring_profiles(run.account_id)
        resources = self._registry.list_account_resources(run.account_id)
        matches = [
            profile for profile in profiles if profile.profile_id == run.profile_id
        ]
        matching_resources = [
            resource
            for resource in resources
            if resource.resource_id == run.resource_id
        ]
        if len(matches) != 1 or len(matching_resources) != 1:
            raise ValueError("ollama_cloud_target_ineligible")
        profile, resource = matches[0], matching_resources[0]
        if (
            profile.lifecycle != "active"
            or profile.management_state != "managed"
            or profile.is_protected_default
            or profile.compatibility_state != "compatible"
            or profile.identity_state not in {"owner_confirmed", "provider_verified"}
            or profile.purpose not in {"subscription", "combined"}
            or profile.provider_installation_id != run.installation_id
            or resource.lifecycle != "active"
            or resource.kind != "subscription_pool"
            or resource.resource_id not in profile.resource_ids
            or profile.profile_id not in resource.linked_profile_ids
        ):
            raise ValueError("ollama_cloud_target_ineligible")
        active = resolve_active_credential_binding(self._bindings.read(run.account_id))
        if active is None:
            raise ValueError("ollama_cloud_target_ineligible")
        return active

    def register_target(self, run: CollectionRunAdmissionV1) -> None:
        """Register a genuine eligible account schedule without creating a run."""
        require_source_admitted()
        self._eligible_binding(run)
        self._admission.register_schedule(run)

    def execute_admitted(
        self,
        lease: OllamaCloudRequestLeaseV1,
        run: CollectionRunAdmissionV1,
        subject: CapacitySubjectV1,
        collect: Callable[
            [], tuple[CloudBalanceSourceResultV1, ObservationProvenanceV1 | None]
        ],
    ):
        """Create and progress an M04 run around one admitted real source read."""
        require_source_admitted()
        binding = self._eligible_binding(run)
        validate_cloud_target(
            lease.account_id.value,
            binding.account_id.value,
            subject.account_id.value,
            subject.provider_key,
        )
        if (
            run.schedule_id != lease.schedule_id
            or run.account_id != lease.account_id
            or run.scheduler_instance_id != lease.scheduler_instance_id
            or run.installation_id != subject.installation_id
            or run.resource_id != subject.resource_id
        ):
            raise ValueError("ollama_cloud_target_mismatch")
        admitted = self._runs.admit_run(run)
        if admitted.state != "queued":
            raise ValueError("ollama_cloud_run_not_dispatchable")
        now = datetime.now(UTC)
        self._runs.mark_running(run.run_id, now, fencing_token=admitted.fencing_token)
        self._admission.assert_active(lease, datetime.now(UTC))
        # A thrown or interrupted source leaves the rate lease unresolved; do not
        # infer that no 429 happened or open the gate to another request.
        source, provenance = collect()
        completed = datetime.now(UTC)
        if source.state != "success":
            failed = CollectionFailedV1(
                run.run_id, "failed", "ollama_cloud_read_failed", completed
            )
            self._runs.finalize_failed(failed, fencing_token=admitted.fencing_token)
            self.complete_failure(lease, source)
            return failed
        if source.balance is None or provenance is None:
            raise ValueError("ollama_cloud_source_binding_invalid")
        payload = cloud_balance_to_capacity(
            source.balance, subject, run.registry_revision
        )
        digest = capacity_payload_digest(payload)
        self._runs.mark_committing(
            run.run_id,
            fencing_token=admitted.fencing_token,
            payload_digest=digest,
            committing_at=completed,
            terminal_state="partial",
        )
        receipt = self.commit_reading(
            lease, binding, run, subject, run.registry_revision, source, provenance
        )
        self._runs.finalize_committed(
            receipt,
            terminal_state="partial",
            completed_at=datetime.now(UTC),
            fencing_token=admitted.fencing_token,
        )
        return receipt

    def recover_committing_runs(
        self,
        *,
        as_of: datetime,
        owner_stale_before: datetime,
        recovery_lease_expires_at: datetime,
        maximum_runs: int = 10,
    ):
        """Recover M04 receipts without making a provider request.

        An unresolved global rate lease stays blocked for separate reconciliation.
        """
        executor = ExecuteCollectionRunV1(
            self._runs, SqliteCapacityRepositoryV1(self._reference)
        )
        return executor.recover_pending_commits(
            provider_key="ollama",
            capability_id="subscription.quota",
            source_id="ollama.cloud.balance.v1",
            as_of=as_of,
            owner_stale_before=owner_stale_before,
            recovery_instance_id=self._instance,
            recovery_lease_expires_at=recovery_lease_expires_at,
            maximum_runs=maximum_runs,
        )

    def acquire_next(self, now: datetime) -> OllamaCloudAdmissionDecisionV1:
        """Use M04's durable round-robin schedule selector, once admitted."""
        require_source_admitted()
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

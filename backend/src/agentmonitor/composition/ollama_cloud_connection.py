"""Owner-asserted cloud connection composition; no credential or network I/O."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import datetime
from typing import Literal

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
)
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.ollama_cloud_admission import (  # noqa: E501
    OllamaCloudAdmissionRepositoryErrorV1,
    SqliteOllamaCloudAdmissionRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.integration.sqlite.ollama_cloud_schedule_snapshot import (  # noqa: E501
    OllamaCloudScheduleSnapshotErrorV1,
    SqliteOllamaCloudScheduleSnapshotRepositoryV1,
)
from agentmonitor.adapters.persistence.integration.sqlite.ollama_cloud_verification_enqueue_v2 import (  # noqa: E501
    SqliteAtomicOllamaCloudVerificationEnqueueRepositoryV2,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
    SqliteCredentialBindingsV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.probe_descriptor import (
    ollama_cloud_probe_fingerprint,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.verification_run import (
    cloud_schedule_target_digest,
)
from agentmonitor.adapters.providers.ollama.manifest import OLLAMA_ADAPTER_VERSION
from agentmonitor.composition.ollama_cloud_collection import (
    OllamaCloudCollectionV1,
    OllamaCloudTargetIneligible,
)
from agentmonitor.contracts.cloud_schedule_status_v1 import CloudScheduleStatusV1
from agentmonitor.contracts.collection_control_v1 import (
    OllamaCloudLatestSourceSignalQueryV1,
    OllamaCloudVerificationEnqueueV2,
    OllamaCloudVerificationReplayQueryV1,
    OllamaCloudVerificationTargetV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    ActiveCredentialBindingRefV1,
    AssertCredentialAccountOwnershipCommandV1,
    CredentialConnectionStatusV1,
    InitiateOllamaCloudVerificationCommandV1,
    ProviderTargetRefV1,
)
from agentmonitor.modules.collection_control.application.ollama_cloud_admission import (
    AtomicallyEnqueueOllamaCloudVerificationV2,
)
from agentmonitor.modules.provider_system.domain.protocol import (
    current_access_from_signal,
)
from agentmonitor.modules.registry.application.accounts import (
    AssertCredentialAccountOwnershipV1,
)
from agentmonitor.modules.registry.application.organizations import (
    RegistryCommandConflictV1,
)
from agentmonitor.modules.registry.domain.cloud_connection_status import (
    derive_connection_status,
    scheduled_monitoring_state,
)
from agentmonitor.modules.registry.domain.cloud_verification import (
    cloud_verification_enqueue_account_version,
)
from agentmonitor.modules.registry.domain.credential_binding import (
    resolve_active_credential_binding,
)


def _enqueue_conflict(
    error: OllamaCloudAdmissionRepositoryErrorV1,
) -> RegistryCommandConflictV1 | None:
    if error.code == "ollama_cloud_verification_idempotency_conflict":
        return RegistryCommandConflictV1("registry_idempotency_conflict")
    return None


class OllamaCloudConnectionServiceV1:
    """Prepare one owner-asserted request; the worker owns all later I/O.

    The caller must supply a non-secret readiness check that includes the
    owner's credential policy, source admission and bounded worker availability.
    This candidate is not wired into the application.
    """

    def __init__(
        self,
        reference: DatabaseRefV1,
        *,
        ready: Callable[[], bool],
        monitoring_ready: Callable[[], bool] = lambda: False,
        location_current: Callable[[], bool] = lambda: False,
    ) -> None:
        self._reference = reference
        self._registry = SqliteRegistryRepositoryV1(reference)
        self._bindings = SqliteCredentialBindingsV1(reference)
        self._cloud = SqliteCloudCredentialRegistryV1(reference)
        self._admission = SqliteOllamaCloudAdmissionRepositoryV1(reference)
        self._runs = SqliteCollectionRepositoryV1(reference)
        self._capacity = SqliteCapacityRepositoryV1(reference)
        self._ready = ready
        self._monitoring_ready = monitoring_ready
        self._location_current = location_current
        self._schedule_snapshot = SqliteOllamaCloudScheduleSnapshotRepositoryV1(
            reference
        )
        self._collector = OllamaCloudCollectionV1(reference)

    def _monitoring_status(
        self,
        enabled: bool,
        binding: ActiveCredentialBindingRefV1 | None,
        account_record_version: int,
    ) -> tuple[Literal["off", "waiting", "scheduled", "unavailable", "reading"], str]:
        ready = self._ready() and self._monitoring_ready() and self._location_current()
        if not enabled or not ready or binding is None:
            return scheduled_monitoring_state(
                enabled, ready, binding is not None, False, False
            )
        proof = None
        try:
            proof = self._collector.scheduled_proof_for_binding(binding)
        except OllamaCloudTargetIneligible:
            pass
        graph = self._cloud.read_monitoring_target(binding.account_id)
        if graph is None or graph.binding != binding:
            return scheduled_monitoring_state(True, True, True, False, False)
        digest = cloud_schedule_target_digest(graph)
        target = CloudScheduleStatusV1(
            "ollama-cloud-" + digest[:40],
            digest,
            graph.account_id.value,
            graph.profile_id.value,
            graph.resource_id.value,
            graph.access_target_id.value,
            binding.generation,
        )
        fingerprint = ollama_cloud_probe_fingerprint()
        try:
            registered, reading, latest = (
                self._schedule_snapshot.read_authorized_snapshot(
                    target,
                    account_record_version,
                    binding,
                    fingerprint,
                )
            )
        except OllamaCloudScheduleSnapshotErrorV1:
            return "unavailable", "source_not_admitted"
        admitted = (
            proof is not None and latest == proof.authorization_signal_run_id.value
        )
        return scheduled_monitoring_state(
            True, True, True, admitted, registered, reading
        )

    def _verified(self, binding: ActiveCredentialBindingRefV1) -> bool:
        receipt = self._cloud.read_current_verification(binding)
        if receipt is None:
            return False
        graph = self._cloud.read_monitoring_target(binding.account_id)
        if (
            graph is None
            or graph.binding != binding
            or graph.lifecycle != "active"
            or graph.identity_state != "owner_confirmed"
            or graph.access_target_id != receipt.access_target_id
        ):
            return False
        run = self._runs.get_run(receipt.run_id)
        commit = self._capacity.get_commit_status(receipt.run_id, "subscription.quota")
        return (
            run.state in {"succeeded", "partial"}
            and run.account_id == binding.account_id
            and run.resource_id == graph.resource_id
            and run.provider_key == "ollama"
            and run.capability_id == "subscription.quota"
            and run.source_id == receipt.source_id
            and run.adapter_version == receipt.adapter_version
            and run.payload_digest == receipt.payload_digest
            and commit.state == "committed"
            and commit.receipt is not None
            and commit.receipt.payload_digest == receipt.payload_digest
        )

    def read(
        self, account_id: OpaqueIdV1, as_of: datetime
    ) -> CredentialConnectionStatusV1:
        account = self._registry.get_account(account_id)
        if (
            account is None
            or account.provider_key != "ollama"
            or account.lifecycle == "archived"
        ):
            raise ValueError("ollama_cloud_account_unavailable")
        binding = resolve_active_credential_binding(self._bindings.read(account_id))
        monitoring_state, monitoring_reason = self._monitoring_status(
            account.is_effective_monitoring_enabled, binding, account.record_version
        )
        if binding is None:
            return CredentialConnectionStatusV1(
                account_id,
                "not_configured",
                False,
                None,
                None,
                "binding_absent",
                monitoring_state,
                monitoring_reason,
            )
        status = self._admission.read_verification_status(
            account_id, binding.generation, as_of
        )
        job = status.job
        verified = self._verified(binding)
        signal_reason = job.reason_code if job else None
        job_state = job.state if job else None
        gate_state = status.gate_state
        observed_at = job.terminal_at if job is not None else None
        if verified:
            graph = self._cloud.read_monitoring_target(account_id)
            if graph is None:
                verified = False
                gate_state = "unresolved"
            else:
                signal = self._admission.read_latest_source_signal(
                    OllamaCloudLatestSourceSignalQueryV1(
                        account_id,
                        binding.generation,
                        graph.access_target_id,
                        "subscription.quota",
                        "ollama.cloud.balance.v1",
                        OLLAMA_ADAPTER_VERSION,
                        ollama_cloud_probe_fingerprint(),
                        "ProviderQuotaInputV2@2",
                        as_of,
                    )
                )
                if signal.signal_observed_at is not None:
                    observed_at = signal.signal_observed_at
                verified = current_access_from_signal(signal.signal)
                if verified:
                    windows = self._capacity.list_quota_windows(
                        account_id, graph.resource_id, "subscription.quota", as_of
                    )
                    current_windows = tuple(
                        item
                        for item in windows
                        if item.collection_run_id == signal.run_id
                    )
                    verified = account.is_effective_monitoring_enabled and any(
                        item.freshness == "fresh" for item in current_windows
                    )
                    if not verified:
                        signal_reason, job_state = "last_check_stale", "terminal"
                        if (
                            not account.is_effective_monitoring_enabled
                            or not current_windows
                            or any(
                                item.freshness != "stale" for item in current_windows
                            )
                        ):
                            gate_state = "unresolved"
                if not verified:
                    if signal.signal == "credential_unauthorized":
                        signal_reason, job_state = "unauthorized", "terminal"
                    elif signal.signal == "rate_limited":
                        signal_reason, job_state = "rate_limited", "terminal"
                    elif signal.signal == "authorization_unavailable":
                        signal_reason, job_state = (
                            "authorization_unavailable",
                            "terminal",
                        )
                    elif signal.signal == "transient_failure":
                        signal_reason, job_state = "transient_failure", "terminal"
                    elif signal.signal == "verified_success":
                        signal_reason, job_state = "last_check_stale", "terminal"
                    else:
                        gate_state = "unresolved"
        state, can_verify = derive_connection_status(
            True,
            verified,
            job_state,
            signal_reason,
            gate_state,
            self._ready() and self._location_current(),
        )
        return CredentialConnectionStatusV1(
            account_id,
            state,
            can_verify,
            binding.generation,
            observed_at,
            "cloud_connection_" + state,
            monitoring_state,
            monitoring_reason,
        )

    def initiate(
        self, command: InitiateOllamaCloudVerificationCommandV1
    ) -> CredentialConnectionStatusV1:
        try:
            replay = self._admission.replay_verification(
                OllamaCloudVerificationReplayQueryV1(
                    command.idempotency_key,
                    command.principal_id,
                    command.account_id,
                    command.expected_account_record_version,
                )
            )
        except OllamaCloudAdmissionRepositoryErrorV1 as error:
            conflict = _enqueue_conflict(error)
            if conflict is not None:
                raise conflict from None
            raise
        if replay is not None:
            return self.read(command.account_id, command.requested_at)
        if not self._ready():
            raise ValueError("ollama_cloud_verification_unavailable")
        account = self._registry.get_account(command.account_id)
        if (
            account is None
            or account.provider_key != "ollama"
            or account.lifecycle == "archived"
        ):
            raise ValueError("ollama_cloud_account_unavailable")
        binding = resolve_active_credential_binding(
            self._bindings.read(command.account_id)
        )
        if binding is None:
            raise ValueError("ollama_cloud_binding_unavailable")
        if not self._location_current():
            raise ValueError("ollama_cloud_verification_unavailable")
        target = self._cloud.reconcile_access_target(
            provider_key="ollama",
            authority_id="ollama.com",
            manifest_fingerprint=ollama_cloud_probe_fingerprint(),
            as_of=command.requested_at,
        )
        graph = self._cloud.read_monitoring_target(command.account_id)
        owner_assertion_required = (
            graph is None
            or account.record_version != command.expected_account_record_version
        )
        if owner_assertion_required:
            account, graph = AssertCredentialAccountOwnershipV1(self._registry)(
                AssertCredentialAccountOwnershipCommandV1(
                    command.idempotency_key,
                    command.principal_id,
                    command.account_id,
                    target.access_target_id,
                    command.expected_account_record_version,
                    binding,
                    command.requested_at,
                )
            )
        expected_enqueue_account_record_version = (
            cloud_verification_enqueue_account_version(
                command_expected_version=command.expected_account_record_version,
                owner_assertion_required=owner_assertion_required,
            )
        )
        if account.record_version != expected_enqueue_account_record_version:
            raise RegistryCommandConflictV1("registry_account_version_conflict")
        if graph is None:
            raise ValueError("ollama_cloud_target_changed")
        if (
            graph.account_id != command.account_id
            or graph.access_target_id != target.access_target_id
            or graph.binding != binding
            or graph.lifecycle != "active"
            or graph.identity_state != "owner_confirmed"
        ):
            raise ValueError("ollama_cloud_target_changed")
        digest = hashlib.sha256(
            "\0".join(
                (
                    "ollama",
                    target.access_target_id.value,
                    command.account_id.value,
                    graph.profile_id.value,
                    graph.resource_id.value,
                    binding.binding_id.value,
                    str(binding.generation),
                )
            ).encode()
        ).hexdigest()
        schedule_id = OpaqueIdV1("ollama-cloud-" + digest[:40])
        self._admission.register_verification_target(
            OllamaCloudVerificationTargetV1(
                schedule_id,
                command.account_id,
                graph.profile_id,
                graph.resource_id,
                ProviderTargetRefV1("cloud_service", target.access_target_id),
                digest,
                binding.generation,
                command.requested_at,
            )
        )
        try:
            AtomicallyEnqueueOllamaCloudVerificationV2(
                SqliteAtomicOllamaCloudVerificationEnqueueRepositoryV2(self._reference)
            )(
                OllamaCloudVerificationEnqueueV2(
                    idempotency_key=command.idempotency_key,
                    principal_id=command.principal_id,
                    schedule_id=schedule_id,
                    account_id=command.account_id,
                    access_target_id=target.access_target_id,
                    binding_generation=binding.generation,
                    requested_at=command.requested_at,
                    expected_account_record_version=(
                        command.expected_account_record_version
                    ),
                ),
                expected_enqueue_account_record_version,
                binding,
                ollama_cloud_probe_fingerprint(),
            )
        except OllamaCloudAdmissionRepositoryErrorV1 as error:
            if error.code == "ollama_cloud_verification_account_version_conflict":
                raise RegistryCommandConflictV1(
                    "registry_account_version_conflict"
                ) from None
            conflict = _enqueue_conflict(error)
            if conflict is not None:
                raise conflict from None
            raise
        return self.read(command.account_id, command.requested_at)

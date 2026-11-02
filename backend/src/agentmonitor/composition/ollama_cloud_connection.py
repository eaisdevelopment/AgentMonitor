"""Owner-asserted cloud connection composition; no credential or network I/O."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import datetime

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.ollama_cloud_admission import (  # noqa: E501
    SqliteOllamaCloudAdmissionRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
    SqliteCredentialBindingsV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.composition.ollama_cloud_collection import require_cloud_manifest
from agentmonitor.contracts.collection_control_v1 import (
    OllamaCloudVerificationEnqueueV1,
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
from agentmonitor.modules.provider_system.application.gateway import (
    get_manifest_fingerprint_v1,
)
from agentmonitor.modules.registry.application.accounts import (
    AssertCredentialAccountOwnershipV1,
)
from agentmonitor.modules.registry.domain.cloud_connection_status import (
    derive_connection_status,
)
from agentmonitor.modules.registry.domain.credential_binding import (
    resolve_active_credential_binding,
)


class OllamaCloudConnectionServiceV1:
    """Prepare one owner-asserted request; the worker owns all later I/O.

    The caller must supply a non-secret readiness check that includes the
    owner's credential policy, source admission and bounded worker availability.
    This candidate is not wired into the application.
    """

    def __init__(self, reference: DatabaseRefV1, *, ready: Callable[[], bool]) -> None:
        self._registry = SqliteRegistryRepositoryV1(reference)
        self._bindings = SqliteCredentialBindingsV1(reference)
        self._cloud = SqliteCloudCredentialRegistryV1(reference)
        self._admission = SqliteOllamaCloudAdmissionRepositoryV1(reference)
        self._runs = SqliteCollectionRepositoryV1(reference)
        self._capacity = SqliteCapacityRepositoryV1(reference)
        self._ready = ready

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
        if binding is None:
            return CredentialConnectionStatusV1(
                account_id, "not_configured", False, None, as_of, "binding_absent"
            )
        status = self._admission.read_verification_status(
            account_id, binding.generation, as_of
        )
        job = status.job
        state, can_verify = derive_connection_status(
            True,
            self._verified(binding),
            job.state if job else None,
            job.reason_code if job else None,
            status.gate_state,
            self._ready(),
        )
        return CredentialConnectionStatusV1(
            account_id,
            state,
            can_verify,
            binding.generation,
            as_of,
            "cloud_connection_" + state,
        )

    def initiate(
        self, command: InitiateOllamaCloudVerificationCommandV1
    ) -> CredentialConnectionStatusV1:
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
        manifest = require_cloud_manifest()
        target = self._cloud.reconcile_access_target(
            provider_key="ollama",
            authority_id="ollama.com",
            manifest_fingerprint=get_manifest_fingerprint_v1(manifest),
            as_of=command.requested_at,
        )
        graph = self._cloud.read_monitoring_target(command.account_id)
        if (
            graph is None
            or account.record_version != command.expected_account_record_version
        ):
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
        self._admission.enqueue_verification(
            OllamaCloudVerificationEnqueueV1(
                command.idempotency_key,
                command.principal_id,
                schedule_id,
                command.account_id,
                target.access_target_id,
                binding.generation,
                command.requested_at,
            )
        )
        return self.read(command.account_id, command.requested_at)

"""Bind M04 and M02 transaction fences to Ollama cloud capacity writes."""

# ruff: noqa: E501 -- the canonical M04 import path is intentionally explicit.

from datetime import UTC, datetime

from sqlalchemy.engine import Connection

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.ollama_cloud_admission import (
    ensure_ollama_lease_in_transaction,
    ensure_ollama_run_in_transaction,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    ensure_access_target_in_transaction,
    ensure_active_binding_in_transaction,
    ensure_cloud_target_graph_in_transaction,
    ensure_current_binding_in_transaction,
    ensure_monitored_graph_in_transaction,
    record_credential_binding_verification_in_transaction,
)
from agentmonitor.contracts.collection_control_v1 import (
    CollectionRunAdmissionV1OrV2,
    CollectionRunAdmissionV2,
    OllamaCloudRequestLeaseV1,
)
from agentmonitor.contracts.registry_v1 import (
    ActiveCredentialBindingRefV1,
    ProviderAccessTargetV1,
)


def validate_cloud_target_fence(
    target: ProviderAccessTargetV1, fingerprint: str
) -> None:
    """Reject a disabled, relabelled or changed cloud target in M05's transaction."""
    if (
        target.provider_key != "ollama"
        or target.target_kind != "cloud_service"
        or target.authority_id != "ollama.com"
        or target.lifecycle != "active"
        or target.manifest_fingerprint != fingerprint
    ):
        raise ValueError("ollama_cloud_target_changed")


def ollama_capacity_repository(
    reference: DatabaseRefV1,
    lease: OllamaCloudRequestLeaseV1,
    run: CollectionRunAdmissionV1OrV2,
    payload_digest: str,
    *,
    verified_at: datetime | None = None,
) -> SqliteCapacityRepositoryV1:
    """Fence every write by the acquired M04 lease and current M02 credential."""

    def fences(connection: Connection, binding: ActiveCredentialBindingRefV1) -> None:
        if binding.account_id != lease.account_id:
            raise ValueError("ollama_cloud_target_mismatch")
        now = datetime.now(UTC)
        ensure_ollama_lease_in_transaction(connection, lease, now)
        ensure_ollama_run_in_transaction(connection, lease, run, payload_digest, now)
        if run.account_id is None or run.profile_id is None or run.resource_id is None:
            raise ValueError("ollama_cloud_target_mismatch")
        if (
            isinstance(run, CollectionRunAdmissionV2)
            and run.provider_target.target_kind == "cloud_service"
        ):
            target = ensure_access_target_in_transaction(
                connection, run.provider_target.target_id
            )
            validate_cloud_target_fence(target, run.manifest_fingerprint)
            if run.trigger == "reauth_verification":
                if verified_at is None or verified_at.utcoffset() is None:
                    raise ValueError("ollama_cloud_verification_time_invalid")
                ensure_current_binding_in_transaction(connection, binding)
            else:
                ensure_active_binding_in_transaction(connection, binding)
            ensure_cloud_target_graph_in_transaction(
                connection,
                account_id=run.account_id,
                profile_id=run.profile_id,
                resource_id=run.resource_id,
                access_target_id=run.provider_target.target_id,
                binding=binding,
            )
            if run.trigger == "reauth_verification":
                assert verified_at is not None
                record_credential_binding_verification_in_transaction(
                    connection,
                    binding=binding,
                    access_target_id=run.provider_target.target_id,
                    run_id=run.run_id,
                    admission_id=lease.admission_id,
                    source_id="ollama.cloud.balance.v1",
                    adapter_version=run.adapter_version,
                    manifest_fingerprint=run.manifest_fingerprint,
                    payload_digest=payload_digest,
                    verified_at=verified_at,
                )
            return
        ensure_active_binding_in_transaction(connection, binding)
        installation_id = (
            run.provider_target.target_id
            if isinstance(run, CollectionRunAdmissionV2)
            else run.installation_id
        )
        ensure_monitored_graph_in_transaction(
            connection,
            run.account_id,
            run.profile_id,
            run.resource_id,
            installation_id,
        )

    return SqliteCapacityRepositoryV1(
        reference,
        credential_fence=fences,
        credential_fence_required=True,
    )

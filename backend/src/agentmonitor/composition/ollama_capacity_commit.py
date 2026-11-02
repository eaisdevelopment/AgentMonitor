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
    ensure_active_binding_in_transaction,
    ensure_monitored_graph_in_transaction,
)
from agentmonitor.contracts.collection_control_v1 import (
    CollectionRunAdmissionV1,
    OllamaCloudRequestLeaseV1,
)
from agentmonitor.contracts.registry_v1 import ActiveCredentialBindingRefV1


def ollama_capacity_repository(
    reference: DatabaseRefV1,
    lease: OllamaCloudRequestLeaseV1,
    run: CollectionRunAdmissionV1,
    payload_digest: str,
) -> SqliteCapacityRepositoryV1:
    """Fence every write by the acquired M04 lease and current M02 credential."""

    def fences(connection: Connection, binding: ActiveCredentialBindingRefV1) -> None:
        if binding.account_id != lease.account_id:
            raise ValueError("ollama_cloud_target_mismatch")
        now = datetime.now(UTC)
        ensure_ollama_lease_in_transaction(connection, lease, now)
        ensure_ollama_run_in_transaction(connection, lease, run, payload_digest, now)
        ensure_active_binding_in_transaction(connection, binding)
        if run.account_id is None or run.profile_id is None or run.resource_id is None:
            raise ValueError("ollama_cloud_target_mismatch")
        ensure_monitored_graph_in_transaction(
            connection,
            run.account_id,
            run.profile_id,
            run.resource_id,
            run.installation_id,
        )

    return SqliteCapacityRepositoryV1(
        reference,
        credential_fence=fences,
        credential_fence_required=True,
    )

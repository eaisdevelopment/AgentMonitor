"""Bind M02's transaction fence to the M05 Ollama capacity writer."""

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    ensure_active_binding_in_transaction,
)


def ollama_capacity_repository(reference: DatabaseRefV1) -> SqliteCapacityRepositoryV1:
    """Return an Ollama writer with the M02 fence installed fail-closed."""
    return SqliteCapacityRepositoryV1(
        reference,
        credential_fence=ensure_active_binding_in_transaction,
        credential_fence_required=True,
    )

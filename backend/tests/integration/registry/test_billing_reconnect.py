"""Real M02 archive/restore/reconnect metadata; no credential or provider fiction."""

import secrets
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
    SqliteBillingConnectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCredentialBindingsV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.composition.ollama_credential_enrollment import (
    EnrollmentError,
    require_billing_credential_target,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import (
    ReconnectBillingConnectionCommandV1,
)
from agentmonitor.modules.registry.application.organizations import (
    RegistryCommandConflictV1,
)

from backend.tests.integration.registry.test_billing_credential_binding import (
    _account,
    _archive,
    _billing_connection,
    _database,
)


@pytest.mark.parametrize("provider", ["claude", "codex"])
def test_restored_billing_account_can_reconnect_without_old_authority(
    tmp_path: Path, provider: str
) -> None:
    """M7-REG-RECONNECT-001: preserved source epoch, explicit new setup required."""
    reference = _database(tmp_path)
    account = _account(reference, provider)
    _billing_connection(reference, account)
    registry = SqliteRegistryRepositoryV1(reference)
    billing = SqliteBillingConnectionRepositoryV1(reference)
    before = billing.get(account.account_id)
    assert before is not None
    original = before.connections[0]
    resources = registry.list_account_resources(account.account_id)
    bindings = SqliteCredentialBindingsV1(reference)
    prepared = bindings.transition(
        account.account_id, action="prepare", expected_record_version=0
    )
    archived = registry.edit_account(_archive(account))
    retired = bindings.read(account.account_id)
    assert retired.bindings[0].binding_id == prepared.bindings[0].binding_id
    assert retired.bindings[0].lifecycle == "cleanup_pending"
    archived_status = billing.get(account.account_id)
    assert archived_status is not None
    disconnected = archived_status.connections[0]
    command = ReconnectBillingConnectionCommandV1(
        account_id=account.account_id,
        resource_id=disconnected.resource_id,
        expected_account_version=archived.record_version,
        expected_connection_version=disconnected.record_version,
        expected_scope_generation=disconnected.scope_generation,
        principal_id=OpaqueIdV1("isolated-binding-owner"),
        command_id=OpaqueIdV1(secrets.token_urlsafe(24)),
        requested_at=datetime.now(UTC),
    )
    with pytest.raises(
        RegistryCommandConflictV1, match="billing_connection_unavailable"
    ):
        billing.reconnect(command)
    restored = registry.edit_account(
        replace(
            _archive(archived),
            action="restore",
            command_id=OpaqueIdV1(secrets.token_urlsafe(24)),
        )
    )
    with pytest.raises(EnrollmentError, match="billing_credential_target_unavailable"):
        require_billing_credential_target(
            reference, account.account_id, original.resource_id
        )
    with pytest.raises(RegistryCommandConflictV1, match="registry_version_conflict"):
        billing.reconnect(command)
    command = replace(command, expected_account_version=restored.record_version)
    for stale in (
        replace(command, expected_connection_version=disconnected.record_version + 1),
        replace(command, expected_scope_generation=disconnected.scope_generation + 1),
    ):
        with pytest.raises(
            RegistryCommandConflictV1, match="registry_version_conflict"
        ):
            billing.reconnect(stale)
    connected = billing.reconnect(command)
    assert connected.lifecycle == "pending"
    assert connected.monitoring_preference == "disabled"
    assert connected.resource_id == original.resource_id
    assert connected.scope_id == original.scope_id
    assert connected.scope_evidence == original.scope_evidence
    assert connected.scope_generation == original.scope_generation
    assert connected.record_version == disconnected.record_version + 1
    assert connected.registry_revision > disconnected.registry_revision
    assert bindings.read(account.account_id) == retired
    assert registry.list_account_resources(account.account_id) == tuple(
        replace(resource, registry_revision=connected.registry_revision)
        for resource in resources
    )
    assert registry.get_account(account.account_id) == replace(
        restored, registry_revision=connected.registry_revision
    )
    assert registry.list_monitoring_profiles(account.account_id) == ()
    current = require_billing_credential_target(
        reference, account.account_id, connected.resource_id
    )
    assert current.credential_status is not None
    assert current.credential_status.state == "cleanup_required"
    assert current.credential_status.active_generation is None
    assert current.credential_status.pending_generation is None
    assert billing.reconnect(command) == connected
    with pytest.raises(
        RegistryCommandConflictV1, match="registry_idempotency_conflict"
    ):
        billing.reconnect(replace(command, expected_scope_generation=2))
    with pytest.raises(
        RegistryCommandConflictV1, match="billing_connection_unavailable"
    ):
        billing.reconnect(
            replace(
                command,
                command_id=OpaqueIdV1(secrets.token_urlsafe(24)),
                expected_connection_version=connected.record_version,
            )
        )
    registry.edit_account(_archive(restored))
    with pytest.raises(RegistryCommandConflictV1, match="registry_replay_stale"):
        billing.reconnect(command)

"""Actual locked billing metadata revocation, without credentials or telemetry."""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
    SqliteBillingConnectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCredentialBindingsV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_lock import (
    account_credential_lock,
)
from agentmonitor.adapters.persistence.registry.sqlite.financial_pools import (
    SqliteFinancialPoolRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import CreateBillingConnectionCommandV1

from backend.tests.integration.registry.test_billing_credential_binding import (
    _account,
    _archive,
    _billing_connection,
    _database,
)
from backend.tests.integration.registry.test_financial_pools import _assign


def _pool_metadata(
    reference: DatabaseRefV1, identity: OpaqueIdV1
) -> tuple[object, ...]:
    # The disconnected configuration hides associations; inspect retained M02
    # metadata directly without asserting it still grants current authority.
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            return tuple(
                connection.exec_driver_sql(
                    "SELECT m.*,p.* FROM reg_financial_pool_membership m "
                    "JOIN reg_financial_pool p ON p.pool_id=m.pool_id "
                    "WHERE m.association_id=?",
                    (identity.value,),
                ).one()
            )


@pytest.mark.parametrize("provider", ("claude", "codex"))
@pytest.mark.parametrize("prepare", (False, True))
def test_disconnect_retires_pending_or_empty_metadata_and_keeps_lock(
    tmp_path: Path,
    provider: str,
    prepare: bool,
) -> None:
    reference = _database(tmp_path)
    account = _account(reference, provider)
    billing = SqliteBillingConnectionRepositoryV1(reference)
    billing.create(
        CreateBillingConnectionCommandV1(
            account_id=account.account_id,
            expected_account_version=account.record_version,
            scope_id="owner-declared-scope",
            principal_id=OpaqueIdV1("isolated-binding-owner"),
            command_id=OpaqueIdV1("create-billing"),
            requested_at=datetime.now(UTC),
        )
    )
    status = billing.get(account.account_id)
    assert status is not None
    original = status.connections[0]
    pools = SqliteFinancialPoolRepositoryV1(reference)
    associated = pools.assign(_assign(pools, account, original))
    assert associated.membership is not None
    association_id = associated.membership.association_id
    pool_before = _pool_metadata(reference, association_id)
    bindings = SqliteCredentialBindingsV1(reference)
    before = bindings.read(account.account_id)
    if prepare:
        before = bindings.transition(
            account.account_id,
            action="prepare",
            expected_record_version=0,
        )
    registry = SqliteRegistryRepositoryV1(reference)
    resources = registry.list_account_resources(account.account_id)
    with account_credential_lock(reference, account.account_id) as lease:
        retired = bindings.disconnect_billing_locked(
            account.account_id,
            original.resource_id,
            expected_account_version=account.record_version,
            expected_connection_version=original.record_version,
            expected_scope_generation=original.scope_generation,
            expected_record_version=before.record_version,
            lock_lease=lease,
        )
        current = billing.get(account.account_id)
        assert current is not None
        disconnected = current.connections[0]
        assert disconnected.lifecycle == "disconnected"
        assert disconnected.monitoring_preference == "disabled"
        assert disconnected.scope_generation == original.scope_generation
        assert disconnected.scope_id == original.scope_id
        assert disconnected.record_version == original.record_version + 1
        assert retired.record_version == before.record_version + int(prepare)
        assert retired.binding_generation == before.binding_generation + int(prepare)
        assert all(item.lifecycle == "cleanup_pending" for item in retired.bindings)
        assert all(
            item.reason_code == "owner_disconnected" for item in retired.bindings
        )
        assert tuple(item.binding_id for item in retired.bindings) == tuple(
            item.binding_id for item in before.bindings
        )
        assert (
            bindings.disconnect_billing_locked(
                account.account_id,
                original.resource_id,
                expected_account_version=account.record_version,
                expected_connection_version=disconnected.record_version,
                expected_scope_generation=original.scope_generation,
                expected_record_version=retired.record_version,
                lock_lease=lease,
            )
            == retired
        )
        assert billing.get(account.account_id) == current
        with pytest.raises(ValueError, match="credential_account_busy"):
            bindings.transition(
                account.account_id,
                action="prepare",
                expected_record_version=retired.record_version,
            )
        lease.inherited_lock(account.account_id)
    assert bindings.read(account.account_id) == retired
    assert registry.list_account_resources(account.account_id) == tuple(
        replace(item, registry_revision=disconnected.registry_revision)
        for item in resources
    )
    assert registry.list_monitoring_profiles(account.account_id) == ()
    configuration = pools.get_configuration(
        account.account_id, original.resource_id, "billing"
    )
    assert configuration is not None
    assert configuration.reason_code == "financial_pool_resource_unavailable"
    assert _pool_metadata(reference, association_id) == pool_before


@pytest.mark.parametrize(
    "field",
    (
        "expected_account_version",
        "expected_connection_version",
        "expected_scope_generation",
        "expected_record_version",
    ),
)
def test_disconnect_stale_versions_do_not_mutate(tmp_path: Path, field: str) -> None:
    reference = _database(tmp_path)
    account = _account(reference, "claude")
    _billing_connection(reference, account)
    bindings = SqliteCredentialBindingsV1(reference)
    before = bindings.transition(
        account.account_id, action="prepare", expected_record_version=0
    )
    billing = SqliteBillingConnectionRepositoryV1(reference)
    status = billing.get(account.account_id)
    assert status is not None
    selected = status.connections[0]
    versions = dict(
        expected_account_version=account.record_version,
        expected_connection_version=selected.record_version,
        expected_scope_generation=selected.scope_generation,
        expected_record_version=before.record_version,
    )
    versions[field] += 1
    with account_credential_lock(reference, account.account_id) as lease:
        with pytest.raises(ValueError, match="billing_disconnect_version_conflict"):
            bindings.disconnect_billing_locked(
                account.account_id, selected.resource_id, lock_lease=lease, **versions
            )
    assert bindings.read(account.account_id) == before
    assert billing.get(account.account_id) == status


@pytest.mark.parametrize(
    "invalid",
    (
        "wrong_root",
        "expired",
        "wrong_account",
        "wrong_resource",
        "archived",
        "provider",
    ),
)
def test_disconnect_rejects_invalid_authority(tmp_path: Path, invalid: str) -> None:
    reference = _database(tmp_path)
    account = _account(reference, "ollama" if invalid == "provider" else "codex")
    billing = SqliteBillingConnectionRepositoryV1(reference)
    if invalid != "provider":
        _billing_connection(reference, account)
    if invalid == "archived":
        account = SqliteRegistryRepositoryV1(reference).edit_account(_archive(account))
    status = billing.get(account.account_id)
    assert status is not None
    resource = (
        status.connections[0].resource_id
        if status.connections
        else OpaqueIdV1("no-billing-resource")
    )
    version = status.connections[0].record_version if status.connections else 1
    bindings = SqliteCredentialBindingsV1(reference)
    before = bindings.read(account.account_id)
    lock_reference = reference
    lock_account = account.account_id
    if invalid == "wrong_root":
        other = tmp_path / "other"
        other.mkdir(mode=0o700)
        lock_reference = _database(other)
    if invalid == "wrong_account":
        lock_account = OpaqueIdV1("another-account")
    with account_credential_lock(lock_reference, lock_account) as lease:
        if invalid == "expired":
            lease.invalidate()
        with pytest.raises(ValueError):
            bindings.disconnect_billing_locked(
                account.account_id,
                OpaqueIdV1("another-resource")
                if invalid == "wrong_resource"
                else resource,
                expected_account_version=account.record_version,
                expected_connection_version=version,
                expected_scope_generation=1,
                expected_record_version=before.record_version,
                lock_lease=lease,
            )
    assert bindings.read(account.account_id) == before
    assert billing.get(account.account_id) == status

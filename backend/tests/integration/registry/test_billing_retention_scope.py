"""Retention scope metadata is independent of a provider credential or call."""

import secrets
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.registry.sqlite import billing_connections
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import ChangeBillingScopeCommandV1
from agentmonitor.modules.registry.application.accounts import EditAccountCommandV1

from backend.tests.integration.registry.test_billing_connections import (
    _account,
    _command,
    _counts,
    _database,
)


@pytest.mark.parametrize("provider", ["claude", "codex"])
def test_known_scope_remains_readable_without_active_credential(
    tmp_path: Path, provider: str
) -> None:
    reference = _database(tmp_path)
    account = _account(reference, provider)
    billing = billing_connections.SqliteBillingConnectionRepositoryV1(reference)
    created = billing.create(_command(account))
    before = _counts(reference)
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql("BEGIN")
            assert (
                billing_connections.resolve_billing_access_in_transaction(
                    connection, account.account_id, created.resource_id, "verification"
                )
                is None
            )
            assert (
                billing_connections.read_billing_retention_scope_in_transaction(
                    connection, account.account_id, created.resource_id
                )
                == created
            )
            assert created.monitoring_preference == "disabled"
            assert created.scope_evidence == "owner_asserted"
            assert connection.in_transaction()
            for table in ("collection_run", "capacity_budget_report"):
                assert (
                    connection.exec_driver_sql(
                        f"SELECT count(*) FROM {table}"
                    ).scalar_one()
                    == 0
                )
            connection.rollback()
    assert _counts(reference) == before


def test_retention_scope_tracks_scope_edit_and_refuses_retired_account(
    tmp_path: Path,
) -> None:
    reference = _database(tmp_path)
    account = _account(reference)
    billing = billing_connections.SqliteBillingConnectionRepositoryV1(reference)
    created = billing.create(_command(account))
    command = ChangeBillingScopeCommandV1(
        account.account_id,
        created.resource_id,
        account.record_version,
        created.record_version,
        created.scope_generation,
        "changed-owner-scope-" + secrets.token_hex(8),
        OpaqueIdV1("isolated-registry-owner"),
        OpaqueIdV1(secrets.token_urlsafe(24)),
        datetime.now(UTC),
    )
    changed = billing.change_scope(command)
    assert changed.scope_generation == created.scope_generation + 1
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            with pytest.raises(ValueError, match="billing_transaction_required"):
                billing_connections.read_billing_retention_scope_in_transaction(
                    connection, account.account_id, created.resource_id
                )
            connection.exec_driver_sql("BEGIN")
            assert (
                billing_connections.read_billing_retention_scope_in_transaction(
                    connection, account.account_id, created.resource_id
                )
                == changed
            )
            assert (
                billing_connections.read_billing_retention_scope_in_transaction(
                    connection, account.account_id, OpaqueIdV1("absent-resource")
                )
                is None
            )
            connection.rollback()
    archive = EditAccountCommandV1(
        account_id=account.account_id,
        expected_version=account.record_version,
        principal_id=OpaqueIdV1("isolated-registry-owner"),
        command_id=OpaqueIdV1(secrets.token_urlsafe(24)),
        action="archive",
        requested_at=datetime.now(UTC),
    )
    registry = SqliteRegistryRepositoryV1(reference)
    archived = registry.edit_account(archive)
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql("BEGIN")
            assert (
                billing_connections.read_billing_retention_scope_in_transaction(
                    connection, account.account_id, created.resource_id
                )
                is None
            )
            connection.rollback()
    registry.edit_account(
        replace(
            archive,
            expected_version=archived.record_version,
            action="restore",
            command_id=OpaqueIdV1(secrets.token_urlsafe(24)),
            requested_at=datetime.now(UTC),
        )
    )
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql("BEGIN")
            # Restore does not reconnect the explicitly disconnected billing resource.
            assert (
                billing_connections.read_billing_retention_scope_in_transaction(
                    connection, account.account_id, created.resource_id
                )
                is None
            )
            connection.rollback()

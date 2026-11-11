"""M7 API setup intent remains inert administrator metadata in real SQLite."""

import hashlib
import json
import secrets
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.claude.manifest import build_claude_manifest
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.provider_system.application.gateway import (
    get_manifest_fingerprint_v1,
)
from agentmonitor.modules.registry.application.accounts import (
    CreatePendingAccountCommandV1,
    RegisterAccountV1,
)
from agentmonitor.modules.registry.application.organizations import (
    RegistryCommandConflictV1,
)
from sqlalchemy.exc import IntegrityError


def _command() -> CreatePendingAccountCommandV1:
    return CreatePendingAccountCommandV1(
        command_id=OpaqueIdV1(secrets.token_urlsafe(24)),
        principal_id=OpaqueIdV1("isolated-registry-owner"),
        provider_key="claude",
        manifest_reference=get_manifest_fingerprint_v1(build_claude_manifest()),
        friendly_name="Billing setup " + secrets.token_urlsafe(8),
        organization_id=None,
        requested_at=datetime.now(UTC),
    )


def _database(tmp_path: Path) -> DatabaseRefV1:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    return reference


def test_existing_account_creation_has_nullable_intent_storage(tmp_path: Path) -> None:
    """M7-REG-DB-001: legacy creation leaves the new persisted intent null."""
    reference = _database(tmp_path)
    created = RegisterAccountV1(SqliteRegistryRepositoryV1(reference)).pending(
        _command()
    )
    assert created.initial_connection_purpose is None
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            columns = {
                row[1]: row
                for row in connection.exec_driver_sql("PRAGMA table_info(reg_account)")
            }
            assert "initial_connection_purpose" in columns, (
                "Registered accounts need nullable persisted API setup intent"
            )
            column = columns["initial_connection_purpose"]
            assert column[3] == 0 and column[4] is None
            assert (
                connection.exec_driver_sql(
                    "SELECT initial_connection_purpose FROM reg_account "
                    "WHERE account_id=?",
                    (created.account_id.value,),
                ).scalar_one()
                is None
            )


def test_api_intent_survives_reopen_without_identity_or_monitoring(
    tmp_path: Path,
) -> None:
    """M7-REG-DB-002: intent persists, replays and rejects conflicting retries."""
    reference = _database(tmp_path)
    command = replace(_command(), initial_connection_purpose="api")
    register = RegisterAccountV1(SqliteRegistryRepositoryV1(reference))
    created = register.pending(command)
    assert created.initial_connection_purpose == "api"
    assert created.lifecycle == "pending"
    assert created.identity_state == "unresolved"
    assert created.monitoring_preference == "disabled"
    assert not created.is_effective_monitoring_enabled
    reopened = SqliteRegistryRepositoryV1(reference)
    assert reopened.get_account(created.account_id) == created
    assert reopened.list_accounts() == (created,)
    assert RegisterAccountV1(reopened).pending(command) == created
    with pytest.raises(
        RegistryCommandConflictV1, match="registry_idempotency_conflict"
    ):
        RegisterAccountV1(reopened).pending(
            replace(command, initial_connection_purpose=None)
        )
    assert reopened.get_account(created.account_id) == created
    assert reopened.list_monitoring_profiles(created.account_id) == ()
    assert reopened.list_account_resources(created.account_id) == ()
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            with pytest.raises(IntegrityError):
                connection.exec_driver_sql(
                    "UPDATE reg_account SET initial_connection_purpose=? "
                    "WHERE account_id=?",
                    ("unsupported-purpose", created.account_id.value),
                )
            connection.rollback()
            assert (
                connection.exec_driver_sql("PRAGMA integrity_check").scalar_one()
                == "ok"
            )
            assert (
                connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
            )
    assert reopened.get_account(created.account_id) == created


def test_null_intent_keeps_existing_idempotency_fingerprint(tmp_path: Path) -> None:
    """M7-REG-DB-003: the historical creation grammar remains replay compatible."""
    reference = _database(tmp_path)
    command = _command()
    register = RegisterAccountV1(SqliteRegistryRepositoryV1(reference))
    created = register.pending(command)
    # The pre-M7 command grammar omits purpose entirely, including for null.
    historical_shape = {
        "provider_key": command.provider_key,
        "manifest_reference": command.manifest_reference,
        "friendly_name": command.friendly_name,
        "organization_id": None,
        "operation": "register_pending_account",
    }
    expected = hashlib.sha256(
        json.dumps(
            historical_shape, ensure_ascii=True, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
    ).hexdigest()
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            fingerprint = connection.exec_driver_sql(
                "SELECT request_fingerprint FROM reg_command_receipt "
                "WHERE outcome_subject_id=? "
                "AND operation_key='register_pending_account'",
                (created.account_id.value,),
            ).scalar_one()
    assert fingerprint == expected
    assert (
        register.pending(replace(command, initial_connection_purpose=None)) == created
    )
    with pytest.raises(
        RegistryCommandConflictV1, match="registry_idempotency_conflict"
    ):
        register.pending(replace(command, initial_connection_purpose="api"))
    assert SqliteRegistryRepositoryV1(reference).list_accounts() == (created,)


@pytest.mark.parametrize("purpose", ["", "subscription", True, []])
def test_invalid_initial_connection_purpose_is_rejected(purpose: object) -> None:
    """Invalid caller intent fails before registry I/O."""
    command = CreatePendingAccountCommandV1(
        command_id=OpaqueIdV1("pure-command"),
        principal_id=OpaqueIdV1("pure-owner"),
        provider_key="claude",
        manifest_reference="0" * 32,
        friendly_name="Pure policy input",
        organization_id=None,
        requested_at=datetime(2026, 11, 11, tzinfo=UTC),
    )
    with pytest.raises(ValueError, match="registry_pending_account_command_invalid"):
        # Deliberately violate the annotation to verify runtime rejection.
        replace(command, initial_connection_purpose=cast(Literal["api"], purpose))

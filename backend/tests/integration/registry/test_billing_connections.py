"""Billing metadata uses real isolated SQLite and production account commands."""

import secrets
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier

import pytest
from sqlalchemy.exc import IntegrityError

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
    SqliteBillingConnectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.claude.manifest import build_claude_manifest
from agentmonitor.adapters.providers.codex.manifest import build_codex_manifest
from agentmonitor.adapters.providers.ollama.manifest import build_ollama_manifest
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import (
    BillingConnectionViewV1,
    CreateBillingConnectionCommandV1,
)
from agentmonitor.contracts.registry_v1 import AccountViewV1
from agentmonitor.modules.provider_system.application.gateway import (
    get_manifest_fingerprint_v1,
)
from agentmonitor.modules.registry.application.accounts import (
    CreatePendingAccountCommandV1,
    EditAccountCommandV1,
    RegisterAccountV1,
)
from agentmonitor.modules.registry.application.organizations import (
    RegistryCommandConflictV1,
)
from agentmonitor.modules.registry.domain.billing_connection import (
    billing_connection_eligibility,
)


def _database(tmp_path: Path) -> DatabaseRefV1:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    return reference


def test_billing_connection_schema_exists(tmp_path: Path) -> None:
    """M7-REG-BILL-001: additive metadata storage is physically present."""
    reference = _database(tmp_path)
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            columns = {
                row[1]
                for row in connection.exec_driver_sql(
                    "PRAGMA table_info(reg_billing_connection)"
                )
            }
            assert "scope_generation" in columns, "billing metadata table is missing"


def _account(reference: DatabaseRefV1, provider: str = "claude") -> AccountViewV1:
    manifest = {
        "claude": build_claude_manifest,
        "codex": build_codex_manifest,
        "ollama": build_ollama_manifest,
    }[provider]()
    return RegisterAccountV1(SqliteRegistryRepositoryV1(reference)).pending(
        CreatePendingAccountCommandV1(
            command_id=OpaqueIdV1(secrets.token_urlsafe(24)),
            principal_id=OpaqueIdV1("isolated-registry-owner"),
            provider_key=provider,
            manifest_reference=get_manifest_fingerprint_v1(manifest),
            friendly_name="Billing metadata " + secrets.token_urlsafe(8),
            organization_id=None,
            requested_at=datetime.now(UTC),
        )
    )


def _command(account: AccountViewV1) -> CreateBillingConnectionCommandV1:
    return CreateBillingConnectionCommandV1(
        account_id=account.account_id,
        expected_account_version=account.record_version,
        principal_id=OpaqueIdV1("isolated-registry-owner"),
        command_id=OpaqueIdV1(secrets.token_urlsafe(24)),
        scope_id="owner-scope-" + secrets.token_hex(8),
        requested_at=datetime.now(UTC),
    )


def _counts(reference: DatabaseRefV1) -> tuple[int, ...]:
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            return tuple(
                int(connection.exec_driver_sql(query).scalar_one())
                for query in (
                    "SELECT count(*) FROM reg_account_resource",
                    "SELECT count(*) FROM reg_billing_connection",
                    "SELECT count(*) FROM reg_registry_change",
                    "SELECT count(*) FROM reg_event_outbox",
                    "SELECT count(*) FROM reg_command_receipt",
                    "SELECT registry_revision FROM reg_registry_state",
                )
            )


@pytest.mark.parametrize("provider", ["claude", "codex"])
@pytest.mark.parametrize("resolved", [False, True])
def test_create_reopen_replay_preserves_subscription(
    tmp_path: Path, provider: str, resolved: bool
) -> None:
    """M7-REG-BILL-003: durable pending connection with independent identity."""
    reference = _database(tmp_path)
    account = _account(reference, provider)
    repository = SqliteBillingConnectionRepositoryV1(reference)
    assert repository.get(OpaqueIdV1("absent-account")) is None
    initial = repository.get(account.account_id)
    assert initial is not None and initial.can_add_connection
    assert initial.reason_code == "billing_connection_available"
    command = _command(account)
    if not resolved:
        command = replace(command, scope_id=None)
    before = _counts(reference)
    created = repository.create(command)
    assert created.provider_key == provider
    assert created.account_id == account.account_id
    assert created.scope_id == command.scope_id
    assert created.scope_evidence == ("owner_asserted" if resolved else "unresolved")
    assert created.scope_generation == created.record_version == 1
    assert created.lifecycle == "pending"
    assert created.monitoring_preference == "disabled"
    assert created.created_at == created.updated_at == command.requested_at
    assert created.registry_revision == before[-1] + 1
    after = _counts(reference)
    assert after == tuple(n + 1 for n in before)
    reopened = SqliteBillingConnectionRepositoryV1(reference)
    status = reopened.get(account.account_id)
    assert status is not None and status.connections == (created,)
    assert not status.can_add_connection
    assert status.reason_code == "billing_connection_exists"
    assert reopened.create(command) == created
    assert _counts(reference) == after
    registry = SqliteRegistryRepositoryV1(reference)
    unchanged = registry.get_account(account.account_id)
    assert unchanged is not None
    assert replace(unchanged, registry_revision=account.registry_revision) == account
    assert registry.list_monitoring_profiles(account.account_id) == ()
    resources = registry.list_account_resources(account.account_id)
    assert len(resources) == 1
    assert resources[0].resource_id == created.resource_id
    assert resources[0].kind == "api_organization"
    assert resources[0].lifecycle == "active"
    assert resources[0].linked_profile_ids == ()
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            events = (
                connection.exec_driver_sql(
                    "SELECT payload_json FROM reg_event_outbox WHERE subject_id=?",
                    (created.resource_id.value,),
                )
                .scalars()
                .all()
            )
            assert len(events) == 1
            assert '"subject_type":"resource"' in events[0]
            assert "scope" not in events[0]
            if command.scope_id is not None:
                assert command.scope_id not in events[0]
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
            assert (
                connection.exec_driver_sql("PRAGMA integrity_check").scalar_one()
                == "ok"
            )


def test_conflicts_do_not_write_and_account_version_is_checked(tmp_path: Path) -> None:
    """M7-REG-BILL-004: optimistic concurrency and idempotency are atomic."""
    reference = _database(tmp_path)
    account = _account(reference)
    repository = SqliteBillingConnectionRepositoryV1(reference)
    command = _command(account)
    before = _counts(reference)
    for invalid, reason in (
        (
            replace(command, account_id=OpaqueIdV1("missing-account")),
            "registry_subject_not_found",
        ),
        (replace(command, expected_account_version=2), "registry_version_conflict"),
    ):
        with pytest.raises(RegistryCommandConflictV1, match=reason):
            repository.create(invalid)
        assert _counts(reference) == before
    created = repository.create(command)
    after = _counts(reference)
    for conflicting, reason in (
        (replace(command, scope_id="different-scope"), "registry_idempotency_conflict"),
        (
            replace(command, command_id=OpaqueIdV1(secrets.token_urlsafe(24))),
            "billing_connection_exists",
        ),
    ):
        with pytest.raises(RegistryCommandConflictV1, match=reason):
            repository.create(conflicting)
        assert _counts(reference) == after
    assert repository.create(command) == created


def test_archived_and_ollama_accounts_cannot_create(tmp_path: Path) -> None:
    """M7-REG-BILL-005: no new Ollama graph or archived account enrollment."""
    reference = _database(tmp_path)
    registry = SqliteRegistryRepositoryV1(reference)
    account = _account(reference)
    archived = registry.edit_account(
        EditAccountCommandV1(
            account_id=account.account_id,
            expected_version=account.record_version,
            principal_id=OpaqueIdV1("isolated-registry-owner"),
            command_id=OpaqueIdV1(secrets.token_urlsafe(24)),
            action="archive",
            requested_at=datetime.now(UTC),
        )
    )
    ollama = _account(reference, "ollama")
    repository = SqliteBillingConnectionRepositoryV1(reference)
    before = _counts(reference)
    for current, reason in (
        (archived, "account_unavailable"),
        (ollama, "existing_cloud_connection_required"),
    ):
        status = repository.get(current.account_id)
        assert status is not None and not status.can_add_connection
        assert status.reason_code == reason
        with pytest.raises(RegistryCommandConflictV1, match=reason):
            repository.create(_command(current))
        assert _counts(reference) == before


@pytest.mark.parametrize("same_command", [False, True])
def test_concurrent_creates_have_one_connection(
    tmp_path: Path, same_command: bool
) -> None:
    """M7-REG-BILL-006: separate real connections serialize the singleton."""
    reference = _database(tmp_path)
    account = _account(reference)
    first = _command(account)
    second = first if same_command else _command(account)
    before = _counts(reference)
    barrier = Barrier(2)

    def create(
        command: CreateBillingConnectionCommandV1,
    ) -> BillingConnectionViewV1 | str:
        barrier.wait(timeout=10)
        try:
            return SqliteBillingConnectionRepositoryV1(reference).create(command)
        except RegistryCommandConflictV1 as error:
            return str(error)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(create, command) for command in (first, second)]
        outcomes = [future.result(timeout=15) for future in futures]
    successes = [
        result for result in outcomes if isinstance(result, BillingConnectionViewV1)
    ]
    assert len(successes) == (2 if same_command else 1)
    assert len({result.resource_id for result in successes}) == 1
    if not same_command:
        assert "billing_connection_exists" in outcomes
    assert _counts(reference) == tuple(n + 1 for n in before)


@pytest.mark.parametrize(
    ("provider", "lifecycle", "exists", "expected"),
    [
        ("claude", "active", False, (True, "billing_connection_available")),
        ("codex", "pending", False, (True, "billing_connection_available")),
        ("claude", "disabled", False, (False, "account_unavailable")),
        ("other", "pending", False, (False, "provider_unsupported")),
        ("ollama", "active", False, (False, "existing_cloud_connection_required")),
        ("codex", "active", True, (False, "billing_connection_exists")),
    ],
)
def test_pure_eligibility_policy(
    provider: str, lifecycle: str, exists: bool, expected: tuple[bool, str]
) -> None:
    """No-I/O constructed policy inputs; no invented persisted identity."""
    assert billing_connection_eligibility(provider, lifecycle, exists) == expected


def test_database_enforces_binding_and_status_constraints(tmp_path: Path) -> None:
    """M7-REG-BILL-007: physical FK, state, and version checks cannot be bypassed."""
    reference = _database(tmp_path)
    account = _account(reference)
    other = _account(reference)
    created = SqliteBillingConnectionRepositoryV1(reference).create(_command(account))
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            for query, parameters in (
                ("UPDATE reg_billing_connection SET scope_generation=0", ()),
                ("UPDATE reg_billing_connection SET record_version=0", ()),
                (
                    "UPDATE reg_billing_connection SET monitoring_preference='enabled'",
                    (),
                ),
                ("UPDATE reg_billing_connection SET scope_evidence='unresolved'", ()),
                (
                    "UPDATE reg_billing_connection SET account_id=?",
                    (other.account_id.value,),
                ),
            ):
                with pytest.raises(IntegrityError):
                    connection.exec_driver_sql(query, parameters)
                connection.rollback()
    status = SqliteBillingConnectionRepositoryV1(reference).get(account.account_id)
    assert status is not None and status.connections == (created,)

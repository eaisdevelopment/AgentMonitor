"""M7-REG-POOL: real isolated owner metadata, without provider/credential data."""

import secrets
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier
from typing import Literal

import pytest
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
from agentmonitor.adapters.persistence.registry.sqlite.financial_pools import (
    SqliteFinancialPoolRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.claude.manifest import build_claude_manifest
from agentmonitor.adapters.providers.codex.manifest import build_codex_manifest
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import (
    AssignFinancialPoolCommandV1,
    BillingConnectionViewV1,
    ChangeBillingScopeCommandV1,
    CreateBillingConnectionCommandV1,
    EditFinancialPoolCommandV1,
    FinancialPoolConfigurationV1,
)
from agentmonitor.contracts.registry_v1 import AccountViewV1, OrganizationViewV1
from agentmonitor.modules.provider_system.application.gateway import (
    get_manifest_fingerprint_v1,
)
from agentmonitor.modules.registry.application.accounts import (
    CreatePendingAccountCommandV1,
    EditAccountCommandV1,
    RegisterAccountV1,
)
from agentmonitor.modules.registry.application.organizations import (
    CreateOrganizationCommandV1,
    EditOrganizationCommandV1,
    RegistryCommandConflictV1,
)
from sqlalchemy.exc import IntegrityError

OWNER = OpaqueIdV1("isolated-pool-owner")


def _id() -> OpaqueIdV1:
    return OpaqueIdV1(secrets.token_urlsafe(24))


def _repository(reference: DatabaseRefV1) -> SqliteFinancialPoolRepositoryV1:
    return SqliteFinancialPoolRepositoryV1(reference)


def _source(
    reference: DatabaseRefV1,
    *,
    provider: Literal["claude", "codex"] = "claude",
    scope: str | None = "owner-scope",
) -> tuple[AccountViewV1, BillingConnectionViewV1]:
    manifest = (
        build_claude_manifest if provider == "claude" else build_codex_manifest
    )()
    registry = SqliteRegistryRepositoryV1(reference)
    account = RegisterAccountV1(registry).pending(
        CreatePendingAccountCommandV1(
            command_id=_id(),
            principal_id=OWNER,
            provider_key=provider,
            manifest_reference=get_manifest_fingerprint_v1(manifest),
            friendly_name="Pool metadata " + secrets.token_urlsafe(8),
            organization_id=None,
            requested_at=datetime.now(UTC),
        )
    )
    billing = SqliteBillingConnectionRepositoryV1(reference).create(
        CreateBillingConnectionCommandV1(
            account.account_id,
            account.record_version,
            OWNER,
            _id(),
            scope,
            datetime.now(UTC),
        )
    )
    return account, billing


def _assign(
    repository: SqliteFinancialPoolRepositoryV1,
    account: AccountViewV1,
    billing: BillingConnectionViewV1,
    *,
    action: Literal["create", "join", "unlink"] = "create",
    pool_id: OpaqueIdV1 | None = None,
    org: OpaqueIdV1 | None = None,
) -> AssignFinancialPoolCommandV1:
    config = repository.get_configuration(
        account.account_id, billing.resource_id, "billing"
    )
    assert config is not None and config.scope is not None
    return AssignFinancialPoolCommandV1(
        config.scope,
        config.registry_revision,
        action,
        pool_id,
        org,
        OWNER,
        _id(),
        datetime.now(UTC),
    )


def _counts(reference: DatabaseRefV1) -> tuple[int, ...]:
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            return tuple(
                connection.exec_driver_sql("SELECT count(*) FROM " + table).scalar_one()
                for table in (
                    "reg_financial_pool",
                    "reg_financial_pool_membership",
                    "reg_registry_change",
                    "reg_event_outbox",
                    "reg_command_receipt",
                )
            )


def _organization(reference: DatabaseRefV1) -> OrganizationViewV1:
    return SqliteRegistryRepositoryV1(reference).create_organization(
        CreateOrganizationCommandV1(
            _id(),
            OWNER,
            "Pool group " + secrets.token_urlsafe(8),
            None,
            datetime.now(UTC),
        )
    )


def _database(tmp_path: Path) -> DatabaseRefV1:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    return reference


def test_financial_pool_schema_is_present(tmp_path: Path) -> None:
    reference = _database(tmp_path)
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            tables = set(
                connection.exec_driver_sql(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).scalars()
            )
            assert {"reg_financial_pool", "reg_financial_pool_membership"} <= tables
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []


def test_create_reopen_replay_and_snapshot_preserve_source_metadata(
    tmp_path: Path,
) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    repository = _repository(reference)
    migrate_to_head(reference)
    account, billing = _source(reference)
    registry = SqliteRegistryRepositoryV1(reference)
    before_account = registry.get_account(account.account_id)
    assert before_account is not None
    command = _assign(repository, account, billing)
    before = _counts(reference)
    result = repository.assign(command)
    assert result.pool is not None and result.membership is not None
    assert result.pool.display_name == account.friendly_name + " · billing"
    assert result.membership.scope == command.scope
    assert result.membership.association_evidence == "owner_asserted"
    assert result.registry_revision == command.expected_registry_revision + 1
    assert _counts(reference) == tuple(value + 1 for value in before)
    reopened = _repository(reference)
    assert reopened.assign(command) == result
    assert _counts(reference) == tuple(value + 1 for value in before)
    snapshot = reopened(
        (billing.resource_id,),
        expected_registry_revision=result.registry_revision,
        as_of=datetime.now(UTC),
    )
    assert snapshot.availability.state == "available"
    assert snapshot.pools == (result.pool,)
    assert snapshot.memberships == (result.membership,)
    current = registry.get_account(account.account_id)
    assert current is not None
    assert (
        replace(current, registry_revision=before_account.registry_revision)
        == before_account
    )
    billing_status = SqliteBillingConnectionRepositoryV1(reference).get(
        account.account_id
    )
    assert billing_status is not None and billing_status.connections == (billing,)
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            payload = connection.exec_driver_sql(
                "SELECT payload_json FROM reg_event_outbox ORDER BY "
                "producer_sequence DESC LIMIT 1"
            ).scalar_one()
            assert command.scope.provider_scope_id not in payload
            assert "binding" not in payload and "display_name" not in payload
            event = connection.exec_driver_sql(
                "SELECT subject_type,subject_id,aggregate_version "
                "FROM reg_event_outbox "
                "ORDER BY producer_sequence DESC LIMIT 1"
            ).one()
            receipt = connection.exec_driver_sql(
                "SELECT outcome_subject_type,outcome_subject_id,outcome_record_version "
                "FROM reg_command_receipt WHERE operation_key='assign_financial_pool'"
            ).one()
            expected = (
                "financial_pool_membership",
                result.membership.association_id.value,
                result.membership.record_version,
            )
            assert tuple(event) == expected
            assert tuple(receipt) == expected


def test_join_unlink_retains_epochs_and_stale_replay_cannot_restore_them(
    tmp_path: Path,
) -> None:
    reference = _database(tmp_path)
    repository = _repository(reference)
    first, first_billing = _source(reference)
    second, second_billing = _source(reference)
    created = repository.assign(_assign(repository, first, first_billing))
    assert created.pool is not None
    join = _assign(
        repository, second, second_billing, action="join", pool_id=created.pool.pool_id
    )
    joined = repository.assign(join)
    assert joined.membership is not None
    assert joined.pool == created.pool
    assert repository.assign(join) == joined
    unlink = _assign(repository, second, second_billing, action="unlink")
    unlinked = repository.assign(unlink)
    assert unlinked.pool is None and unlinked.membership is None
    assert repository.assign(unlink) == unlinked
    with pytest.raises(RegistryCommandConflictV1, match="registry_replay_stale"):
        repository.assign(join)
    snapshot = repository(
        (first_billing.resource_id, second_billing.resource_id),
        expected_registry_revision=unlinked.registry_revision,
        as_of=datetime.now(UTC),
    )
    assert snapshot.memberships == (created.membership,)
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            old = connection.exec_driver_sql(
                "SELECT valid_until,record_version FROM "
                "reg_financial_pool_membership WHERE association_id=?",
                (joined.membership.association_id.value,),
            ).one()
            assert old[0] is not None and old[1] == 2
            event = connection.exec_driver_sql(
                "SELECT subject_type,subject_id,aggregate_version "
                "FROM reg_event_outbox "
                "ORDER BY producer_sequence DESC LIMIT 1"
            ).one()
            assert tuple(event) == (
                "financial_pool_membership",
                joined.membership.association_id.value,
                2,
            )
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []


def test_conflicting_scope_provider_and_stale_revision_are_atomic(
    tmp_path: Path,
) -> None:
    reference = _database(tmp_path)
    repository = _repository(reference)
    first, billing = _source(reference)
    different, different_billing = _source(reference, scope="another-owner-scope")
    foreign, foreign_billing = _source(reference, provider="codex")
    created = repository.assign(_assign(repository, first, billing))
    assert created.pool is not None
    for account, resource in (
        (different, different_billing),
        (foreign, foreign_billing),
    ):
        command = _assign(
            repository, account, resource, action="join", pool_id=created.pool.pool_id
        )
        before = _counts(reference)
        with pytest.raises(
            RegistryCommandConflictV1, match="financial_pool_incompatible"
        ):
            repository.assign(command)
        assert _counts(reference) == before
    command = _assign(repository, different, different_billing)
    with pytest.raises(RegistryCommandConflictV1, match="registry_revision_conflict"):
        repository.assign(
            replace(
                command,
                expected_registry_revision=command.expected_registry_revision - 1,
            )
        )
    with pytest.raises(RegistryCommandConflictV1, match="financial_pool_scope_changed"):
        repository.assign(
            replace(command, scope=replace(command.scope, scope_generation=2))
        )


def test_attribution_edit_and_pool_pagination_are_revision_fenced(
    tmp_path: Path,
) -> None:
    reference = _database(tmp_path)
    repository = _repository(reference)
    organization = _organization(reference)
    sources = [_source(reference) for _ in range(3)]
    pools = []
    for source in sources:
        created = repository.assign(_assign(repository, *source))
        assert created.pool is not None
        pools.append(created.pool)
    first = repository.list_pools("claude", limit=2)
    second = repository.list_pools(
        "claude",
        limit=2,
        after=first.next_pool_id,
        expected_registry_revision=first.registry_revision,
    )
    assert first.next_pool_id is not None and second.next_pool_id is None
    assert [p.pool_id.value for p in first.pools + second.pools] == sorted(
        p.pool_id.value for p in pools
    )
    edit = EditFinancialPoolCommandV1(
        pools[0].pool_id,
        pools[0].record_version,
        first.registry_revision,
        organization.organization_id,
        OWNER,
        _id(),
        datetime.now(UTC),
    )
    result = repository.edit(edit)
    assert result.primary_organization_id == organization.organization_id
    assert result.record_version == pools[0].record_version + 1
    assert repository.edit(edit) == result
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            event = connection.exec_driver_sql(
                "SELECT subject_type,subject_id,aggregate_version "
                "FROM reg_event_outbox "
                "ORDER BY producer_sequence DESC LIMIT 1"
            ).one()
            receipt = connection.exec_driver_sql(
                "SELECT outcome_subject_type,outcome_subject_id,outcome_record_version "
                "FROM reg_command_receipt WHERE operation_key='edit_financial_pool'"
            ).one()
            expected = ("financial_pool", result.pool_id.value, result.record_version)
            assert tuple(event) == expected
            assert tuple(receipt) == expected
    with pytest.raises(RegistryCommandConflictV1, match="registry_revision_conflict"):
        repository.list_pools(
            "claude",
            limit=2,
            after=first.next_pool_id,
            expected_registry_revision=first.registry_revision,
        )
    with pytest.raises(
        RegistryCommandConflictV1, match="registry_idempotency_conflict"
    ):
        repository.edit(replace(edit, primary_organization_id=None))


def test_unknown_binding_archive_and_invalid_organization_are_not_authority(
    tmp_path: Path,
) -> None:
    reference = _database(tmp_path)
    repository = _repository(reference)
    unresolved, unresolved_billing = _source(reference, scope=None)
    config = repository.get_configuration(
        unresolved.account_id, unresolved_billing.resource_id, "billing"
    )
    assert config is not None and config.scope is None and config.membership is None
    account, billing = _source(reference)
    command = _assign(repository, account, billing, org=_id())
    before = _counts(reference)
    with pytest.raises(
        RegistryCommandConflictV1, match="financial_pool_organization_unavailable"
    ):
        repository.assign(command)
    assert _counts(reference) == before
    organization = _organization(reference)
    SqliteRegistryRepositoryV1(reference).edit_organization(
        EditOrganizationCommandV1(
            organization.organization_id,
            organization.record_version,
            OWNER,
            _id(),
            "archive",
            datetime.now(UTC),
        )
    )
    with pytest.raises(
        RegistryCommandConflictV1, match="financial_pool_organization_unavailable"
    ):
        repository.assign(
            _assign(repository, account, billing, org=organization.organization_id)
        )
    create = _assign(repository, account, billing)
    created = repository.assign(create)
    SqliteRegistryRepositoryV1(reference).edit_account(
        EditAccountCommandV1(
            account.account_id,
            account.record_version,
            OWNER,
            _id(),
            "archive",
            datetime.now(UTC),
        )
    )
    archived = repository.get_configuration(
        account.account_id, billing.resource_id, "billing"
    )
    assert archived is not None and archived.scope is None
    with pytest.raises(RegistryCommandConflictV1, match="registry_replay_stale"):
        repository.assign(create)
    revision = repository.list_pools("claude").registry_revision
    snapshot = repository(
        (billing.resource_id,),
        expected_registry_revision=revision,
        as_of=datetime.now(UTC),
    )
    assert snapshot.availability.state == "available" and snapshot.memberships == ()
    assert created.membership is not None


def test_snapshot_never_presents_new_metadata_at_old_time_or_revision(
    tmp_path: Path,
) -> None:
    reference = _database(tmp_path)
    repository = _repository(reference)
    account, billing = _source(reference)
    created = repository.assign(_assign(repository, account, billing))
    assert created.membership is not None
    for revision, as_of in (
        (created.registry_revision - 1, datetime.now(UTC)),
        (
            created.registry_revision,
            created.membership.valid_from - timedelta(microseconds=1),
        ),
    ):
        result = repository(
            (billing.resource_id,), expected_registry_revision=revision, as_of=as_of
        )
        assert result.availability.state == "unavailable"
        assert result.pools == () and result.memberships == ()


def test_current_metadata_read_preserves_financial_cutoff_and_revision_guard(
    tmp_path: Path,
) -> None:
    reference = _database(tmp_path)
    repository = _repository(reference)
    account, billing = _source(reference)
    created = repository.assign(_assign(repository, account, billing))
    assert created.membership is not None
    cutoff = created.membership.valid_from - timedelta(microseconds=1)
    result = repository.read_current(
        (billing.resource_id,),
        expected_registry_revision=created.registry_revision,
        as_of=cutoff,
    )
    assert result.availability.state == "available"
    assert result.as_of == cutoff
    assert result.metadata_basis == "current_registry"
    assert result.pools == (created.pool,)
    assert result.memberships == (created.membership,)
    stale = repository.read_current(
        (billing.resource_id,),
        expected_registry_revision=created.registry_revision - 1,
        as_of=cutoff,
    )
    assert stale.availability.state == "unavailable"
    assert stale.pools == () and stale.memberships == ()
    with pytest.raises(ValueError, match="financial_pool_snapshot_invalid"):
        replace(
            result,
            memberships=(replace(created.membership, valid_until=datetime.now(UTC)),),
        )


@pytest.mark.parametrize("same_command", [False, True])
def test_concurrent_owner_assignments_are_serialized(
    tmp_path: Path, same_command: bool
) -> None:
    reference = _database(tmp_path)
    repository = _repository(reference)
    account, billing = _source(reference)
    command = _assign(repository, account, billing)
    other = command if same_command else replace(command, command_id=_id())
    barrier = Barrier(2)

    def assign(
        value: AssignFinancialPoolCommandV1,
    ) -> FinancialPoolConfigurationV1 | str:
        barrier.wait(timeout=10)
        try:
            return _repository(reference).assign(value)
        except RegistryCommandConflictV1 as error:
            return str(error)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(assign, value) for value in (command, other)]
        outcomes = [future.result(timeout=15) for future in futures]
    successes = [value for value in outcomes if not isinstance(value, str)]
    assert len(successes) == (2 if same_command else 1)
    pool_ids = set()
    for value in successes:
        assert value.pool is not None
        pool_ids.add(value.pool.pool_id)
    assert len(pool_ids) == 1
    assert _counts(reference)[:2] == (1, 1)


def test_long_owner_name_keeps_a_bounded_derived_pool_label(tmp_path: Path) -> None:
    reference = _database(tmp_path)
    repository = _repository(reference)
    account, billing = _source(reference)
    renamed = SqliteRegistryRepositoryV1(reference).edit_account(
        EditAccountCommandV1(
            account.account_id,
            account.record_version,
            OWNER,
            _id(),
            "rename",
            datetime.now(UTC),
            friendly_name="A" * 256,
        )
    )
    result = repository.assign(_assign(repository, renamed, billing))
    assert result.pool is not None
    assert len(result.pool.display_name) == 256
    assert result.pool.display_name.endswith(" · billing")
    current = SqliteRegistryRepositoryV1(reference).get_account(account.account_id)
    assert current is not None and current.friendly_name == "A" * 256


def test_actual_foreign_keys_and_current_epoch_uniqueness(tmp_path: Path) -> None:
    reference = _database(tmp_path)
    repository = _repository(reference)
    first, billing = _source(reference)
    other, other_billing = _source(reference)
    first_pool = repository.assign(_assign(repository, first, billing))
    repository.assign(_assign(repository, other, other_billing))
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            for query, parameters in (
                (
                    "UPDATE reg_financial_pool_membership SET account_id=? "
                    "WHERE resource_id=?",
                    (other.account_id.value, billing.resource_id.value),
                ),
                (
                    "UPDATE reg_financial_pool_membership "
                    "SET cloud_resource_id=resource_id",
                    (),
                ),
                ("UPDATE reg_financial_pool_membership SET provider_key='codex'", ()),
                ("UPDATE reg_financial_pool_membership SET scope_generation=0", ()),
                ("UPDATE reg_financial_pool_membership SET valid_until=valid_from", ()),
                (
                    "UPDATE reg_financial_pool_membership SET resource_id=?,"
                    "billing_resource_id=?,account_id=? WHERE resource_id=?",
                    (
                        billing.resource_id.value,
                        billing.resource_id.value,
                        first.account_id.value,
                        other_billing.resource_id.value,
                    ),
                ),
            ):
                with pytest.raises(IntegrityError):
                    connection.exec_driver_sql(query, parameters)
                connection.rollback()
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    current = repository.get_configuration(
        first.account_id, billing.resource_id, "billing"
    )
    assert current is not None and current.membership == first_pool.membership


def test_noop_join_and_unlink_do_not_create_false_epochs(tmp_path: Path) -> None:
    reference = _database(tmp_path)
    repository = _repository(reference)
    account, billing = _source(reference)
    empty = repository.assign(_assign(repository, account, billing, action="unlink"))
    assert empty.membership is None
    created = repository.assign(_assign(repository, account, billing))
    assert created.pool is not None
    before = _counts(reference)
    same = repository.assign(
        _assign(
            repository, account, billing, action="join", pool_id=created.pool.pool_id
        )
    )
    assert same == created
    assert _counts(reference)[:4] == before[:4]
    assert _counts(reference)[4] == before[4] + 1


def test_scope_edit_closes_membership_without_rewriting_original_scope(
    tmp_path: Path,
) -> None:
    reference = _database(tmp_path)
    account, connection = _source(reference)
    pools = _repository(reference)
    membership_command = _assign(pools, account, connection)
    associated = pools.assign(membership_command)
    assert associated.membership is not None and associated.pool is not None
    registry = SqliteBillingConnectionRepositoryV1(reference)
    command = ChangeBillingScopeCommandV1(
        account.account_id,
        connection.resource_id,
        account.record_version,
        connection.record_version,
        connection.scope_generation,
        "owner-corrected-scope",
        OWNER,
        _id(),
        datetime.now(UTC),
    )
    changed = registry.change_scope(command)
    assert changed.scope_generation == connection.scope_generation + 1
    assert (
        changed.monitoring_preference == "disabled" and changed.lifecycle == "pending"
    )
    current = pools.get_configuration(
        account.account_id, connection.resource_id, "billing"
    )
    assert current is not None and current.scope is not None
    assert current.scope.provider_scope_id == "owner-corrected-scope"
    assert current.membership is None and current.pool is None
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as database:
            retained = database.exec_driver_sql(
                "SELECT provider_scope_id,scope_generation,valid_until "
                "FROM reg_financial_pool_membership WHERE association_id=?",
                (associated.membership.association_id.value,),
            ).one()
    assert (
        retained[0] == connection.scope_id
        and retained[1] == connection.scope_generation
    )
    assert retained[2] is not None
    with pytest.raises(RegistryCommandConflictV1, match="registry_replay_stale"):
        pools.assign(membership_command)
    before = _counts(reference)
    assert registry.change_scope(command) == changed
    assert _counts(reference) == before
    with pytest.raises(
        RegistryCommandConflictV1, match="registry_idempotency_conflict"
    ):
        registry.change_scope(replace(command, scope_id="different-command"))
    with pytest.raises(RegistryCommandConflictV1, match="registry_version_conflict"):
        registry.change_scope(replace(command, command_id=_id()))
    reopened = SqliteBillingConnectionRepositoryV1(reference).get(account.account_id)
    assert reopened is not None and reopened.connections == (changed,)
    assert (
        reopened.credential_status is not None
        and reopened.credential_status.state == "missing"
    )

"""A-DB01: real admin/rule configuration, production SQLite/Alembic, no telemetry."""

import secrets
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from agentmonitor.adapters.identity_access.argon2_password import Argon2PasswordV1
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseOpenModeV1,
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    MIGRATIONS_PATH,
    load_migration_catalog,
    migrate_to_head,
)
from agentmonitor.adapters.persistence.alerting.sqlite.repository import (
    SqliteAlertingRepositoryV1,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.repository import (
    SqliteIdentityAccessRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.contracts.alerting_v1 import (
    AlertRuleListQueryV1,
    AlertScopeRefV1,
    ArchiveAlertRuleCommandV1,
    CapacityRemainingRuleConfigurationV1,
    CreateAlertRuleCommandV1,
    UpdateAlertRuleCommandV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.identity_access_v1 import SecretInputV1
from agentmonitor.modules.alerting.application.rules import (
    ArchiveAlertRuleOverrideV1,
    CreateAlertRuleV1,
    UpdateAlertRuleV1,
)
from agentmonitor.modules.identity_access.application.bootstrap import (
    BootstrapAdministratorV1,
)
from agentmonitor.modules.registry.application.accounts import (
    AlertScopeAndSubjectQueryV1,
)
from agentmonitor.modules.registry.application.organizations import (
    CreateOrganizationCommandV1,
    CreateOrganizationV1,
)
from alembic import command as alembic_command
from alembic.config import Config
from sqlalchemy.exc import IntegrityError


def installation(tmp_path: Path) -> tuple[DatabaseRefV1, OpaqueIdV1]:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    outcome = BootstrapAdministratorV1(
        SqliteIdentityAccessRepositoryV1(reference), Argon2PasswordV1()
    )(SecretInputV1(secrets.token_urlsafe(32)), correlation_id=secrets.token_hex(16))
    assert outcome.code == "created" and outcome.administrator_id is not None
    return reference, outcome.administrator_id


def command(
    actor: OpaqueIdV1, scope: AlertScopeRefV1 | None = None
) -> CreateAlertRuleCommandV1:
    return CreateAlertRuleCommandV1(
        OpaqueIdV1(secrets.token_hex(16)),
        actor,
        "capacity_remaining",
        scope or AlertScopeRefV1("global", None),
        True,
        CapacityRemainingRuleConfigurationV1(1, 3000, 1500),
        datetime.now(UTC),
    )


def actions(
    reference: DatabaseRefV1,
) -> tuple[
    SqliteAlertingRepositoryV1,
    CreateAlertRuleV1,
    UpdateAlertRuleV1,
    ArchiveAlertRuleOverrideV1,
]:
    repository = SqliteAlertingRepositoryV1(reference)
    scope = AlertScopeAndSubjectQueryV1(SqliteRegistryRepositoryV1(reference))
    return (
        repository,
        CreateAlertRuleV1(repository, scope),
        UpdateAlertRuleV1(repository, scope),
        ArchiveAlertRuleOverrideV1(repository, scope),
    )


def test_rule_crud_replay_and_original_receipts_survive_reopen(tmp_path: Path) -> None:
    reference, actor = installation(tmp_path)
    repository, create, update, archive = actions(reference)
    original = command(actor)
    created = create(original)
    assert created.rule.record_version == 1 and created.rule.rule_id is not None
    assert create(replace(original, as_of=datetime.now(UTC))) == created
    edited_command = UpdateAlertRuleCommandV1(
        OpaqueIdV1(secrets.token_hex(16)),
        actor,
        "capacity_remaining",
        original.scope,
        False,
        CapacityRemainingRuleConfigurationV1(1, 4000, 1000),
        datetime.now(UTC),
        created.rule.rule_id,
        1,
    )
    edited = update(edited_command)
    assert edited.rule.record_version == 2 and not edited.rule.enabled
    assert update(replace(edited_command, as_of=datetime.now(UTC))) == edited
    assert create(original) == created
    retired_command = ArchiveAlertRuleCommandV1(
        OpaqueIdV1(secrets.token_hex(16)),
        actor,
        created.rule.rule_id,
        2,
        datetime.now(UTC),
    )
    retired = archive(retired_command)
    assert retired.rule.record_version == 3 and retired.rule.archived_at is not None
    reopened_repository, _, reopened_update, reopened_archive = actions(reference)
    assert reopened_repository.get_rule(created.rule.rule_id) == retired.rule
    assert reopened_update(edited_command) == edited
    assert reopened_archive(retired_command) == retired
    assert (
        reopened_repository.list_rules(AlertRuleListQueryV1(datetime.now(UTC))).items
        == ()
    )
    assert reopened_repository.list_rules(
        AlertRuleListQueryV1(datetime.now(UTC), include_archived=True)
    ).items == (retired.rule,)
    replacement = create(command(actor))
    assert replacement.rule.rule_id != created.rule.rule_id
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM alert_rule_revision"
                ).scalar_one()
                == 4
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM alert_command_receipt"
                ).scalar_one()
                == 4
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM alert_reevaluation_job"
                ).scalar_one()
                == 4
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM alert_event_outbox"
                ).scalar_one()
                == 4
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM alert_alert"
                ).scalar_one()
                == 0
            )


def test_conflicting_keys_and_stale_versions_leave_rule_unchanged(
    tmp_path: Path,
) -> None:
    reference, actor = installation(tmp_path)
    repository, create, update, _ = actions(reference)
    original = command(actor)
    created = create(original)
    assert created.rule.rule_id is not None
    with pytest.raises(ValueError, match="alert_idempotency_conflict"):
        create(replace(original, enabled=False))
    with pytest.raises(ValueError, match="alert_rule_scope_conflict"):
        create(command(actor))
    changed = UpdateAlertRuleCommandV1(
        OpaqueIdV1(secrets.token_hex(16)),
        actor,
        "capacity_remaining",
        original.scope,
        False,
        original.configuration,
        datetime.now(UTC),
        created.rule.rule_id,
        1,
    )
    update(changed)
    with pytest.raises(ValueError, match="alert_version_conflict"):
        update(
            replace(
                changed,
                command_id=OpaqueIdV1(secrets.token_hex(16)),
                as_of=datetime.now(UTC),
            )
        )
    assert repository.get_rule(created.rule.rule_id).record_version == 2  # type: ignore[union-attr]
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM alert_rule_revision"
                ).scalar_one()
                == 2
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM alert_command_receipt"
                ).scalar_one()
                == 2
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM alert_event_outbox"
                ).scalar_one()
                == 2
            )


def test_real_organization_scope_and_empty_provider_fail_closed(tmp_path: Path) -> None:
    reference, actor = installation(tmp_path)
    registry = SqliteRegistryRepositoryV1(reference)
    organization = CreateOrganizationV1(registry)(
        CreateOrganizationCommandV1(
            OpaqueIdV1(secrets.token_hex(16)),
            actor,
            "Alert rule verification",
            None,
            datetime.now(UTC),
        )
    )
    repository, create, _, _ = actions(reference)
    result = create(
        command(
            actor, AlertScopeRefV1("organization", organization.organization_id.value)
        )
    )
    assert result.rule.scope.scope_id == organization.organization_id.value
    with pytest.raises(ValueError, match="alert_scope_unavailable"):
        create(command(actor, AlertScopeRefV1("provider", "claude")))
    assert (
        len(repository.list_rules(AlertRuleListQueryV1(datetime.now(UTC))).items) == 1
    )


def test_concurrent_identical_command_commits_one_atomic_configuration(
    tmp_path: Path,
) -> None:
    reference, actor = installation(tmp_path)
    original = command(actor)

    def perform() -> object:
        _, create, _, _ = actions(reference)
        return create(original)

    with ThreadPoolExecutor(max_workers=2) as workers:
        first, second = tuple(workers.map(lambda _: perform(), range(2)))
    assert first == second
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            for table in (
                "alert_rule",
                "alert_rule_revision",
                "alert_command_receipt",
                "alert_reevaluation_job",
                "alert_event_outbox",
            ):
                assert (
                    connection.exec_driver_sql(
                        f"SELECT count(*) FROM {table}"
                    ).scalar_one()
                    == 1
                )


def test_moving_override_queues_both_affected_real_scopes(tmp_path: Path) -> None:
    """A-DB01: moving an override must reevaluate the abandoned scope too."""
    reference, actor = installation(tmp_path)
    registry = SqliteRegistryRepositoryV1(reference)
    organization = CreateOrganizationV1(registry)(
        CreateOrganizationCommandV1(
            OpaqueIdV1(secrets.token_hex(16)),
            actor,
            "Moved alert rule scope",
            None,
            datetime.now(UTC),
        )
    )
    _, create, update, _ = actions(reference)
    created = create(command(actor))
    assert created.rule.rule_id is not None
    update(
        UpdateAlertRuleCommandV1(
            OpaqueIdV1(secrets.token_hex(16)),
            actor,
            "capacity_remaining",
            AlertScopeRefV1("organization", organization.organization_id.value),
            True,
            CapacityRemainingRuleConfigurationV1(1, 3000, 1500),
            datetime.now(UTC),
            created.rule.rule_id,
            1,
        )
    )
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            affected = set(
                connection.exec_driver_sql(
                    "SELECT scope_kind,scope_key FROM alert_reevaluation_job "
                    "WHERE cause_id=? AND cause_revision=2",
                    (created.rule.rule_id.value,),
                ).all()
            )
            assert affected == {
                ("global", "global"),
                ("organization", organization.organization_id.value),
            }


@pytest.mark.parametrize("table", ["alert_rule", "alert_rule_revision"])
@pytest.mark.parametrize(
    "document",
    [
        '{"schema_major":1}',
        '{"warning_remaining_basis_points":3000,"critical_remaining_basis_points":1500}',
        '{"schema_major":true,"warning_remaining_basis_points":3000,'
        '"critical_remaining_basis_points":1500}',
    ],
)
def test_real_rule_schema_rejects_incomplete_threshold_document(
    tmp_path: Path, table: str, document: str
) -> None:
    """A-DB01: SQLite must enforce mandatory threshold fields, not SQL NULL."""
    reference, actor = installation(tmp_path)
    _, create, _, _ = actions(reference)
    created = create(command(actor))
    assert created.rule.rule_id is not None
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            with pytest.raises(IntegrityError):
                connection.exec_driver_sql(
                    f"UPDATE {table} SET config_json=? WHERE rule_id=?",
                    (document, created.rule.rule_id.value),
                )
            connection.rollback()


def migrate_exact_revision(reference: DatabaseRefV1, revision: str) -> None:
    """Production Alembic on one offline isolated file, with real catalog admission."""
    catalog = load_migration_catalog()
    mode: DatabaseOpenModeV1 = (
        "migration_initialize"
        if reference.validate(missing_ok=True) is None
        else "migration_existing"
    )
    with open_sqlite_database(reference, mode) as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            config = Config()
            config.set_main_option("script_location", str(MIGRATIONS_PATH))
            config.attributes.update(
                connection=connection,
                migrations_path=MIGRATIONS_PATH,
                catalog_digest=catalog.digest,
            )
            alembic_command.upgrade(config, revision)
            connection.commit()


def historical_installation(tmp_path: Path) -> tuple[DatabaseRefV1, OpaqueIdV1]:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_exact_revision(reference, "v1_0704")
    outcome = BootstrapAdministratorV1(
        SqliteIdentityAccessRepositoryV1(reference), Argon2PasswordV1()
    )(SecretInputV1(secrets.token_urlsafe(32)), correlation_id=secrets.token_hex(16))
    assert outcome.code == "created" and outcome.administrator_id is not None
    return reference, outcome.administrator_id


def test_configuration_guard_upgrade_preserves_real_rule_and_revision_history(
    tmp_path: Path,
) -> None:
    reference, actor = historical_installation(tmp_path)
    repository, create, update, _ = actions(reference)
    original = command(actor)
    created = create(original)
    assert created.rule.rule_id is not None
    changed_command = UpdateAlertRuleCommandV1(
        OpaqueIdV1(secrets.token_hex(16)),
        actor,
        "capacity_remaining",
        original.scope,
        False,
        CapacityRemainingRuleConfigurationV1(1, 4000, 1000),
        datetime.now(UTC),
        created.rule.rule_id,
        1,
    )
    changed = update(changed_command)
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            prior_revisions = connection.exec_driver_sql(
                "SELECT * FROM alert_rule_revision ORDER BY record_version"
            ).all()
    migrate_exact_revision(reference, "v1_0705")
    assert repository.get_rule(created.rule.rule_id) == changed.rule
    assert create(original) == created
    assert update(changed_command) == changed
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT * FROM alert_rule_revision ORDER BY record_version"
                ).all()
                == prior_revisions
            )
            assert connection.exec_driver_sql("PRAGMA integrity_check").scalar() == "ok"
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []


@pytest.mark.parametrize("table", ["alert_rule", "alert_rule_revision"])
def test_configuration_guard_preflight_preserves_invalid_prior_database(
    tmp_path: Path, table: str
) -> None:
    reference, actor = historical_installation(tmp_path)
    _, create, _, _ = actions(reference)
    created = create(command(actor))
    assert created.rule.rule_id is not None
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql(
                f"UPDATE {table} SET config_json=? WHERE rule_id=?",
                ('{"schema_major":1}', created.rule.rule_id.value),
            )
            connection.commit()
    with pytest.raises(
        ValueError, match="alert_rule_configuration_guard_preflight_failed"
    ):
        migrate_exact_revision(reference, "v1_0705")
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT version_num FROM alembic_version"
                ).scalar_one()
                == "v1_0704"
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM sqlite_schema WHERE type='trigger' "
                    "AND name LIKE 'tr_alert_rule%configuration_%'"
                ).scalar_one()
                == 0
            )
            assert (
                connection.exec_driver_sql(
                    f"SELECT config_json FROM {table} WHERE rule_id=?",
                    (created.rule.rule_id.value,),
                ).scalar_one()
                == '{"schema_major":1}'
            )

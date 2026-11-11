"""ST-REG-001 real file-backed SQLite/Alembic registry evidence."""

from datetime import UTC, datetime
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    InspectSchemaCompatibilityV1,
    application_schema_range,
    migrate_to_head,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.registry.application.accounts import (
    AlertScopeAndSubjectQueryV1,
    ListAccountResourcesV1,
    ListAccountsV1,
    ListMonitoringProfilesV1,
    RegisterAccountV1,
)
from agentmonitor.modules.registry.application.discovery import (
    ListDiscoveryCandidatesV1,
)
from agentmonitor.modules.registry.application.organizations import (
    CreateOrganizationCommandV1,
    CreateOrganizationV1,
)

NOW = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)
REGISTRY_TABLES = {
    "reg_billing_connection",
    "reg_registry_state",
    "reg_organization",
    "reg_provider_definition",
    "reg_account",
    "reg_registry_change",
    "reg_provider_installation",
    "reg_discovery_candidate",
    "reg_provider_identity_claim",
    "reg_identity_decision",
    "reg_monitoring_profile",
    "reg_account_resource",
    "reg_profile_resource_link",
    "reg_account_configuration_reference",
    "reg_command_receipt",
    "reg_event_outbox",
    "reg_credential_binding_state",
    "reg_credential_binding",
    "reg_provider_access_target",
    "reg_cloud_monitoring_target",
    "reg_credential_binding_verification",
    "reg_credential_binding_verification_history",
    "reg_organization_provider_coverage",
    "reg_organization_provider_coverage_revision",
}


def _database(tmp_path: Path) -> DatabaseRefV1:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    return reference


def test_current_registry_migrations_create_owned_schema_without_rows(
    tmp_path: Path,
) -> None:
    """M02-DB-001/DB-MIG-001: current chain preserves empty M02 schema."""
    reference = _database(tmp_path)
    view = InspectSchemaCompatibilityV1(
        reference, application_schema_range(), "runtime_read_write"
    )

    assert view.state == "compatible"
    assert view.current_revision == application_schema_range().migration_target_revision
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            tables = set(
                connection.exec_driver_sql(
                    "SELECT name FROM sqlite_schema WHERE type='table' "
                    "AND name LIKE 'reg_%' ORDER BY name"
                ).scalars()
            )
            counts = {
                table: connection.exec_driver_sql(
                    f"SELECT count(*) FROM {table}"  # noqa: S608 - closed table set
                ).scalar_one()
                for table in REGISTRY_TABLES
            }
            foreign_keys = {
                table: connection.exec_driver_sql(
                    f"PRAGMA foreign_key_list({table})"  # noqa: S608 - closed table set
                ).fetchall()
                for table in REGISTRY_TABLES
            }
            assert connection.exec_driver_sql("PRAGMA integrity_check").scalar() == "ok"
    assert tables == REGISTRY_TABLES
    assert counts == {table: 0 for table in REGISTRY_TABLES}
    assert all(
        row[2].startswith("reg_") for rows in foreign_keys.values() for row in rows
    )
    resource_parent_fks = {
        (row[2], row[3], row[4])
        for row in foreign_keys["reg_account_resource"]
        if row[2] == "reg_account_resource"
    }
    link_profile_fks = {
        (row[2], row[3], row[4])
        for row in foreign_keys["reg_profile_resource_link"]
        if row[2] == "reg_monitoring_profile"
    }
    link_resource_fks = {
        (row[2], row[3], row[4])
        for row in foreign_keys["reg_profile_resource_link"]
        if row[2] == "reg_account_resource"
    }
    assert resource_parent_fks == {
        ("reg_account_resource", "account_id", "account_id"),
        ("reg_account_resource", "parent_resource_id", "resource_id"),
    }
    assert link_profile_fks == {
        ("reg_monitoring_profile", "account_id", "account_id"),
        ("reg_monitoring_profile", "profile_id", "profile_id"),
    }
    assert link_resource_fks == {
        ("reg_account_resource", "account_id", "account_id"),
        ("reg_account_resource", "resource_id", "resource_id"),
    }


def test_create_organization_commits_revision_history_outbox_and_receipt(
    tmp_path: Path,
) -> None:
    """M02-DB-002: production use case commits its atomic registry facts."""
    reference = _database(tmp_path)
    repository = SqliteRegistryRepositoryV1(reference)
    create = CreateOrganizationV1(repository)

    result = create(
        CreateOrganizationCommandV1(
            command_id=OpaqueIdV1("command-create-organization-1"),
            principal_id=OpaqueIdV1("principal-owner-1"),
            name="Temporary Registry Verification",
            description=None,
            requested_at=NOW,
        )
    )
    replay = create(
        CreateOrganizationCommandV1(
            command_id=OpaqueIdV1("command-create-organization-1"),
            principal_id=OpaqueIdV1("principal-owner-1"),
            name="Temporary Registry Verification",
            description=None,
            requested_at=NOW,
        )
    )

    assert result == replay
    assert result.registry_revision == 1
    assert result.record_version == 1
    assert repository.list_organizations() == (result,)
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT registry_revision FROM reg_registry_state "
                    "WHERE singleton_key=1"
                ).scalar_one()
                == 1
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM reg_registry_change"
                ).scalar_one()
                == 1
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM reg_event_outbox"
                ).scalar_one()
                == 1
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM reg_command_receipt"
                ).scalar_one()
                == 1
            )


def test_same_command_id_with_different_safe_fingerprint_conflicts(
    tmp_path: Path,
) -> None:
    """M02-DB-002: idempotency key reuse cannot change its command."""
    reference = _database(tmp_path)
    create = CreateOrganizationV1(SqliteRegistryRepositoryV1(reference))
    first = CreateOrganizationCommandV1(
        command_id=OpaqueIdV1("command-create-organization-1"),
        principal_id=OpaqueIdV1("principal-owner-1"),
        name="Temporary Registry Verification",
        description=None,
        requested_at=NOW,
    )
    create(first)

    from agentmonitor.modules.registry.application.organizations import (
        RegistryCommandConflictV1,
    )

    try:
        create(
            CreateOrganizationCommandV1(
                command_id=first.command_id,
                principal_id=first.principal_id,
                name="Different Temporary Organization",
                description=None,
                requested_at=NOW,
            )
        )
    except RegistryCommandConflictV1 as error:
        assert str(error) == "registry_idempotency_conflict"
    else:
        raise AssertionError("idempotency conflict was not raised")


def test_task2_query_surface_reads_empty_real_registry(tmp_path: Path) -> None:
    """CTR-REG-009 empty-state query uses the production real-SQLite repository."""
    repository = SqliteRegistryRepositoryV1(_database(tmp_path))
    missing_account = OpaqueIdV1("missing-account")

    assert ListDiscoveryCandidatesV1(repository)() == ()
    assert ListAccountsV1(repository)() == ()
    assert ListMonitoringProfilesV1(repository)(missing_account) == ()
    assert ListAccountResourcesV1(repository)(missing_account) == ()
    assert callable(RegisterAccountV1(repository))
    snapshot = AlertScopeAndSubjectQueryV1(repository)("global")
    assert snapshot.registry_revision == 0
    assert snapshot.completeness_state == "complete"
    assert snapshot.organization_ids == ()
    assert snapshot.account_ids == ()
    assert snapshot.resource_ids == ()

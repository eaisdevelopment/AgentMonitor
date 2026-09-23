"""M05 empty real SQLite schema and non-observational repository evidence."""

from datetime import UTC, datetime
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    InspectSchemaCompatibilityV1,
    application_schema_range,
    load_migration_catalog,
    migrate_to_head,
)
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    CapacityRepositoryErrorV1,
    SqliteCapacityRepositoryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.capacity.application.queries import (
    GetAccountCapacityV1,
    GetCapacityHealthV1,
    GetCollectionCommitStatusV1,
    ListQuotaWindowsV1,
)

CAPACITY_TABLES = {
    "capacity_resource_policy",
    "capacity_quota_window_definition",
    "capacity_budget_definition",
    "capacity_quota_observation",
    "capacity_quota_measure",
    "capacity_budget_observation",
    "capacity_budget_measure",
    "capacity_usage_bucket",
    "capacity_usage_dimension",
    "capacity_usage_measure",
    "capacity_observation_provenance",
    "capacity_commit_receipt",
    "capacity_commit_receipt_observation",
    "capacity_current_projection",
    "capacity_health_projection",
    "capacity_aggregate_projection",
    "capacity_aggregate_value",
    "capacity_availability_signal",
    "capacity_event_outbox",
    "capacity_event_delivery",
    "capacity_derivation",
    "capacity_derivation_input",
    "capacity_forecast_projection",
    "capacity_retention_run",
}


def _database(tmp_path: Path) -> DatabaseRefV1:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    return reference


def test_capacity_schema_chain_reaches_v1_0504_without_business_rows(
    tmp_path: Path,
) -> None:
    """M05-DB-001: full production chain allocates an empty frozen schema."""
    reference = _database(tmp_path)
    view = InspectSchemaCompatibilityV1(
        reference, application_schema_range(), "runtime_read_write"
    )
    assert view.state == "compatible"
    assert view.current_revision == application_schema_range().maximum_writable_revision
    assert "v1_0504" in {
        revision.revision for revision in load_migration_catalog().revisions
    }

    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            tables = set(
                connection.exec_driver_sql(
                    "SELECT name FROM sqlite_schema WHERE type='table' "
                    "AND name LIKE 'capacity_%' ORDER BY name"
                ).scalars()
            )
            counts = {
                table: connection.exec_driver_sql(
                    f"SELECT count(*) FROM {table}"  # noqa: S608 - closed set
                ).scalar_one()
                for table in CAPACITY_TABLES
            }
            foreign_keys = {
                table: connection.exec_driver_sql(
                    f"PRAGMA foreign_key_list({table})"  # noqa: S608 - closed set
                ).fetchall()
                for table in CAPACITY_TABLES
            }
            assert connection.exec_driver_sql("PRAGMA integrity_check").scalar() == "ok"

    assert tables == CAPACITY_TABLES
    assert counts == {table: 0 for table in CAPACITY_TABLES}
    assert all(
        row[2].startswith("capacity_") for rows in foreign_keys.values() for row in rows
    )


def test_capacity_schema_enforces_receipt_projection_and_retention_invariants(
    tmp_path: Path,
) -> None:
    """M05-DB-001: empty DDL allocates closed conflict/audit invariants."""
    reference = _database(tmp_path)
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            receipt_indexes = connection.exec_driver_sql(
                "PRAGMA index_list(capacity_commit_receipt)"
            ).fetchall()
            unique_columns = {
                tuple(
                    row[2]
                    for row in connection.exec_driver_sql(
                        f"PRAGMA index_info({index[1]})"  # noqa: S608 - catalog name
                    ).fetchall()
                )
                for index in receipt_indexes
                if index[2]
            }
            columns = {
                table: {
                    row[1]
                    for row in connection.exec_driver_sql(
                        f"PRAGMA table_info({table})"  # noqa: S608 - closed set
                    ).fetchall()
                }
                for table in (
                    "capacity_health_projection",
                    "capacity_availability_signal",
                    "capacity_retention_run",
                    "capacity_aggregate_projection",
                )
            }
            sql = {
                name: str(
                    connection.exec_driver_sql(
                        "SELECT sql FROM sqlite_schema WHERE name=?", (name,)
                    ).scalar_one()
                )
                for name in (
                    "capacity_budget_measure",
                    "capacity_health_projection",
                    "capacity_derivation",
                    "capacity_derivation_input",
                    "capacity_forecast_projection",
                )
            }

    assert ("collection_run_id", "capability_id") in unique_columns
    assert {
        "input_set_digest",
        "availability_signal_generation",
        "valid_until",
        "updated_at",
    } <= columns["capacity_health_projection"]
    assert {
        "event_id",
        "generation",
        "stream_sequence",
        "source_contract",
        "source_version",
        "recorded_at",
        "cleared_by_event_id",
    } <= columns["capacity_availability_signal"]
    assert {
        "as_of",
        "preview_digest",
        "export_checkpoint_ref",
        "batch_count",
        "correlation_id",
    } <= columns["capacity_retention_run"]
    assert {
        "constrained_count",
        "critical_count",
        "exhausted_count",
        "reauthentication_required_count",
        "fresh_count",
        "stale_count",
        "freshness_unknown_count",
        "conflicted_count",
        "source_coverage_state",
        "pool_inventory_json",
        "omitted_reason_codes_json",
    } <= columns["capacity_aggregate_projection"]
    assert "minor_units IS NULL OR minor_units >= 0" in sql["capacity_budget_measure"]
    assert "currency GLOB '[A-Z][A-Z][A-Z]'" in sql["capacity_budget_measure"]
    assert "freshness_state IN" in sql["capacity_health_projection"]
    assert "derivation_kind IN" in sql["capacity_derivation"]
    assert "'projection'" in sql["capacity_derivation_input"]
    assert "'availability_event'" in sql["capacity_derivation_input"]
    assert "insufficient_input" in sql["capacity_forecast_projection"]
    assert "not_applicable" in sql["capacity_forecast_projection"]
    assert "conflicted" in sql["capacity_forecast_projection"]


def test_empty_repository_reports_not_committed_without_telemetry(
    tmp_path: Path,
) -> None:
    """M05-DB-001: an empty real repository never invents a receipt."""
    repository = SqliteCapacityRepositoryV1(_database(tmp_path))

    status = GetCollectionCommitStatusV1(repository)(
        OpaqueIdV1("collection-run-with-no-result"), "subscription.quota"
    )

    assert status.state == "not_committed"
    assert status.receipt is None
    account_id = OpaqueIdV1("account-with-no-result")
    resource_id = OpaqueIdV1("resource-with-no-result")
    assert (
        ListQuotaWindowsV1(repository).for_scope(
            account_id,
            resource_id,
            "subscription.quota",
            as_of=datetime(2026, 9, 22, tzinfo=UTC),
        )
        == ()
    )
    queries = (
        lambda: GetCapacityHealthV1(repository)(
            account_id,
            resource_id,
            "subscription.quota",
            datetime(2026, 9, 22, tzinfo=UTC),
        ),
        lambda: GetAccountCapacityV1(repository).for_scope(
            account_id,
            resource_id,
            "subscription.quota",
            as_of=datetime(2026, 9, 22, tzinfo=UTC),
        ),
    )
    for query in queries:
        try:
            query()
        except CapacityRepositoryErrorV1 as error:
            assert error.code in {"capacity_health_not_found", "capacity_not_found"}
        else:
            raise AssertionError("empty capacity query invented a result")


def test_quota_page_executes_bounded_keyset_query_without_inventing_rows(
    tmp_path: Path,
) -> None:
    """API-HTTP-021: M05 paging is bounded even while live quota data is absent."""
    repository = SqliteCapacityRepositoryV1(_database(tmp_path))
    account_id = OpaqueIdV1("account-with-no-live-quota-observation")
    as_of = datetime(2026, 9, 22, tzinfo=UTC)

    assert repository.page_account_quota_windows(account_id, as_of, 2, None) == ()
    try:
        repository.page_account_quota_windows(account_id, as_of, 202, None)
    except CapacityRepositoryErrorV1 as error:
        assert error.code == "capacity_query_invalid"
    else:
        raise AssertionError("unbounded quota page was accepted")

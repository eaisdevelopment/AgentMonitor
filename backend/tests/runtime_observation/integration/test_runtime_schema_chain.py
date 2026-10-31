"""M06 production migration-chain acceptance against a real SQLite file."""

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


def test_runtime_schema_chain_reaches_v1_0603(tmp_path: Path) -> None:
    """M06-DB-001: canonical production chain allocates all runtime tables."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)

    view = InspectSchemaCompatibilityV1(
        reference, application_schema_range(), "runtime_read_write"
    )
    catalog = load_migration_catalog()
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            tables = set(
                connection.exec_driver_sql(
                    "SELECT name FROM sqlite_schema WHERE type='table' "
                    "AND name LIKE 'runtime_%' ORDER BY name"
                ).scalars()
            )

    assert view.current_revision == application_schema_range().migration_target_revision
    assert tuple(
        item.revision for item in catalog.revisions if item.owner == "M06"
    ) == (
        "v1_0600",
        "v1_0601",
        "v1_0602",
        "v1_0603",
    )
    assert {
        "runtime_session",
        "runtime_process_instance",
        "runtime_process_snapshot",
        "runtime_session_observation",
        "runtime_metric_observation",
        "runtime_session_process_link",
        "runtime_session_relationship",
        "runtime_correlation_evidence",
        "runtime_session_correlation_decision",
        "runtime_stall_policy",
        "runtime_state_transition",
        "runtime_ingest_receipt",
        "runtime_event_outbox",
    } == tables

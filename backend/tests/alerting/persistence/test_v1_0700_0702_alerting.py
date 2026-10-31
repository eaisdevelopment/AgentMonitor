"""A-DB01/05: production Alembic chain, no invented alert telemetry."""

from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    load_migration_catalog,
    migrate_to_head,
)

ALERT_TABLES = {
    "alert_rule",
    "alert_rule_revision",
    "alert_alert",
    "alert_event",
    "alert_evidence_reference",
    "alert_event_receipt",
    "alert_stream_checkpoint",
    "alert_command_receipt",
    "alert_deadline",
    "alert_reevaluation_job",
    "alert_event_outbox",
    "alert_retention_run",
}


def test_real_fresh_chain_has_owned_empty_alert_schema(tmp_path: Path) -> None:
    catalog = load_migration_catalog()
    owned = tuple(item for item in catalog.revisions if item.owner == "M07")
    assert tuple(item.revision for item in owned) == (
        "v1_0700",
        "v1_0701",
        "v1_0702",
        "v1_0705",
    ), "A-DB01: reviewed production alert revisions are absent"
    assert tuple(item.parent_revision for item in owned) == (
        "v1_0603",
        "v1_0700",
        "v1_0701",
        "v1_0704",
    )
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            actual = set(
                connection.exec_driver_sql(
                    "SELECT name FROM sqlite_schema WHERE type='table' "
                    "AND name LIKE 'alert_%'"
                ).scalars()
            )
            assert actual == ALERT_TABLES
            for table in sorted(ALERT_TABLES):
                assert (
                    connection.exec_driver_sql(
                        f"SELECT count(*) FROM {table}"  # closed owner table set
                    ).scalar_one()
                    == 0
                )
                assert all(
                    row[2].startswith("alert_")
                    for row in connection.exec_driver_sql(
                        f"PRAGMA foreign_key_list({table})"
                    )
                )
            assert connection.exec_driver_sql("PRAGMA integrity_check").scalar() == "ok"
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []

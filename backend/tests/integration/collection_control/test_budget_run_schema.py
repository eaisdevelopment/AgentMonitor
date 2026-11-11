"""Actual empty M04 storage for report references; no seeded collection runs."""

from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)


def test_budget_run_can_keep_empty_report_identity_without_fake_observations(
    tmp_path: Path,
) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            columns = {
                row[1]
                for row in connection.exec_driver_sql(
                    "PRAGMA table_info(collection_budget_run)"
                )
            }
            assert {
                "run_id",
                "canonical_target_json",
                "report_id",
                "consumer_key",
                "consumer_version",
                "receipt_version",
            } <= columns
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM collection_budget_run"
                ).scalar_one()
                == 0
            )
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []

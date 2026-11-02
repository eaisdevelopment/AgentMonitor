"""The real migrated SQLite schema preserves source period starts."""

from pathlib import Path

from sqlalchemy import inspect

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)


def test_quota_observation_has_nullable_source_period_start(tmp_path: Path) -> None:
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    with open_sqlite_database(ref, "runtime_read_only") as database:
        with database.connect() as connection:
            columns = {
                item["name"]: item
                for item in inspect(connection).get_columns(
                    "capacity_quota_observation"
                )
            }
            assert columns["source_period_start"]["nullable"]

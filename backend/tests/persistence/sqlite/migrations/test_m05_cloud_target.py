"""Real empty SQLite migration preserves explicit M05 cloud target identity."""

from pathlib import Path

from sqlalchemy import inspect

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)


def test_capacity_target_columns_do_not_require_an_installation(tmp_path: Path) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    with open_sqlite_database(reference, "runtime_read_only") as database:
        with database.connect() as connection:
            inspector = inspect(connection)
            for table in (
                "capacity_quota_window_definition",
                "capacity_current_projection",
            ):
                columns = {
                    item["name"]: item for item in inspector.get_columns(table)
                }
                assert columns["installation_id"]["nullable"] is True
                assert {"provider_target_kind", "provider_target_id"} <= set(columns)

"""M04 must record no-response terminals without inventing response times."""

from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from sqlalchemy import inspect


def test_versioned_no_response_terminal_table_exists(tmp_path: Path) -> None:
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    with open_sqlite_database(ref, "runtime_read_only") as db:
        with db.connect() as connection:
            names = set(inspect(connection).get_table_names())
            assert "collection_cloud_no_response_terminal" in names

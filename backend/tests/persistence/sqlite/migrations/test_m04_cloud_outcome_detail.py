"""Durable cloud failures retain a safe category across recovery."""

from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from sqlalchemy import inspect


def test_cloud_journal_has_nullable_failure_code(tmp_path: Path) -> None:
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    with open_sqlite_database(ref, "runtime_read_only") as db:
        with db.connect() as connection:
            columns = {
                item["name"]: item
                for item in inspect(connection).get_columns(
                    "collection_cloud_attempt_journal"
                )
            }
            assert columns["failure_code"]["nullable"]
            indexes = {
                item["name"]: item
                for item in inspect(connection).get_indexes(
                    "collection_cloud_attempt_journal"
                )
            }
            assert indexes["uq_collection_cloud_attempt_run"]["unique"]

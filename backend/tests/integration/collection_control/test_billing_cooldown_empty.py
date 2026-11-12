"""Real empty-storage cooldown queries; no invented runs or provider telemetry."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    CollectionRepositoryErrorV1,
    SqliteCollectionRepositoryV1,
)


def test_empty_budget_cooldown_reads_without_creating_rows(tmp_path: Path) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    repository = SqliteCollectionRepositoryV1(reference)
    assert (
        repository.get_budget_next_allowed_at(
            "a" * 64, "request", "count", datetime.now(UTC)
        )
        is None
    )
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            for table in (
                "collection_run",
                "collection_budget_reservation",
                "collection_schedule",
            ):
                assert (
                    connection.exec_driver_sql(
                        f"SELECT count(*) FROM {table}"
                    ).scalar_one()
                    == 0
                )
            assert (
                connection.exec_driver_sql("PRAGMA integrity_check").scalar_one()
                == "ok"
            )


@pytest.mark.parametrize(
    "scope,dimension,unit,instant",
    [
        ("g" * 64, "request", "count", datetime.now(UTC)),
        ("A" * 64, "request", "count", datetime.now(UTC)),
        ("a" * 63, "request", "count", datetime.now(UTC)),
        ("a" * 64, "", "count", datetime.now(UTC)),
        ("a" * 64, "request", "count bad", datetime.now(UTC)),
        ("a" * 64, "request", "count", datetime(2026, 11, 12)),
    ],
)
def test_invalid_cooldown_query_is_rejected_before_storage(
    tmp_path: Path, scope: str, dimension: str, unit: str, instant: datetime
) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    with pytest.raises(CollectionRepositoryErrorV1, match="collection_query_invalid"):
        SqliteCollectionRepositoryV1(reference).get_budget_next_allowed_at(
            scope, dimension, unit, instant
        )
    assert not (tmp_path / "agentmonitor.db").exists()

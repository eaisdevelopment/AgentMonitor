"""DB-M4-READ-001..003: actual isolated SQLite, no boundary doubles."""

import importlib
import sqlite3
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)


def implementation() -> ModuleType:
    return importlib.import_module(
        "agentmonitor.adapters.persistence._shared.sqlite.core.bounded_read"
    )


def initialize(tmp_path: Path) -> DatabaseRefV1:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    with open_sqlite_database(reference, "migration_initialize"):
        pass
    return reference


def deadline(milliseconds: int = 1000) -> datetime:
    return datetime.now(UTC) + timedelta(milliseconds=milliseconds)


def test_bounded_reader_policy_and_connection_close(tmp_path: Path) -> None:
    bounded = implementation()
    reference = initialize(tmp_path)
    with bounded.open_bounded_sqlite_read(
        reference, deadline=deadline(), allowed_tables=frozenset({"sqlite_schema"})
    ) as reader:
        for key, expected in (
            ("query_only", 1),
            ("foreign_keys", 1),
            ("journal_mode", "wal"),
            ("synchronous", 2),
            ("read_uncommitted", 0),
            ("trusted_schema", 0),
        ):
            assert reader.fetch_one(f"PRAGMA {key}") == (expected,)
        assert 0 < reader.fetch_one("PRAGMA busy_timeout")[0] <= 1000
        assert reader.fetch_one("SELECT count(*) FROM sqlite_schema") == (0,)
    with pytest.raises(SqlitePolicyError) as caught:
        reader.fetch_one("SELECT 1")
    assert caught.value.code == "database_handle_closed"


@pytest.mark.parametrize(
    "statement",
    [
        "PRAGMA user_version=9",
        "CREATE TABLE forbidden(value TEXT)",
        "ATTACH DATABASE ? AS forbidden",
        "PRAGMA query_only=OFF",
        "PRAGMA busy_timeout=5000",
    ],
)
def test_reader_denies_actual_mutations(tmp_path: Path, statement: str) -> None:
    bounded = implementation()
    reference = initialize(tmp_path)
    original = reference._path.read_bytes()
    with pytest.raises(SqlitePolicyError) as caught:
        with bounded.open_bounded_sqlite_read(
            reference, deadline=deadline(), allowed_tables=frozenset({"sqlite_schema"})
        ) as reader:
            parameters = (
                (str(tmp_path / "unapproved.db"),)
                if statement.startswith("ATTACH")
                else ()
            )
            reader.fetch_one(statement, parameters)
    assert caught.value.code == "persistence_read_only"
    assert str(tmp_path) not in str(caught.value)
    assert statement not in str(caught.value)
    assert reference._path.read_bytes() == original


def test_reader_refuses_table_outside_explicit_allowlist(tmp_path: Path) -> None:
    bounded = implementation()
    reference = initialize(tmp_path)
    with pytest.raises(SqlitePolicyError) as caught:
        with bounded.open_bounded_sqlite_read(
            reference, deadline=deadline(), allowed_tables=frozenset()
        ) as reader:
            reader.fetch_one("SELECT count(*) FROM sqlite_schema")
    assert caught.value.code == "persistence_read_only"


def test_actual_vm_work_interrupts_before_returning(tmp_path: Path) -> None:
    bounded = implementation()
    reference = initialize(tmp_path)
    started = time.monotonic()
    with pytest.raises(SqlitePolicyError) as caught:
        with bounded.open_bounded_sqlite_read(
            reference, deadline=deadline(100), allowed_tables=frozenset()
        ) as reader:
            reader.fetch_one(
                "WITH RECURSIVE work(x) AS (VALUES(1) UNION ALL "
                "SELECT x+1 FROM work WHERE x < 1000000000) SELECT sum(x) FROM work"
            )
    assert caught.value.code == "database_timeout"
    assert time.monotonic() - started < 0.5
    with bounded.open_bounded_sqlite_read(
        reference, deadline=deadline(), allowed_tables=frozenset()
    ) as fresh:
        assert fresh.fetch_one("SELECT 1") == (1,)


def test_actual_exclusive_lock_is_bounded_before_connection_returns(
    tmp_path: Path,
) -> None:
    bounded = implementation()
    reference = initialize(tmp_path)
    writer = sqlite3.connect(reference._path)
    try:
        writer.execute("PRAGMA locking_mode=EXCLUSIVE")
        writer.execute("BEGIN EXCLUSIVE")
        writer.execute("PRAGMA user_version=1")
        started = time.monotonic()
        with pytest.raises(SqlitePolicyError) as caught:
            with bounded.open_bounded_sqlite_read(
                reference, deadline=deadline(100), allowed_tables=frozenset()
            ):
                pytest.fail("exclusive writer admitted a second reader")
        assert caught.value.code in {"database_timeout", "persistence_busy"}
        assert time.monotonic() - started < 0.5
    finally:
        writer.rollback()
        writer.close()


def test_identity_changed_during_read_is_refused_after_close(tmp_path: Path) -> None:
    bounded = implementation()
    reference = initialize(tmp_path)
    with pytest.raises(SqlitePolicyError) as caught:
        with bounded.open_bounded_sqlite_read(
            reference, deadline=deadline(), allowed_tables=frozenset()
        ) as reader:
            assert reader.fetch_one("SELECT 1") == (1,)
            reference._path.rename(tmp_path / "preserved.db")
            reference._path.touch(mode=0o600)
    assert caught.value.code == "database_identity_changed"
    with pytest.raises(SqlitePolicyError):
        reader.fetch_one("SELECT 1")

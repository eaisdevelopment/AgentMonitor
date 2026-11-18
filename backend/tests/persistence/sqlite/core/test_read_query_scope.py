"""Real file/connection lifetime and security under synchronous read reuse."""

import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
    sqlite_read_query_scope,
)
from sqlalchemy.exc import OperationalError


def initialized(root: Path) -> DatabaseRefV1:
    root.mkdir(mode=0o700)
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    with open_sqlite_database(reference, "migration_initialize"):
        pass
    return reference


def read(reference: DatabaseRefV1) -> tuple[object, int]:
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            return (
                connection.connection.driver_connection,
                connection.exec_driver_sql("PRAGMA user_version").scalar_one(),
            )


def assert_closed(driver: object) -> None:
    assert isinstance(driver, sqlite3.Connection)
    with pytest.raises(sqlite3.ProgrammingError):
        driver.execute("SELECT 1")


def test_nested_reads_reuse_connection_but_observe_external_commits(
    tmp_path: Path,
) -> None:
    reference = initialized(tmp_path / "database")
    with sqlite_read_query_scope(reference):
        first, initial = read(reference)
        assert initial == 0
        with open_sqlite_database(reference, "runtime_read_write") as writer:
            with writer.connect() as connection:
                assert connection.connection.driver_connection is not first
                connection.exec_driver_sql("PRAGMA user_version=17")
                connection.commit()
        with sqlite_read_query_scope(reference):
            second, current = read(reference)
        assert second is first and current == 17
        third, current = read(reference)
        assert third is first and current == 17
    assert_closed(first)
    with sqlite_read_query_scope(reference):
        subsequent, current = read(reference)
        assert subsequent is not first and current == 17
    assert_closed(subsequent)


def test_reused_read_keeps_policy_permissions_and_identity_checks(
    tmp_path: Path,
) -> None:
    reference = initialized(tmp_path / "database")
    path = tmp_path / "database/agentmonitor.db"
    replacement = initialized(tmp_path / "replacement")
    with sqlite_read_query_scope(reference):
        driver, _ = read(reference)
        assert isinstance(driver, sqlite3.Connection)
        driver.execute("PRAGMA foreign_keys=OFF")
        with open_sqlite_database(reference, "runtime_read_only") as handle:
            with handle.connect() as connection:
                assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
                with pytest.raises(OperationalError) as caught:
                    connection.exec_driver_sql(
                        "CREATE TABLE forbidden_write (id INTEGER)"
                    )
                assert isinstance(caught.value.orig, sqlite3.Error)
                assert caught.value.orig.sqlite_errorcode == sqlite3.SQLITE_READONLY
        path.chmod(0o644)
        try:
            with pytest.raises(SqlitePolicyError, match="database_permissions_unsafe"):
                read(reference)
        finally:
            path.chmod(0o600)
        os.replace(replacement._path, path)
        with pytest.raises(SqlitePolicyError, match="database_identity_changed"):
            read(reference)
    assert_closed(driver)


def test_exception_closes_only_its_scope_and_restores_parent(tmp_path: Path) -> None:
    first = initialized(tmp_path / "first")
    second = initialized(tmp_path / "second")
    with sqlite_read_query_scope(first):
        outer, _ = read(first)
        with pytest.raises(ValueError, match="scope_exit_probe"):
            with sqlite_read_query_scope(second):
                inner, _ = read(second)
                raise ValueError("scope_exit_probe")
        assert_closed(inner)
        restored, _ = read(first)
        assert restored is outer
    assert_closed(outer)


def test_concurrent_query_scopes_do_not_share_connections(tmp_path: Path) -> None:
    reference = initialized(tmp_path / "database")
    barrier = Barrier(2)

    def query() -> object:
        with sqlite_read_query_scope(reference):
            driver, _ = read(reference)
            barrier.wait(timeout=10)
            assert read(reference)[0] is driver
            return driver

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(query), pool.submit(query)]
        first, second = [future.result(timeout=20) for future in futures]
    assert first is not second
    assert_closed(first)
    assert_closed(second)

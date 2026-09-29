"""Private M04 deadline writer; no connection escapes this adapter family."""

import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
)

_TABLES = frozenset(
    {
        "collection_schedule",
        "collection_run",
        "collection_run_observation_ref",
        "collection_alert_condition",
        "collection_event_outbox",
        "collection_event_delivery",
    }
)


class CollectorConditionStorageErrorV1(ValueError):
    def __init__(self, code: str = "collector_query_unavailable") -> None:
        self.code = code
        super().__init__(code)


class _ConditionWriterV1:
    def __init__(self, connection: sqlite3.Connection, end: float) -> None:
        self._connection = connection
        self._end = end
        self._closed = False

    def remaining(self) -> int:
        remaining = int((self._end - time.monotonic()) * 1000)
        if self._closed or remaining < 1:
            raise CollectorConditionStorageErrorV1("collector_query_unavailable")
        return min(2000, remaining)

    def authorize(
        self,
        action: int,
        first: str | None,
        second: str | None,
        database: str | None,
        source: str | None,
    ) -> int:
        allowed = action in {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_RECURSIVE}
        if action in {
            sqlite3.SQLITE_READ,
            sqlite3.SQLITE_INSERT,
            sqlite3.SQLITE_UPDATE,
            sqlite3.SQLITE_DELETE,
        }:
            allowed = database in {None, "main"} and first in _TABLES
        elif action == sqlite3.SQLITE_FUNCTION:
            allowed = second in {"count", "max", "min", "coalesce", "length", "glob"}
        elif action == sqlite3.SQLITE_TRANSACTION:
            allowed = first in {"BEGIN", "COMMIT", "ROLLBACK"}
        return sqlite3.SQLITE_OK if allowed else sqlite3.SQLITE_DENY

    def rows(
        self, statement: str, parameters: tuple[object, ...] = (), *, limit: int = 201
    ) -> tuple[sqlite3.Row, ...]:
        if not 1 <= limit <= 201 or len(statement) > 8192:
            raise CollectorConditionStorageErrorV1()
        remaining = self.remaining()
        self._connection.set_authorizer(None)
        self._connection.execute(f"PRAGMA busy_timeout={remaining}").close()
        self._connection.set_authorizer(self.authorize)
        cursor = self._connection.execute(statement, parameters)
        try:
            result = tuple(cursor.fetchmany(limit))
            self.remaining()
            return result
        finally:
            cursor.close()

    def execute(self, statement: str, parameters: tuple[object, ...] = ()) -> None:
        self.rows(statement, parameters, limit=1)


@contextmanager
def _open_condition_writer(
    reference: DatabaseRefV1, deadline: datetime
) -> Iterator[_ConditionWriterV1]:
    offset = deadline.utcoffset()
    remaining = (deadline - datetime.now(UTC)).total_seconds()
    if offset is None or offset.total_seconds() != 0 or not 0 < remaining <= 2:
        raise CollectorConditionStorageErrorV1()
    end = time.monotonic() + remaining
    connection: sqlite3.Connection | None = None
    writer: _ConditionWriterV1 | None = None
    failed = False
    try:
        identity = reference.validate()
        timeout = max(0, (end - time.monotonic()))
        if timeout < 0.001:
            raise CollectorConditionStorageErrorV1()
        connection = sqlite3.connect(
            reference._path.as_uri() + "?mode=rw",
            uri=True,
            timeout=timeout,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 65536)
        connection.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 8192)
        writer = _ConditionWriterV1(connection, end)
        connection.set_progress_handler(lambda: int(time.monotonic() >= end), 100)
        for key, value in (
            ("foreign_keys", 1),
            ("synchronous", 2),
            ("read_uncommitted", 0),
            ("trusted_schema", 0),
        ):
            connection.execute(f"PRAGMA busy_timeout={writer.remaining()}").close()
            connection.execute(f"PRAGMA {key}={value}").close()
            cursor = connection.execute(f"PRAGMA {key}")
            try:
                row = cursor.fetchone()
                if row is None or row[0] != value:
                    raise CollectorConditionStorageErrorV1()
            finally:
                cursor.close()
        cursor = connection.execute("PRAGMA journal_mode")
        try:
            row = cursor.fetchone()
            if row is None or row[0] != "wal":
                raise CollectorConditionStorageErrorV1()
        finally:
            cursor.close()
        if reference.validate() != identity:
            raise CollectorConditionStorageErrorV1()
        writer.execute("BEGIN IMMEDIATE")
        yield writer
        writer.remaining()
        if reference.validate() != identity:
            raise CollectorConditionStorageErrorV1()
        writer.execute("COMMIT")
        writer.remaining()
    except (
        sqlite3.Error,
        SqlitePolicyError,
        CollectorConditionStorageErrorV1,
        OSError,
    ):
        failed = True
    finally:
        if connection is not None:
            try:
                connection.set_authorizer(None)
                connection.set_progress_handler(None, 0)
                if connection.in_transaction:
                    connection.rollback()
            except sqlite3.Error:
                failed = True
            finally:
                try:
                    connection.close()
                except sqlite3.Error:
                    failed = True
        if writer is not None:
            writer._closed = True
    if failed:
        raise CollectorConditionStorageErrorV1() from None

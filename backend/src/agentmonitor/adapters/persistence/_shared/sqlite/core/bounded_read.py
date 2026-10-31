"""Adapter-only bounded live reads; no executor or normal pool-policy change.

The deadline bounds SQLite busy/VM work on an approved local data root, not
kernel filesystem stalls or OS scheduling. SQLite may maintain shared-memory
bookkeeping; this connection cannot write database/WAL content or checkpoint.
"""

import re
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    _error_code,
)

_READ_PRAGMAS = frozenset(
    {
        "query_only",
        "foreign_keys",
        "journal_mode",
        "synchronous",
        "read_uncommitted",
        "trusted_schema",
        "busy_timeout",
        "schema_version",
    }
)
_TABLE_PRAGMAS = frozenset(
    {"table_info", "table_xinfo", "index_list", "index_xinfo", "foreign_key_list"}
)
_FUNCTIONS = frozenset(
    {
        "count",
        "sum",
        "min",
        "max",
        "coalesce",
        "abs",
        "length",
        "lower",
        "upper",
        "strftime",
        "julianday",
    }
)


@dataclass(slots=True)
class BoundedSqliteReadConnectionV1:
    """Caller-owned adapter SQL and rows stay inside persistence adapters."""

    _connection: sqlite3.Connection = field(repr=False)
    _end: float = field(repr=False)
    _allowed_tables: frozenset[str] = field(repr=False)
    _closed: bool = field(default=False, init=False, repr=False)
    _denied: bool = field(default=False, init=False, repr=False)

    def _remaining_ms(self) -> int:
        if self._closed:
            raise SqlitePolicyError("database_handle_closed") from None
        remaining = int((self._end - time.monotonic()) * 1000)
        if remaining < 1:
            raise SqlitePolicyError("database_timeout") from None
        return min(remaining, 2000)

    def _progress(self) -> int:
        return int(time.monotonic() >= self._end)

    def _authorize(
        self,
        action: int,
        first: str | None,
        second: str | None,
        database: str | None,
        source: str | None,
    ) -> int:
        allowed = False
        if action in {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_RECURSIVE}:
            allowed = True
        elif action == sqlite3.SQLITE_READ:
            # SQLite authorizes named schema columns as sqlite_master, while
            # count(*) can report sqlite_schema with an implicit database name.
            table = "sqlite_schema" if first == "sqlite_master" else first
            allowed = database in {None, "main"} and table in self._allowed_tables
        elif action == sqlite3.SQLITE_FUNCTION:
            allowed = second is not None and second.lower() in _FUNCTIONS
        elif action == sqlite3.SQLITE_PRAGMA and first is not None:
            key = first.lower()
            allowed = (key in _READ_PRAGMAS and second is None) or (
                key in _TABLE_PRAGMAS and second in self._allowed_tables
            )
        elif action == sqlite3.SQLITE_TRANSACTION:
            allowed = first in {"BEGIN", "ROLLBACK"}
        if not allowed:
            self._denied = True
        return sqlite3.SQLITE_OK if allowed else sqlite3.SQLITE_DENY

    def fetch_many(
        self, statement: str, parameters: tuple[object, ...] = (), *, limit: int
    ) -> tuple[tuple[object, ...], ...]:
        if type(limit) is not int or not 1 <= limit <= 513:
            raise SqlitePolicyError("database_read_limit_invalid") from None
        if not isinstance(statement, str) or len(statement) > 8192:
            raise SqlitePolicyError("database_read_statement_invalid") from None
        remaining = self._remaining_ms()
        self._denied = False
        cursor: sqlite3.Cursor | None = None
        failure: str | None = None
        result: tuple[tuple[object, ...], ...] = ()
        try:
            # Only the adapter's timeout setting bypasses its read authorizer.
            self._connection.set_authorizer(None)
            self._connection.execute(f"PRAGMA busy_timeout={remaining}").close()
            self._connection.set_authorizer(self._authorize)
            self._remaining_ms()
            cursor = self._connection.execute(statement, parameters)
            result = tuple(tuple(row) for row in cursor.fetchmany(limit))
            self._remaining_ms()
        except sqlite3.Error as error:
            if self._denied:
                failure = "persistence_read_only"
            elif (
                time.monotonic() >= self._end
                or getattr(error, "sqlite_errorcode", None) == sqlite3.SQLITE_INTERRUPT
            ):
                failure = "database_timeout"
            else:
                failure = _error_code(error)
        finally:
            if cursor is not None:
                cursor.close()
            self._connection.set_authorizer(self._authorize)
        if failure is not None:
            raise SqlitePolicyError(failure) from None
        return result

    def fetch_one(
        self, statement: str, parameters: tuple[object, ...] = ()
    ) -> tuple[object, ...] | None:
        rows = self.fetch_many(statement, parameters, limit=1)
        return rows[0] if rows else None


@contextmanager
def open_bounded_sqlite_read(
    database_ref: DatabaseRefV1, *, deadline: datetime, allowed_tables: frozenset[str]
) -> Iterator[BoundedSqliteReadConnectionV1]:
    offset = deadline.utcoffset()
    if offset is None or offset.total_seconds() != 0:
        raise SqlitePolicyError("database_deadline_invalid") from None
    remaining = (deadline - datetime.now(UTC)).total_seconds()
    if remaining <= 0:
        raise SqlitePolicyError("database_timeout") from None
    if (
        remaining > 2
        or not isinstance(allowed_tables, frozenset)
        or any(
            not re.fullmatch(r"[a-z][a-z0-9_]{0,127}", table)
            for table in allowed_tables
        )
    ):
        raise SqlitePolicyError("database_read_policy_invalid") from None
    end = time.monotonic() + remaining
    connection: sqlite3.Connection | None = None
    reader: BoundedSqliteReadConnectionV1 | None = None
    failure: str | None = None
    try:
        identity = database_ref.validate()
        budget = int((end - time.monotonic()) * 1000)
        if budget < 1:
            raise SqlitePolicyError("database_timeout")
        connection = sqlite3.connect(
            database_ref._path.as_uri() + "?mode=ro",
            uri=True,
            timeout=budget / 1000,
            isolation_level=None,
        )
        connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 65536)
        connection.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 8192)
        reader = BoundedSqliteReadConnectionV1(connection, end, allowed_tables)
        connection.set_progress_handler(reader._progress, 100)
        for name, expected in (
            ("query_only", 1),
            ("foreign_keys", 1),
            ("synchronous", 2),
            ("read_uncommitted", 0),
            ("trusted_schema", 0),
        ):
            budget = reader._remaining_ms()
            connection.execute(f"PRAGMA busy_timeout={budget}").close()
            connection.execute(f"PRAGMA {name}={expected}").close()
            cursor = connection.execute(f"PRAGMA {name}")
            try:
                if cursor.fetchone() != (expected,):
                    raise SqlitePolicyError("database_policy_incompatible")
            finally:
                cursor.close()
        if reader.fetch_one("PRAGMA journal_mode") != ("wal",):
            raise SqlitePolicyError("database_policy_incompatible")
        if database_ref.validate() != identity:
            raise SqlitePolicyError("database_identity_changed")
        reader.fetch_one("BEGIN")
        yield reader
        reader._remaining_ms()
        if database_ref.validate() != identity:
            raise SqlitePolicyError("database_identity_changed")
        reader._remaining_ms()
    except (SqlitePolicyError, sqlite3.Error, OSError) as error:
        if isinstance(error, sqlite3.Error) and time.monotonic() >= end:
            failure = "database_timeout"
        else:
            failure = _error_code(error)
    finally:
        if connection is not None:
            connection.set_authorizer(None)
            connection.set_progress_handler(None, 0)
            connection.close()
        if reader is not None:
            reader._closed = True
    if failure is not None:
        raise SqlitePolicyError(failure) from None

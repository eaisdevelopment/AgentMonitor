"""V1 file-backed SQLite policy. Paths and driver objects stay in this adapter.

Composition supplies one explicitly approved, existing owner-only data root.
Only migration_initialize creates an absent agentmonitor.db, exclusively, with
0600 permissions. Existing files/roots are checked, never silently repaired.
SQLite URI construction, PRAGMAs and result codes are dialect-local mechanisms;
future PostgreSQL adapters must provide equivalent isolation/durability semantics.
"""

import os
import sqlite3
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import Literal

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import DBAPIError, SQLAlchemyError, TimeoutError
from sqlalchemy.pool import QueuePool

DatabaseOpenModeV1 = Literal[
    "runtime_read_write",
    "runtime_read_only",
    "migration_initialize",
    "migration_existing",
]

_MODES = frozenset(
    {
        "runtime_read_write",
        "runtime_read_only",
        "migration_initialize",
        "migration_existing",
    }
)
_PRAGMAS: tuple[tuple[str, int | str], ...] = (
    ("foreign_keys", 1),
    ("journal_mode", "wal"),
    ("synchronous", 2),
    ("busy_timeout", 5000),
    ("read_uncommitted", 0),
    ("wal_autocheckpoint", 1000),
    ("trusted_schema", 0),
)


class SqlitePolicyError(ValueError):
    """A bounded code only; raw driver errors must never cross this boundary."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _error_code(error: BaseException) -> str:
    if isinstance(error, SqlitePolicyError):
        return error.code
    if isinstance(error, TimeoutError):
        return "persistence_busy"
    original = error.orig if isinstance(error, DBAPIError) else error
    code = getattr(original, "sqlite_errorcode", 0)
    primary = code & 0xFF if isinstance(code, int) else 0
    return {
        sqlite3.SQLITE_BUSY: "persistence_busy",
        sqlite3.SQLITE_LOCKED: "persistence_busy",
        sqlite3.SQLITE_READONLY: "persistence_read_only",
        sqlite3.SQLITE_CORRUPT: "persistence_corrupt",
        sqlite3.SQLITE_NOTADB: "persistence_corrupt",
        sqlite3.SQLITE_FULL: "persistence_space_exhausted",
        sqlite3.SQLITE_IOERR: "persistence_io_failure",
        sqlite3.SQLITE_CANTOPEN: "database_unreadable",
    }.get(primary, "persistence_unavailable")


@dataclass(frozen=True, slots=True)
class DatabaseRefV1:
    """Non-displayable adapter reference; caller approves this exact root."""

    _path: Path = field(repr=False)
    _approved_root: Path = field(repr=False)

    def __post_init__(self) -> None:
        for path in (self._path, self._approved_root):
            if (
                not isinstance(path, Path)
                or not path.is_absolute()
                or any(part in {"..", "."} for part in path.parts)
                or any(char in str(path) for char in "\x00$~*?[]:")
            ):
                raise SqlitePolicyError("database_reference_invalid") from None
        if (
            self._path.parent != self._approved_root
            or self._path.name != "agentmonitor.db"
        ):
            raise SqlitePolicyError("database_reference_invalid") from None
        if self._approved_root in {
            Path(self._approved_root.anchor),
            Path(__file__).resolve().parents[8],
            Path.home(),
        }:
            raise SqlitePolicyError("database_reference_invalid") from None

    def validate(self, *, missing_ok: bool = False) -> tuple[int, int] | None:
        """Check exact root, ancestor symlinks, files/sidecars and owner modes."""
        failure: str | None = None
        identity: tuple[int, int] | None = None
        try:
            for parent in (self._approved_root, *self._approved_root.parents):
                info = parent.lstat()
                if not stat.S_ISDIR(info.st_mode):
                    raise SqlitePolicyError("database_reference_unsafe")
                if info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX:
                    raise SqlitePolicyError("database_reference_unsafe")
            _check_owner(self._approved_root, directory=True)
            try:
                identity = _check_owner(self._path)
            except FileNotFoundError:
                if not missing_ok:
                    raise SqlitePolicyError("database_missing") from None
            for suffix in ("-wal", "-shm", "-journal"):
                try:
                    _check_owner(self._path.with_name(self._path.name + suffix))
                except FileNotFoundError:
                    pass
        except SqlitePolicyError as error:
            failure = error.code
        except (OSError, ValueError):
            failure = "database_unreadable"
        if failure is not None:
            raise SqlitePolicyError(failure) from None
        return identity


def _check_owner(path: Path, *, directory: bool = False) -> tuple[int, int]:
    info = path.lstat()
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected(info.st_mode) or (not directory and info.st_nlink != 1):
        raise SqlitePolicyError("database_reference_unsafe")
    if os.name == "posix":
        mode = 0o700 if directory else 0o600
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != mode:
            raise SqlitePolicyError("database_permissions_unsafe")
    return info.st_dev, info.st_ino


def _apply_policy(connection: sqlite3.Connection, *, read_only: bool) -> None:
    # PRAGMA names/values are a closed code-owned list; SQLite does not bind these.
    cursor = connection.cursor()
    try:
        for name, value in _PRAGMAS:
            if name != "journal_mode" or not read_only:
                cursor.execute(f"PRAGMA {name}={value}")
            cursor.execute(f"PRAGMA {name}")
            row = cursor.fetchone()
            if row is None or row[0] != value:
                raise SqlitePolicyError("database_policy_incompatible")
    finally:
        cursor.close()


@dataclass(slots=True)
class SqliteDatabaseHandleV1:
    """Adapter-only engine lifetime; connections never enter domain contracts."""

    _engine: Engine = field(repr=False)
    _closed: bool = field(default=False, init=False)
    _active: int = field(default=0, init=False, repr=False)

    @contextmanager
    def connect(self) -> Iterator[Connection]:
        if self._closed:
            raise SqlitePolicyError("database_handle_closed") from None
        failure: str | None = None
        self._active += 1
        try:
            with self._engine.connect() as connection:
                yield connection
        except (SqlitePolicyError, SQLAlchemyError, sqlite3.Error, OSError) as error:
            failure = _error_code(error)
        finally:
            self._active -= 1
        if failure is not None:
            raise SqlitePolicyError(failure) from None

    def close(self) -> None:
        if self._active:
            raise SqlitePolicyError("database_connections_active") from None
        self._engine.dispose()
        self._closed = True

    def __enter__(self) -> "SqliteDatabaseHandleV1":
        if self._closed:
            raise SqlitePolicyError("database_handle_closed") from None
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


def open_sqlite_database(
    database_ref: DatabaseRefV1, mode: DatabaseOpenModeV1
) -> SqliteDatabaseHandleV1:
    """Open explicit real file, enforcing policy before returning any handle.

    This low-level adapter factory does not grant writable schema readiness.
    Composition must inspect and require a writable receipt before service use.
    Failed initialization preserves its exact file for inspection/recovery.
    """
    if not isinstance(database_ref, DatabaseRefV1) or mode not in _MODES:
        raise SqlitePolicyError("database_reference_invalid") from None
    identity = database_ref.validate(missing_ok=mode == "migration_initialize")
    if mode == "migration_initialize":
        if identity is not None:
            raise SqlitePolicyError("database_already_exists") from None
        failure: str | None = None
        try:
            descriptor = os.open(
                database_ref._path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600
            )
            try:
                if os.name == "posix":
                    os.fchmod(descriptor, 0o600)
            finally:
                os.close(descriptor)
        except FileExistsError:
            failure = "database_already_exists"
        except OSError:
            failure = "database_unreadable"
        if failure is not None:
            raise SqlitePolicyError(failure) from None
        identity = database_ref.validate()

    read_only = mode == "runtime_read_only"

    def connect_driver() -> sqlite3.Connection:
        if database_ref.validate() != identity:
            raise SqlitePolicyError("database_identity_changed") from None
        connection = sqlite3.connect(
            database_ref._path.as_uri() + ("?mode=ro" if read_only else "?mode=rw"),
            uri=True,
            timeout=5,
            check_same_thread=False,
        )
        try:
            _apply_policy(connection, read_only=read_only)
            if database_ref.validate() != identity:
                raise SqlitePolicyError("database_identity_changed")
        except BaseException:
            connection.close()
            raise
        return connection

    engine = create_engine(
        "sqlite+pysqlite://",
        creator=connect_driver,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=0,
        pool_timeout=5,
        echo=False,
        hide_parameters=True,
    )

    def verify_checkout(driver: object, record: object, proxy: object) -> None:
        if not isinstance(driver, sqlite3.Connection):
            raise SqlitePolicyError("database_policy_incompatible")
        if database_ref.validate() != identity:
            raise SqlitePolicyError("database_identity_changed")
        _apply_policy(driver, read_only=read_only)

    event.listen(engine, "checkout", verify_checkout)
    handle = SqliteDatabaseHandleV1(engine)
    try:
        with handle.connect():
            pass
    except BaseException:
        handle.close()
        raise
    return handle

"""Bounded offline AgentMonitor v1_0603/v1_0707/v1_0708/v1_0709 to v1_0710 upgrade.

This operator command never starts/stops the service or restores a database.
It acts only on an explicitly selected owner-only data root and retains its
verified pre-migration backup and any failed database for separate recovery.
"""

# This operator script inserts the checkout's backend source path before imports.

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import sqlite3
import stat
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import ExitStack, closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import NoReturn

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Connection

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend/src"))

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
    open_sqlite_inspection,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    MIGRATIONS_PATH,
    InspectSchemaCompatibilityV1,
    MigrationCatalogV1,
    SchemaCompatibilityError,
    application_schema_range,
    load_migration_catalog,
)
from agentmonitor.adapters.persistence.runtime_observation.settings.repository import (
    OwnerAssociationSettingsRepositoryV1,
)
from agentmonitor.composition.iam_operator import (
    OperatorQuiescenceError,
    exclusive_service_quiescence,
)
from agentmonitor.modules.runtime_observation.application.ports import (
    OwnerAssociationErrorV1,
)

SOURCES = ("v1_0603", "v1_0707", "v1_0708", "v1_0709")
TARGET = "v1_0710"
SETTINGS = "owner-process-account-associations-v1.json"
SETTINGS_LOCK = ".owner-process-account-associations-v1.lock"
MAX_SETTINGS_BYTES = 1024 * 1024
MAX_LOCK_BYTES = 4096
MAX_MANIFEST_BYTES = 8192


class MigrationRefused(RuntimeError):
    def __init__(self, code: str, *, failed: bool = False) -> None:
        self.code = code
        self.failed = failed
        super().__init__(code)


def _refuse(code: str, *, failed: bool = False) -> NoReturn:
    raise MigrationRefused(code, failed=failed) from None


def _safe_directory(path: Path) -> tuple[int, int]:
    info = path.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o700
        or info.st_uid != os.getuid()
    ):
        _refuse("backup_root_unsafe")
    return info.st_dev, info.st_ino


def _backup_parent(root: Path) -> Path:
    parent = root / "backups"
    try:
        parent.mkdir(mode=0o700)
    except FileExistsError:
        pass
    _safe_directory(parent)
    _fsync_directory(root)
    return parent


@contextmanager
def _hold_settings_lock(root: Path) -> Iterator[None]:
    """Exclude the production M06 settings writer for the whole upgrade."""
    path = root / SETTINGS_LOCK
    try:
        (root / SETTINGS).lstat()
        settings_present = True
    except FileNotFoundError:
        settings_present = False
    try:
        path.lstat()
        lock_present = True
    except FileNotFoundError:
        lock_present = False
    if settings_present and not lock_present:
        _refuse("settings_lock_missing")
    descriptor = os.open(
        path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600
    )
    try:
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_uid != os.getuid()
            or info.st_nlink != 1
        ):
            _refuse("settings_lock_unsafe")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            _refuse("settings_lock_occupied")
        current = path.stat(follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
            _refuse("settings_lock_changed")
        yield
        current = path.stat(follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
            _refuse("settings_lock_changed", failed=True)
    finally:
        os.close(descriptor)


def _digest_file(path: Path, *, max_bytes: int | None = None) -> str:
    digest = hashlib.sha256()
    total = 0
    descriptor = os.open(
        path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
    )
    try:
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_uid != os.getuid()
            or info.st_nlink != 1
        ):
            _refuse("backup_object_unsafe")
        while chunk := os.read(descriptor, 1024 * 1024):
            total += len(chunk)
            if max_bytes is not None and total > max_bytes:
                _refuse("backup_object_oversize")
            digest.update(chunk)
        if os.fstat(descriptor).st_size != total:
            _refuse("backup_object_changed")
        return digest.hexdigest()
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _copy_metadata_file(root: Path, backup: Path, name: str, limit: int) -> str | None:
    source = root / name
    try:
        descriptor = os.open(
            source, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
        )
    except FileNotFoundError:
        return None
    try:
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_uid != os.getuid()
            or info.st_nlink != 1
            or info.st_size > limit
        ):
            _refuse("settings_unsafe")
        original = os.read(descriptor, limit + 1)
        if len(original) != info.st_size or len(original) > limit:
            _refuse("settings_changed")
        if name == SETTINGS:
            try:
                document = json.loads(original, object_pairs_hook=_closed_json_object)
            except (ValueError, UnicodeError):
                _refuse("settings_format_invalid")
            if (
                not isinstance(document, dict)
                or set(document) != {"format", "records"}
                or document["format"] != "owner-process-account-associations.v1"
                or not isinstance(document["records"], dict)
                or len(document["records"]) > 2048
            ):
                _refuse("settings_format_invalid")
        target = backup / name
        copy_fd = os.open(
            target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
        )
        try:
            with os.fdopen(copy_fd, "wb", closefd=False) as stream:
                stream.write(original)
                stream.flush()
            os.fsync(copy_fd)
        finally:
            os.close(copy_fd)
        digest = hashlib.sha256(original).hexdigest()
        if _digest_file(target, max_bytes=limit) != digest:
            _refuse("settings_copy_invalid")
        return digest
    finally:
        os.close(descriptor)


def _closed_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _verify_source_metadata(
    root: Path, digests: dict[str, str | None], *, failed: bool = False
) -> None:
    for name, expected in digests.items():
        source = root / name
        try:
            actual = _digest_file(
                source,
                max_bytes=MAX_SETTINGS_BYTES if name == SETTINGS else MAX_LOCK_BYTES,
            )
        except FileNotFoundError:
            actual = None
        if actual != expected:
            _refuse("settings_changed", failed=failed)


def _create_sqlite_backup(driver: sqlite3.Connection, target: Path) -> str:
    descriptor = os.open(
        target, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    os.close(descriptor)
    deadline = time.monotonic() + 120

    def progress(_status: int, _remaining: int, _total: int) -> None:
        if time.monotonic() >= deadline:
            _refuse("backup_timeout")

    with closing(sqlite3.connect(f"{target.as_uri()}?mode=rw", uri=True)) as copy:
        driver.backup(copy, pages=128, progress=progress, sleep=0.05)
    # SQLite backup closes its destination before the durable file flush.
    descriptor = os.open(target, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return _digest_file(target)


def _verify_sqlite_backup(
    backup_root: Path, catalog_digest: str, source_revision: str
) -> None:
    backup_ref = DatabaseRefV1(backup_root / "agentmonitor.db", backup_root)
    view = InspectSchemaCompatibilityV1(
        backup_ref, application_schema_range(), "runtime_read_write"
    )
    if (
        view.state != "upgrade_required"
        or view.current_revision != source_revision
        or view.integrity_state != "passed"
        or view.policy_state != "passed"
        or view.application_range.catalog_digest != catalog_digest
    ):
        _refuse("backup_schema_invalid")
    with open_sqlite_inspection(backup_ref) as connection:
        if connection.exec_driver_sql("PRAGMA integrity_check").scalars().fetchmany(
            2
        ) != ["ok"]:
            _refuse("backup_integrity_invalid")
        if connection.exec_driver_sql("PRAGMA foreign_key_check").first() is not None:
            _refuse("backup_foreign_keys_invalid")


def _write_manifest(
    backup: Path,
    *,
    catalog_digest: str,
    database_digest: str,
    settings_digests: dict[str, str | None],
    source_revision: str,
) -> None:
    manifest = {
        "format": "agentmonitor-m4-migration-preflight.v1",
        "backup_id": backup.name,
        "source_revision": source_revision,
        "target_revision": TARGET,
        "catalog_digest": catalog_digest,
        "database_sha256": database_digest,
        "settings_sha256": settings_digests[SETTINGS],
        "settings_lock_sha256": settings_digests[SETTINGS_LOCK],
        "completed_at": datetime.now(UTC).isoformat(),
    }
    encoded = (
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    if len(encoded) > MAX_MANIFEST_BYTES:
        _refuse("backup_manifest_invalid")
    path = backup / "manifest.json"
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(encoded)
            stream.flush()
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    if (
        _digest_file(path, max_bytes=MAX_MANIFEST_BYTES)
        != hashlib.sha256(encoded).hexdigest()
    ):
        _refuse("backup_manifest_invalid")
    _fsync_directory(backup)
    _fsync_directory(backup.parent)


def _marker(connection: Connection) -> str:
    rows = (
        connection.exec_driver_sql("SELECT version_num FROM alembic_version LIMIT 2")
        .scalars()
        .all()
    )
    if len(rows) != 1 or not isinstance(rows[0], str):
        _refuse("source_revision_invalid")
    return rows[0]


def _preflight_catalog(source: str) -> tuple[MigrationCatalogV1, tuple[str, ...]]:
    catalog = load_migration_catalog()
    revisions = [item.revision for item in catalog.revisions]
    if catalog.head != TARGET or source not in SOURCES or revisions[-1] != TARGET:
        _refuse("migration_catalog_not_m4")
    tail = catalog.revisions[revisions.index(source) + 1 :]
    expected_tail = (
        (*tuple(f"v1_070{index}" for index in range(10)), "v1_0710")
        if source == "v1_0603"
        else ("v1_0708", "v1_0709", "v1_0710")
        if source == "v1_0707"
        else ("v1_0709", "v1_0710")
        if source == "v1_0708"
        else ("v1_0710",)
    )
    if tuple(item.revision for item in tail) != expected_tail or any(
        item.backup_prerequisite != "required_existing_database"
        or item.downtime_policy != "offline_additive_schema_migration"
        for item in tail
    ):
        _refuse("migration_chain_not_m4")
    return catalog, tuple(item.revision for item in tail)


def run_upgrade(root: Path, source: str) -> tuple[str, str | None]:
    catalog, revisions = _preflight_catalog(source)
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    reference.validate()
    backup_id: str | None = None
    with exclusive_service_quiescence(root, reference), ExitStack() as settings_guard:
        identity = reference.validate()
        with (
            open_sqlite_database(reference, "migration_existing") as handle,
            handle.connect() as connection,
        ):
            current = _marker(connection)
            if current == TARGET:
                connection.commit()
                # Exact schema validation follows after the connection closes.
                outcome = "already_current"
            elif current != source:
                _refuse("source_revision_not_m4")
            else:
                settings_guard.enter_context(_hold_settings_lock(root))
                driver = connection.connection.driver_connection
                if not isinstance(driver, sqlite3.Connection):
                    _refuse("database_driver_invalid")
                original_version = connection.exec_driver_sql(
                    "PRAGMA data_version"
                ).scalar_one()
                database_bytes = (root / "agentmonitor.db").stat().st_size
                wal = root / "agentmonitor.db-wal"
                try:
                    wal_info = wal.stat(follow_symlinks=False)
                except FileNotFoundError:
                    wal_info = None
                if wal_info is not None:
                    if (
                        not stat.S_ISREG(wal_info.st_mode)
                        or stat.S_IMODE(wal_info.st_mode) != 0o600
                        or wal_info.st_uid != os.getuid()
                        or wal_info.st_nlink != 1
                    ):
                        _refuse("database_sidecar_unsafe")
                    database_bytes += wal_info.st_size
                space = os.statvfs(root)
                if space.f_bavail * space.f_frsize < max(
                    16 * 1024 * 1024, database_bytes * 3
                ):
                    _refuse("backup_space_insufficient")
                backup_parent = _backup_parent(root)
                backup = Path(
                    tempfile.mkdtemp(prefix="migration-preflight-", dir=backup_parent)
                )
                _safe_directory(backup)
                backup_id = backup.name
                digest = _create_sqlite_backup(driver, backup / "agentmonitor.db")
                settings_digests = {
                    SETTINGS: _copy_metadata_file(
                        root, backup, SETTINGS, MAX_SETTINGS_BYTES
                    ),
                    SETTINGS_LOCK: _copy_metadata_file(
                        root, backup, SETTINGS_LOCK, MAX_LOCK_BYTES
                    ),
                }
                if (
                    settings_digests[SETTINGS] is not None
                    and settings_digests[SETTINGS_LOCK] is None
                ):
                    _refuse("settings_lock_missing")
                if settings_digests[SETTINGS] is not None:
                    try:
                        OwnerAssociationSettingsRepositoryV1(backup).records()
                    except OwnerAssociationErrorV1:
                        _refuse("settings_format_invalid")
                _verify_sqlite_backup(backup, catalog.digest, source)
                _write_manifest(
                    backup,
                    catalog_digest=catalog.digest,
                    database_digest=digest,
                    settings_digests=settings_digests,
                    source_revision=source,
                )
                _verify_source_metadata(root, settings_digests)
                if (
                    reference.validate() != identity
                    or connection.exec_driver_sql("PRAGMA data_version").scalar_one()
                    != original_version
                ):
                    _refuse("source_changed_after_backup")
                connection.commit()
                connection.exec_driver_sql("BEGIN IMMEDIATE")
                if (
                    reference.validate() != identity
                    or connection.exec_driver_sql("PRAGMA data_version").scalar_one()
                    != original_version
                    or _marker(connection) != source
                ):
                    _refuse("source_changed_after_backup")
                config = Config()
                config.set_main_option(
                    "script_location", str(MIGRATIONS_PATH).replace("%", "%%")
                )
                config.attributes.update(
                    connection=connection,
                    migrations_path=MIGRATIONS_PATH,
                    catalog_digest=catalog.digest,
                )
                try:
                    for revision in revisions:
                        if not driver.in_transaction:
                            _refuse("migration_lock_lost", failed=True)
                        command.upgrade(config, revision)
                        if not driver.in_transaction or _marker(connection) != revision:
                            _refuse("migration_marker_mismatch", failed=True)
                    if connection.exec_driver_sql(
                        "PRAGMA integrity_check"
                    ).scalars().fetchmany(2) != ["ok"]:
                        _refuse("migration_integrity_failed", failed=True)
                    if (
                        connection.exec_driver_sql("PRAGMA foreign_key_check").first()
                        is not None
                    ):
                        _refuse("migration_foreign_keys_failed", failed=True)
                    connection.commit()
                except BaseException:
                    connection.rollback()
                    raise
                outcome = "upgraded"
        view = InspectSchemaCompatibilityV1(
            reference, application_schema_range(), "runtime_read_write"
        )
        if (
            view.state != "compatible"
            or view.current_revision != TARGET
            or view.integrity_state != "passed"
            or view.policy_state != "passed"
        ):
            _refuse("target_schema_invalid", failed=True)
        if backup_id is not None:
            backup = root / "backups" / backup_id
            if _digest_file(backup / "agentmonitor.db") != digest:
                _refuse("backup_changed", failed=True)
            _verify_source_metadata(root, settings_digests, failed=True)
    return outcome, backup_id


def main() -> int:
    selected = os.environ.get("AGENTMONITOR_MIGRATE_DATA_ROOT")
    expected = os.environ.get("AGENTMONITOR_MIGRATE_EXPECTED_HEAD")
    if not selected or not Path(selected).is_absolute() or expected not in SOURCES:
        print(
            "AUTO-MIGRATE: BLOCKED — explicit supported source/expected head required"
        )
        return 3
    try:
        outcome, backup_id = run_upgrade(Path(selected), expected)
    except MigrationRefused as error:
        state = "FAILED" if error.failed else "BLOCKED"
        print(f"AUTO-MIGRATE: {state} — {error.code}")
        return 2 if error.failed else 3
    except (OperatorQuiescenceError, SchemaCompatibilityError, SqlitePolicyError):
        print("AUTO-MIGRATE: BLOCKED — target_or_catalog_unavailable")
        return 3
    except (OSError, sqlite3.Error, ValueError):
        print("AUTO-MIGRATE: FAILED — migration_or_backup_unavailable")
        return 2
    except Exception:  # noqa: BLE001 -- sanitize Alembic/driver exceptions at CLI.
        print("AUTO-MIGRATE: FAILED — migration_unavailable")
        return 2
    if outcome == "already_current":
        print(f"AUTO-MIGRATE: PASSED — already at {TARGET}; no schema change")
    else:
        print(
            f"AUTO-MIGRATE: PASSED — {expected} to {TARGET}, "
            f"verified backup {backup_id}; service activation Not Run"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Candidate staged SQLite restore; no public CLI or service selection."""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import re
import sqlite3
import stat
import tempfile
from contextlib import closing
from dataclasses import asdict
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    InspectSchemaCompatibilityV1,
    application_schema_range,
    load_migration_catalog,
)
from agentmonitor.composition.iam_operator import ServiceQuiescenceLeaseV1

from tools.automation.implementations.auto_migrate import (
    MAX_MANIFEST_BYTES,
    SETTINGS,
    SETTINGS_LOCK,
    _create_sqlite_backup,
    _digest_file,
    _preflight_catalog,
    _safe_directory,
    _SettingsLockLeaseV1,
    _verify_source_metadata,
    _verify_sqlite_backup,
)
from tools.automation.implementations.m6_quiescent_stop import (
    QuiescentStopReceipt,
    _properties,
)
from tools.automation.implementations.m6_transition_lease import _TransitionLease


class OfflineRestoreError(RuntimeError):
    """A bounded safe restore refusal."""


def _read_private_json(path: Path) -> dict:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.getuid()
            or before.st_mode & 0o077
            or before.st_nlink != 1
        ):
            raise OfflineRestoreError("restore_object_unsafe")
        content = b""
        while len(content) <= MAX_MANIFEST_BYTES:
            part = os.read(fd, min(4096, MAX_MANIFEST_BYTES + 1 - len(content)))
            if not part:
                break
            content += part
        after = os.fstat(fd)
        if (
            len(content) > MAX_MANIFEST_BYTES
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            or len(content) != before.st_size
        ):
            raise OfflineRestoreError("restore_object_changed")

        def unique_pairs(pairs: list[tuple[str, object]]) -> dict:
            result = {}
            for key, value in pairs:
                if key in result:
                    raise OfflineRestoreError("restore_object_duplicate_key")
                result[key] = value
            return result

        document = json.loads(content, object_pairs_hook=unique_pairs)
        if not isinstance(document, dict):
            raise OfflineRestoreError("restore_object_invalid")
        return document
    finally:
        os.close(fd)


def _journal_matches(path: Path, backup_id: str, receipt: QuiescentStopReceipt) -> bool:
    data = _read_private_json(path)
    return (
        data.get("format") == "m6-cutover.v1"
        and data.get("phase") == "migrated"
        and data.get("backup_id") == backup_id
        and data.get("stop_receipt") == json.loads(json.dumps(asdict(receipt)))
    )


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _fd_digest(fd: int) -> str:
    digest = hashlib.sha256()
    os.lseek(fd, 0, os.SEEK_SET)
    while True:
        data = os.read(fd, 1024 * 1024)
        if not data:
            break
        digest.update(data)
    return digest.hexdigest()


def _write_journal(path: Path, document: dict) -> None:
    raw = json.dumps(document, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    if len(raw) > MAX_MANIFEST_BYTES:
        raise OfflineRestoreError("restore_journal_invalid")
    temporary = path.with_name(path.name + ".restore-next")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(raw)
            stream.flush()
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temporary, path)
    _fsync_dir(path.parent)


def _ensure_cgroup_empty(stopped_cgroup: str) -> None:
    group_path = Path("/sys/fs/cgroup") / stopped_cgroup.lstrip("/")
    if (
        not stopped_cgroup.startswith("/user.slice/")
        or ".." in Path(stopped_cgroup).parts
    ):
        raise OfflineRestoreError("restore_cgroup_invalid")
    if group_path.exists():
        for directory, child_dirs, files in os.walk(group_path, followlinks=False):
            if any((Path(directory) / child).is_symlink() for child in child_dirs):
                raise OfflineRestoreError("restore_cgroup_invalid")
            if (
                "cgroup.procs" not in files
                or (Path(directory) / "cgroup.procs").read_text().strip()
            ):
                raise OfflineRestoreError("restore_cgroup_not_empty")


def classify_restore_recovery(root: Path, journal: Path) -> str:
    """Classify a retained prepared/activated journal without exchanging again."""
    try:
        if journal != root / ".m6-cutover-journal.json":
            raise OfflineRestoreError("restore_recovery_journal_invalid")
        data = _read_private_json(journal)
        expected_keys = {
            "format",
            "phase",
            "backup_id",
            "generation",
            "active_identity",
            "staged_identity",
            "preserved_identity",
            "active_sha256",
            "staged_sha256",
            "preserved_sha256",
            "source_revision",
            "stop_receipt",
            "cutover_facts",
        }
        if (
            set(data) != expected_keys
            or any(
                not isinstance(data.get(key), list)
                or len(data[key]) != 2
                or any(type(part) is not int or part < 0 for part in data[key])
                for key in ("active_identity", "staged_identity", "preserved_identity")
            )
            or any(
                re.fullmatch(r"[a-f0-9]{64}", str(data.get(key))) is None
                for key in ("active_sha256", "staged_sha256", "preserved_sha256")
            )
        ):
            raise OfflineRestoreError("restore_recovery_journal_invalid")
        receipt = data.get("stop_receipt")
        original = data.get("cutover_facts")
        if (
            not isinstance(original, dict)
            or original.get("format") != "m6-cutover.v1"
            or original.get("phase") != "migrated"
            or original.get("backup_id") != data.get("backup_id")
            or original.get("stop_receipt") != receipt
            or original.get("source_revision") != data.get("source_revision")
        ):
            raise OfflineRestoreError("restore_recovery_journal_invalid")
        receipt_keys = {
            "unit",
            "pid",
            "cgroup",
            "start_ticks",
            "executable_identity",
            "invocation_id",
            "start_monotonic",
        }
        if (
            not isinstance(receipt, dict)
            or set(receipt) != receipt_keys
            or type(receipt.get("pid")) is not int
            or receipt["pid"] <= 0
            or not isinstance(receipt.get("executable_identity"), list)
            or len(receipt["executable_identity"]) != 2
            or any(type(v) is not int or v < 0 for v in receipt["executable_identity"])
            or any(
                not isinstance(receipt.get(k), str)
                for k in (
                    "unit",
                    "cgroup",
                    "start_ticks",
                    "invocation_id",
                    "start_monotonic",
                )
            )
            or re.fullmatch(r"[A-Za-z0-9_.@:-]+\.service", receipt["unit"]) is None
            or not receipt["cgroup"].startswith("/user.slice/")
            or ".." in Path(receipt["cgroup"]).parts
            or not receipt["start_ticks"].isdigit()
            or not receipt["start_monotonic"].isdigit()
            or re.fullmatch(r"[a-f0-9]{32}", receipt["invocation_id"]) is None
            or not isinstance(data.get("backup_id"), str)
            or re.fullmatch(r"migration-preflight-[a-f0-9]{32}", data["backup_id"])
            is None
            or not isinstance(data.get("source_revision"), str)
        ):
            raise OfflineRestoreError("restore_recovery_journal_invalid")
        _preflight_catalog(data["source_revision"])
        _ensure_cgroup_empty(receipt["cgroup"])
        current = _properties(receipt["unit"])
        if (
            current.get("MainPID") != "0"
            or current.get("ActiveState") not in {"failed", "inactive"}
            or current.get("RefuseManualStart") != "yes"
            or current.get("Restart") != "no"
            or current.get("InvocationID") != receipt["invocation_id"]
            or current.get("ExecMainStartTimestampMonotonic")
            != receipt["start_monotonic"]
        ):
            raise OfflineRestoreError("restore_service_not_blocked")
        generation_name = data["generation"]
        if (
            data.get("format") != "m6-cutover.v1"
            or data.get("phase") not in {"restore_prepared", "restore_activated"}
            or re.fullmatch(r"m6-restore-[A-Za-z0-9_-]+", generation_name) is None
        ):
            raise OfflineRestoreError("restore_recovery_journal_invalid")
        generation = root / "restore-generations" / generation_name
        _safe_directory(root / "restore-generations")
        _safe_directory(generation)
        _safe_directory(generation / "restored")
        _safe_directory(generation / "preserved")
        restored = generation / "restored" / "agentmonitor.db"
        preserved = generation / "preserved" / "agentmonitor.db"
        preserved_info = preserved.stat()
        if (
            _digest_file(preserved) != data["preserved_sha256"]
            or [preserved_info.st_dev, preserved_info.st_ino]
            != data["preserved_identity"]
        ):
            raise OfflineRestoreError("restore_recovery_generation_changed")
        active = DatabaseRefV1(root / "agentmonitor.db", root).validate()
        active_digest = _digest_file(root / "agentmonitor.db")
        other_digest = _digest_file(restored)
        other = restored.stat()
        counterpart = [other.st_dev, other.st_ino]
        if (
            data["phase"] == "restore_prepared"
            and list(active) == data["active_identity"]
            and counterpart == data["staged_identity"]
            and active_digest == data["active_sha256"]
            and other_digest == data["staged_sha256"]
        ):
            return "prepared_not_activated"
        if (
            list(active) == data["staged_identity"]
            and counterpart == data["active_identity"]
            and active_digest == data["staged_sha256"]
            and other_digest == data["active_sha256"]
        ):
            return (
                "activated"
                if data["phase"] == "restore_activated"
                else "activated_unconfirmed"
            )
        raise OfflineRestoreError("restore_recovery_generation_changed")
    except OfflineRestoreError:
        raise
    except Exception:  # noqa: BLE001 -- sanitize filesystem and receipt failures.
        raise OfflineRestoreError("restore_recovery_unavailable") from None


def resume_prepared_restore(
    root: Path,
    *,
    transition_lease: _TransitionLease,
    service_lease: ServiceQuiescenceLeaseV1,
    settings_lease: _SettingsLockLeaseV1,
) -> str:
    """Finish a durably recorded exchange once, with both live locks held.

    This does not start a service, remove its start block, or decide whether a
    candidate may have run. The validated restore journal is the only input.
    """
    try:
        journal = root / ".m6-cutover-journal.json"
        transition_lease.validate(root)
        service_lease.validate(root)
        settings_lease.validate(root)
        data = _read_private_json(journal)
        phase = classify_restore_recovery(root, journal)
        if phase == "activated":
            reference = DatabaseRefV1(root / "agentmonitor.db", root)
            view = InspectSchemaCompatibilityV1(
                reference, application_schema_range(), "runtime_read_write"
            )
            if (
                view.current_revision != data["source_revision"]
                or view.state != "upgrade_required"
            ):
                raise OfflineRestoreError("restore_revision_invalid")
            transition_lease.validate(root)
            service_lease.validate(root)
            settings_lease.validate(root)
            if (
                _read_private_json(journal) != data
                or classify_restore_recovery(root, journal) != "activated"
            ):
                raise OfflineRestoreError("restore_recovery_changed")
            return "already_activated"
        if phase == "prepared_not_activated":
            restored = (
                root
                / "restore-generations"
                / data["generation"]
                / "restored"
                / "agentmonitor.db"
            )
            transition_lease.validate(root)
            service_lease.validate(root)
            settings_lease.validate(root)
            if (
                _read_private_json(journal) != data
                or classify_restore_recovery(root, journal) != phase
            ):
                raise OfflineRestoreError("restore_recovery_changed")
            _exchange(root / "agentmonitor.db", restored)
            _fsync_dir(root)
            _fsync_dir(restored.parent)
        if classify_restore_recovery(root, journal) != "activated_unconfirmed":
            raise OfflineRestoreError("restore_recovery_changed")
        # The previous process may have died after rename but before either
        # directory fsync; make the exchange durable before recording success.
        restored = (
            root
            / "restore-generations"
            / data["generation"]
            / "restored"
            / "agentmonitor.db"
        )
        _fsync_dir(root)
        _fsync_dir(restored.parent)
        reference = DatabaseRefV1(root / "agentmonitor.db", root)
        view = InspectSchemaCompatibilityV1(
            reference, application_schema_range(), "runtime_read_write"
        )
        if (
            view.current_revision != data["source_revision"]
            or view.state != "upgrade_required"
        ):
            raise OfflineRestoreError("restore_revision_invalid")
        transition_lease.validate(root)
        service_lease.validate(root)
        settings_lease.validate(root)
        if (
            _read_private_json(journal) != data
            or classify_restore_recovery(root, journal) != "activated_unconfirmed"
        ):
            raise OfflineRestoreError("restore_recovery_changed")
        data["phase"] = "restore_activated"
        _write_journal(journal, data)
        transition_lease.validate(root)
        service_lease.validate(root)
        settings_lease.validate(root)
        if (
            _read_private_json(journal) != data
            or classify_restore_recovery(root, journal) != "activated"
        ):
            raise OfflineRestoreError("restore_recovery_changed")
        return "activated"
    except OfflineRestoreError:
        raise
    except Exception:  # noqa: BLE001 -- sanitize recovery boundary failures.
        raise OfflineRestoreError("restore_recovery_unavailable") from None


def _exchange(first: Path, second: Path) -> None:
    """Atomic same-filesystem exchange, preserving both inode generations."""
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = libc.renameat2
    renameat2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    renameat2.restype = ctypes.c_int
    if renameat2(-100, os.fsencode(first), -100, os.fsencode(second), 2) != 0:
        raise OfflineRestoreError("restore_exchange_unavailable")


def restore_before_candidate_start(
    root: Path,
    backup_id: str,
    *,
    receipt: QuiescentStopReceipt,
    journal: Path,
    transition_lease: _TransitionLease,
    service_lease: ServiceQuiescenceLeaseV1,
    settings_lease: _SettingsLockLeaseV1,
) -> str:
    """Stage and validate both SQLite generations before atomic activation.

    The caller holds the outer deployment lock, and must enforce the durable
    start boundary. No public CLI; not yet a full CTR-DB-003 implementation.
    """
    if re.fullmatch(r"migration-preflight-[a-f0-9]{32}", backup_id) is None:
        raise OfflineRestoreError("restore_precondition_invalid")
    if journal != root / ".m6-cutover-journal.json" or not _journal_matches(
        journal, backup_id, receipt
    ):
        raise OfflineRestoreError("restore_journal_invalid")
    unit = receipt.unit
    stopped_cgroup = receipt.cgroup
    current = _properties(unit)
    if (
        current.get("MainPID") != "0"
        or current.get("ActiveState") not in {"failed", "inactive"}
        or current.get("RefuseManualStart") != "yes"
        or current.get("Restart") != "no"
        or current.get("InvocationID") != receipt.invocation_id
        or current.get("ExecMainStartTimestampMonotonic") != receipt.start_monotonic
    ):
        raise OfflineRestoreError("restore_service_not_blocked")
    _ensure_cgroup_empty(stopped_cgroup)
    backup_parent = root / "backups"
    backup = backup_parent / backup_id
    try:
        _safe_directory(backup_parent)
        _safe_directory(backup)
        manifest_path = backup / "manifest.json"
        manifest = _read_private_json(manifest_path)
        if (
            manifest.get("format") != "agentmonitor-m4-migration-preflight.v1"
            or manifest.get("backup_id") != backup_id
            or manifest.get("catalog_digest") != load_migration_catalog().digest
            or _digest_file(backup / "agentmonitor.db")
            != manifest.get("database_sha256")
        ):
            raise OfflineRestoreError("restore_backup_invalid")
        source = manifest["source_revision"]
        catalog = load_migration_catalog()
        _preflight_catalog(source)
        if manifest.get("target_revision") != catalog.head:
            raise OfflineRestoreError("restore_backup_invalid")
        _verify_sqlite_backup(backup, load_migration_catalog().digest, source)
        reference = DatabaseRefV1(root / "agentmonitor.db", root)
        transition_lease.validate(root)
        service_lease.validate(root)
        settings_lease.validate(root)
        if _properties(unit) != current or not _journal_matches(
            journal, backup_id, receipt
        ):
            raise OfflineRestoreError("restore_service_changed")
        _verify_source_metadata(
            root,
            {
                SETTINGS: manifest.get("settings_sha256"),
                SETTINGS_LOCK: manifest.get("settings_lock_sha256"),
            },
        )
        generations = root / "restore-generations"
        try:
            generations.mkdir(mode=0o700)
        except FileExistsError:
            pass
        _safe_directory(generations)
        generation = Path(tempfile.mkdtemp(prefix="m6-restore-", dir=generations))
        preserved_dir, restored_dir = (
            generation / "preserved",
            generation / "restored",
        )
        preserved_dir.mkdir(mode=0o700)
        restored_dir.mkdir(mode=0o700)
        backup_fd = os.open(backup / "agentmonitor.db", os.O_RDONLY | os.O_NOFOLLOW)
        try:
            backup_info = os.fstat(backup_fd)
            if (
                not stat.S_ISREG(backup_info.st_mode)
                or backup_info.st_uid != os.getuid()
                or backup_info.st_mode & 0o077
                or _fd_digest(backup_fd) != manifest.get("database_sha256")
            ):
                raise OfflineRestoreError("restore_backup_invalid")
            with closing(
                sqlite3.connect(
                    f"file:/proc/self/fd/{backup_fd}?mode=ro&immutable=1", uri=True
                )
            ) as source_db:
                _create_sqlite_backup(source_db, restored_dir / "agentmonitor.db")
            if _fd_digest(backup_fd) != manifest.get("database_sha256"):
                raise OfflineRestoreError("restore_backup_changed")
        finally:
            os.close(backup_fd)
        _verify_sqlite_backup(restored_dir, load_migration_catalog().digest, source)
        if _digest_file(restored_dir / "agentmonitor.db") != manifest.get(
            "database_sha256"
        ):
            raise OfflineRestoreError("restore_copy_mismatch")
        with (
            open_sqlite_database(reference, "migration_existing") as handle,
            handle.connect() as connection,
        ):
            target = connection.connection.driver_connection
            if not isinstance(target, sqlite3.Connection):
                raise OfflineRestoreError("restore_driver_invalid")
            _create_sqlite_backup(target, preserved_dir / "agentmonitor.db")
            result = target.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            if result is None or result[0] != 0:
                raise OfflineRestoreError("restore_checkpoint_busy")
        preserved_ref = DatabaseRefV1(preserved_dir / "agentmonitor.db", preserved_dir)
        preserved_view = InspectSchemaCompatibilityV1(
            preserved_ref, application_schema_range(), "runtime_read_write"
        )
        if (
            preserved_view.state != "compatible"
            or preserved_view.integrity_state != "passed"
        ):
            raise OfflineRestoreError("restore_preserved_invalid")
        for sidecar in (
            root / "agentmonitor.db-wal",
            root / "agentmonitor.db-shm",
            root / "agentmonitor.db-journal",
        ):
            if sidecar.exists() or sidecar.is_symlink():
                raise OfflineRestoreError("restore_sidecar_present")
        if (
            _properties(unit) != current
            or not _journal_matches(journal, backup_id, receipt)
            or _digest_file(backup / "agentmonitor.db")
            != manifest.get("database_sha256")
        ):
            raise OfflineRestoreError("restore_boundary_changed")
        active_identity = reference.validate()
        staged_info = (restored_dir / "agentmonitor.db").stat()
        preserved_info = (preserved_dir / "agentmonitor.db").stat()
        if active_identity is None or staged_info.st_dev != active_identity[0]:
            raise OfflineRestoreError("restore_generation_invalid")
        cutover_facts = _read_private_json(journal)
        if (
            not _journal_matches(journal, backup_id, receipt)
            or cutover_facts.get("source_revision") != source
        ):
            raise OfflineRestoreError("restore_journal_changed")
        prepared = {
            "format": "m6-cutover.v1",
            "phase": "restore_prepared",
            "backup_id": backup_id,
            "generation": generation.name,
            "active_identity": list(active_identity),
            "staged_identity": [staged_info.st_dev, staged_info.st_ino],
            "preserved_identity": [preserved_info.st_dev, preserved_info.st_ino],
            "active_sha256": _digest_file(root / "agentmonitor.db"),
            "staged_sha256": _digest_file(restored_dir / "agentmonitor.db"),
            "preserved_sha256": _digest_file(preserved_dir / "agentmonitor.db"),
            "source_revision": source,
            "stop_receipt": asdict(receipt),
            "cutover_facts": cutover_facts,
        }
        # Persist both generations before publishing the recoverable journal.
        _fsync_dir(preserved_dir)
        _fsync_dir(restored_dir)
        _fsync_dir(generation)
        _fsync_dir(generations)
        _write_journal(journal, prepared)
        if _read_private_json(journal) != json.loads(json.dumps(prepared)):
            raise OfflineRestoreError("restore_journal_changed")
        transition_lease.validate(root)
        service_lease.validate(root)
        settings_lease.validate(root)
        if (
            reference.validate() != active_identity
            or _digest_file(root / "agentmonitor.db") != prepared["active_sha256"]
            or (
                (restored_dir / "agentmonitor.db").stat().st_dev,
                (restored_dir / "agentmonitor.db").stat().st_ino,
            )
            != (staged_info.st_dev, staged_info.st_ino)
            or (
                (preserved_dir / "agentmonitor.db").stat().st_dev,
                (preserved_dir / "agentmonitor.db").stat().st_ino,
            )
            != (preserved_info.st_dev, preserved_info.st_ino)
            or _digest_file(restored_dir / "agentmonitor.db")
            != prepared["staged_sha256"]
            or _digest_file(preserved_dir / "agentmonitor.db")
            != prepared["preserved_sha256"]
            or _properties(unit) != current
        ):
            raise OfflineRestoreError("restore_boundary_changed")
        _exchange(root / "agentmonitor.db", restored_dir / "agentmonitor.db")
        _fsync_dir(root)
        _fsync_dir(restored_dir)
        retained = (restored_dir / "agentmonitor.db").stat()
        retained_preserved = (preserved_dir / "agentmonitor.db").stat()
        if (
            reference.validate() != (staged_info.st_dev, staged_info.st_ino)
            or (retained.st_dev, retained.st_ino) != active_identity
            or (retained_preserved.st_dev, retained_preserved.st_ino)
            != (preserved_info.st_dev, preserved_info.st_ino)
            or _digest_file(root / "agentmonitor.db") != prepared["staged_sha256"]
            or _digest_file(restored_dir / "agentmonitor.db")
            != prepared["active_sha256"]
            or _digest_file(preserved_dir / "agentmonitor.db")
            != prepared["preserved_sha256"]
            or _properties(unit) != current
        ):
            raise OfflineRestoreError("restore_activation_unverified")
        view = InspectSchemaCompatibilityV1(
            reference, application_schema_range(), "runtime_read_write"
        )
        if view.current_revision != source or view.state != "upgrade_required":
            raise OfflineRestoreError("restore_revision_invalid")
        transition_lease.validate(root)
        service_lease.validate(root)
        settings_lease.validate(root)
        retained = (restored_dir / "agentmonitor.db").stat()
        retained_preserved = (preserved_dir / "agentmonitor.db").stat()
        if (
            reference.validate() != (staged_info.st_dev, staged_info.st_ino)
            or (retained.st_dev, retained.st_ino) != active_identity
            or (retained_preserved.st_dev, retained_preserved.st_ino)
            != (preserved_info.st_dev, preserved_info.st_ino)
            or _digest_file(root / "agentmonitor.db") != prepared["staged_sha256"]
            or _digest_file(restored_dir / "agentmonitor.db")
            != prepared["active_sha256"]
            or _digest_file(preserved_dir / "agentmonitor.db")
            != prepared["preserved_sha256"]
            or _properties(unit) != current
        ):
            raise OfflineRestoreError("restore_activation_unverified")
        if _read_private_json(journal) != json.loads(json.dumps(prepared)):
            raise OfflineRestoreError("restore_journal_changed")
        prepared["phase"] = "restore_activated"
        _write_journal(journal, prepared)
        return "restored"
    except OfflineRestoreError:
        raise
    except Exception:  # noqa: BLE001 -- sanitize persistence boundary failures.
        raise OfflineRestoreError("restore_unavailable") from None

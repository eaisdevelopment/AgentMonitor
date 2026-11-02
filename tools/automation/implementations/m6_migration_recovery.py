"""Recover a stopped M6 migration without starting a dashboard service."""

from __future__ import annotations

import ctypes
import os
import re
import secrets
import stat
from collections.abc import Callable
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    checkpoint_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    InspectSchemaCompatibilityV1,
    application_schema_range,
    load_migration_catalog,
)
from agentmonitor.composition.iam_operator import ServiceQuiescenceLeaseV1

from tools.automation.implementations.auto_migrate import (
    SETTINGS,
    SETTINGS_LOCK,
    _digest_file,
    _preflight_catalog,
    _safe_directory,
    _SettingsLockLeaseV1,
    _verify_source_metadata,
    _verify_sqlite_backup,
    run_upgrade,
)
from tools.automation.implementations.m6_offline_restore import (
    _ensure_cgroup_empty,
    _read_private_json,
)
from tools.automation.implementations.m6_quiescent_stop import (
    QuiescentStopReceipt,
    _properties,
)
from tools.automation.implementations.m6_transition_journal import (
    _read_journal_at,
    _replace_journal,
)
from tools.automation.implementations.m6_transition_lease import _TransitionLease


class MigrationRecoveryError(RuntimeError):
    """Fail-closed recovery refusal without user records."""


def _preserve_interrupted_journal(transition: _TransitionLease) -> None:
    """Retain a killed writer's temp using the pinned root directory."""
    name = ".m6-cutover-journal.json.next"
    try:
        info = os.stat(name, dir_fd=transition.directory, follow_symlinks=False)
    except FileNotFoundError:
        return
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_nlink != 1
    ):
        raise MigrationRecoveryError("migration_recovery_temp_unsafe")
    try:
        os.mkdir(".m6-journal-orphans", 0o700, dir_fd=transition.directory)
    except FileExistsError:
        pass
    directory = os.open(
        ".m6-journal-orphans",
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        dir_fd=transition.directory,
    )
    try:
        state = os.fstat(directory)
        if state.st_uid != os.getuid() or stat.S_IMODE(state.st_mode) != 0o700:
            raise MigrationRecoveryError("migration_recovery_temp_unsafe")
        os.fsync(transition.directory)
        destination = "journal-" + secrets.token_hex(16)
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
        if (
            renameat2(
                transition.directory,
                os.fsencode(name),
                directory,
                os.fsencode(destination),
                1,
            )
            != 0
        ):
            raise MigrationRecoveryError("migration_recovery_temp_unsafe")
        os.fsync(directory)
        os.fsync(transition.directory)
        moved = os.stat(destination, dir_fd=directory, follow_symlinks=False)
        if (moved.st_dev, moved.st_ino) != (info.st_dev, info.st_ino):
            raise MigrationRecoveryError("migration_recovery_temp_unsafe")
    finally:
        os.close(directory)


def _receipt(data: dict) -> QuiescentStopReceipt:
    raw = data.get("stop_receipt")
    keys = {
        "unit",
        "pid",
        "cgroup",
        "start_ticks",
        "executable_identity",
        "invocation_id",
        "start_monotonic",
    }
    if not isinstance(raw, dict) or set(raw) != keys:
        raise MigrationRecoveryError("migration_recovery_receipt_invalid")
    if (
        not isinstance(raw.get("unit"), str)
        or re.fullmatch(r"[A-Za-z0-9_.@:-]+\.service", raw["unit"]) is None
        or type(raw.get("pid")) is not int
        or raw["pid"] <= 0
        or any(
            not isinstance(raw.get(key), str)
            for key in ("cgroup", "start_ticks", "invocation_id", "start_monotonic")
        )
        or not raw["start_ticks"].isdigit()
        or not raw["start_monotonic"].isdigit()
        or re.fullmatch(r"[a-f0-9]{32}", raw["invocation_id"]) is None
        or not isinstance(raw.get("executable_identity"), list)
        or len(raw["executable_identity"]) != 2
        or any(type(part) is not int or part < 0 for part in raw["executable_identity"])
    ):
        raise MigrationRecoveryError("migration_recovery_receipt_invalid")
    return QuiescentStopReceipt(
        **{**raw, "executable_identity": tuple(raw["executable_identity"])}
    )


def _validate_stopped_journal(data: dict, receipt: QuiescentStopReceipt) -> None:
    required = {
        "format",
        "phase",
        "backup_id",
        "unit",
        "baseline_restart",
        "baseline_revision",
        "candidate_revision",
        "source_revision",
        "candidate_build_sha256",
        "fixed_unit_sha256",
        "fixed_baseline_override_sha256",
        "fixed_runtime_sha256",
        "fixed_python_sha256",
        "pid",
        "cgroup",
        "start_ticks",
        "invocation_id",
        "start_monotonic",
        "stop_receipt",
    }
    if set(data) not in (required, required | {"prior_backup_ids"}):
        raise MigrationRecoveryError("migration_recovery_journal_invalid")
    if data.get("baseline_restart") not in {
        "no",
        "always",
        "on-success",
        "on-failure",
        "on-abnormal",
        "on-watchdog",
        "on-abort",
    }:
        raise MigrationRecoveryError("migration_recovery_journal_invalid")
    for field in ("baseline_revision", "candidate_revision"):
        value = data.get(field)
        if not isinstance(value, str) or re.fullmatch(r"[a-f0-9]{40}", value) is None:
            raise MigrationRecoveryError("migration_recovery_journal_invalid")
    for field in (
        "candidate_build_sha256",
        "fixed_unit_sha256",
        "fixed_baseline_override_sha256",
        "fixed_runtime_sha256",
        "fixed_python_sha256",
    ):
        value = data.get(field)
        if (field == "candidate_build_sha256" or value is not None) and (
            not isinstance(value, str) or re.fullmatch(r"[a-f0-9]{64}", value) is None
        ):
            raise MigrationRecoveryError("migration_recovery_journal_invalid")
    if any(
        data.get(field) != getattr(receipt, field)
        for field in (
            "unit",
            "pid",
            "cgroup",
            "start_ticks",
            "invocation_id",
            "start_monotonic",
        )
    ):
        raise MigrationRecoveryError("migration_recovery_receipt_invalid")
    expected_group = f"/user.slice/user-{os.getuid()}.slice/user@{os.getuid()}.service/app.slice/{receipt.unit}"
    if receipt.cgroup != expected_group:
        raise MigrationRecoveryError("migration_recovery_receipt_invalid")
    history = data.get("prior_backup_ids", [])
    if (
        not isinstance(history, list)
        or len(history) > 128
        or len(set(history)) != len(history)
        or any(
            not isinstance(item, str)
            or re.fullmatch(r"migration-preflight-[a-f0-9]{32}", item) is None
            for item in history
        )
        or data.get("backup_id") in history
    ):
        raise MigrationRecoveryError("migration_recovery_journal_invalid")


def _verify_stopped(receipt: QuiescentStopReceipt) -> dict[str, str]:
    current = _properties(receipt.unit)
    if (
        current.get("MainPID") != "0"
        or current.get("ActiveState") not in {"failed", "inactive"}
        or current.get("RefuseManualStart") != "yes"
        or current.get("Restart") != "no"
        or current.get("InvocationID") != receipt.invocation_id
        or current.get("ExecMainStartTimestampMonotonic") != receipt.start_monotonic
        or current.get("ControlGroup", "") not in ("", receipt.cgroup)
    ):
        raise MigrationRecoveryError("migration_recovery_service_changed")
    _ensure_cgroup_empty(receipt.cgroup)
    return current


def _validate_backup(root: Path, backup_id: str, source: str) -> None:
    backup_parent = root / "backups"
    backup = backup_parent / backup_id
    _safe_directory(backup_parent)
    _safe_directory(backup)
    manifest = _read_private_json(backup / "manifest.json")
    catalog = load_migration_catalog()
    if (
        manifest.get("format") != "agentmonitor-m4-migration-preflight.v1"
        or manifest.get("backup_id") != backup_id
        or manifest.get("source_revision") != source
        or manifest.get("target_revision") != catalog.head
        or manifest.get("catalog_digest") != catalog.digest
        or _digest_file(backup / "agentmonitor.db") != manifest.get("database_sha256")
    ):
        raise MigrationRecoveryError("migration_recovery_backup_invalid")
    _verify_sqlite_backup(backup, catalog.digest, source)
    _verify_source_metadata(
        root,
        {
            SETTINGS: manifest.get("settings_sha256"),
            SETTINGS_LOCK: manifest.get("settings_lock_sha256"),
        },
    )


def _recover_migration_before_start(
    root: Path,
    *,
    transition_lease: _TransitionLease,
    service_lease: ServiceQuiescenceLeaseV1,
    settings_lease: _SettingsLockLeaseV1,
    verify_provenance: Callable[[], None] | None = None,
) -> str:
    """Resume a journaled pre-start migration, retaining every earlier backup.

    Caller holds all three capabilities continuously. This function never starts
    a service, deletes a backup, or acts after candidate startup was attempted.
    """
    try:
        transition_lease.validate(root)
        service_lease.validate(root)
        settings_lease.validate(root)
        data = _read_journal_at(transition_lease)[0]
        source = data.get("source_revision")
        backup_id = data.get("backup_id")
        if (
            data.get("format") != "m6-cutover.v1"
            or data.get("phase") != "stopped"
            or not isinstance(source, str)
            or not isinstance(backup_id, str)
            or re.fullmatch(r"migration-preflight-[a-f0-9]{32}", backup_id) is None
        ):
            raise MigrationRecoveryError("migration_recovery_journal_invalid")
        _preflight_catalog(source)
        receipt = _receipt(data)
        _validate_stopped_journal(data, receipt)
        current = _verify_stopped(receipt)
        if verify_provenance is not None:
            verify_provenance()
        ref = DatabaseRefV1(root / "agentmonitor.db", root)
        # A killed SQLite writer may leave a valid WAL/SHM; recover and
        # checkpoint it while all service and settings locks remain held.
        checkpoint_sqlite_database(ref)
        transition_lease.validate(root)
        service_lease.validate(root)
        settings_lease.validate(root)
        if (
            _verify_stopped(receipt) != current
            or _read_journal_at(transition_lease)[0] != data
        ):
            raise MigrationRecoveryError("migration_recovery_service_changed")
        view = InspectSchemaCompatibilityV1(
            ref, application_schema_range(), "runtime_read_write"
        )
        if view.integrity_state != "passed" or view.policy_state != "passed":
            raise MigrationRecoveryError("migration_recovery_database_invalid")
        _preserve_interrupted_journal(transition_lease)
        transition_lease.validate(root)
        service_lease.validate(root)
        settings_lease.validate(root)
        if (
            _verify_stopped(receipt) != current
            or _read_journal_at(transition_lease)[0] != data
        ):
            raise MigrationRecoveryError("migration_recovery_service_changed")
        if view.current_revision == source and view.state == "upgrade_required":
            # The source is intact. Preserve any incomplete old backup and bind
            # a new ID durably before allowing another migration attempt.
            replacement_id = "migration-preflight-" + secrets.token_hex(16)
            history = data.get("prior_backup_ids", [])
            if not isinstance(history, list) or any(
                not isinstance(item, str)
                or re.fullmatch(r"migration-preflight-[a-f0-9]{32}", item) is None
                for item in history
            ):
                raise MigrationRecoveryError("migration_recovery_journal_invalid")
            updated = {
                **data,
                "backup_id": replacement_id,
                "prior_backup_ids": [*history, backup_id],
            }
            _replace_journal(transition_lease, data, updated)
            data = updated
            backup_id = replacement_id
            transition_lease.validate(root)
            service_lease.validate(root)
            settings_lease.validate(root)
            if (
                _verify_stopped(receipt) != current
                or _read_journal_at(transition_lease)[0] != data
            ):
                raise MigrationRecoveryError("migration_recovery_service_changed")
            if verify_provenance is not None:
                verify_provenance()
            outcome, actual = run_upgrade(
                root,
                source,
                service_lease=service_lease,
                settings_lease=settings_lease,
                planned_backup_id=backup_id,
            )
            if outcome != "upgraded" or actual != backup_id:
                raise MigrationRecoveryError("migration_recovery_upgrade_failed")
        elif (
            view.current_revision != load_migration_catalog().head
            or view.state != "compatible"
        ):
            raise MigrationRecoveryError("migration_recovery_schema_unknown")
        _validate_backup(root, backup_id, source)
        transition_lease.validate(root)
        service_lease.validate(root)
        settings_lease.validate(root)
        if (
            _verify_stopped(receipt) != current
            or _read_journal_at(transition_lease)[0] != data
        ):
            raise MigrationRecoveryError("migration_recovery_service_changed")
        view = InspectSchemaCompatibilityV1(
            ref, application_schema_range(), "runtime_read_write"
        )
        if (
            view.current_revision != load_migration_catalog().head
            or view.state != "compatible"
            or view.integrity_state != "passed"
            or view.policy_state != "passed"
        ):
            raise MigrationRecoveryError("migration_recovery_database_invalid")
        if verify_provenance is not None:
            verify_provenance()
        transition_lease.validate(root)
        service_lease.validate(root)
        settings_lease.validate(root)
        if (
            _verify_stopped(receipt) != current
            or _read_journal_at(transition_lease)[0] != data
        ):
            raise MigrationRecoveryError("migration_recovery_service_changed")
        _replace_journal(transition_lease, data, {**data, "phase": "migrated"})
        return "migration_recovered"
    except MigrationRecoveryError:
        raise
    except Exception:  # noqa: BLE001 -- bounded, secret-free refusal.
        raise MigrationRecoveryError("migration_recovery_unavailable") from None

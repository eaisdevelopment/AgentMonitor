"""Recover a stopped M6 migration without starting a dashboard service."""

from __future__ import annotations

import json
import os
import re
import secrets
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
    _fsync_dir,
    _read_private_json,
)
from tools.automation.implementations.m6_quiescent_stop import (
    QuiescentStopReceipt,
    _properties,
)
from tools.automation.implementations.m6_transition_lease import _TransitionLease


class MigrationRecoveryError(RuntimeError):
    """Fail-closed recovery refusal without user records."""


def _replace_journal(path: Path, before: dict, after: dict) -> None:
    """Durably replace only the exact observed stopped journal."""
    if _read_private_json(path) != before:
        raise MigrationRecoveryError("migration_recovery_journal_changed")
    temporary = path.parent / (".m6-recovery-" + secrets.token_hex(16))
    raw = json.dumps(after, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    if len(raw) > 65536:
        raise MigrationRecoveryError("migration_recovery_journal_invalid")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(raw)
            stream.flush()
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    if _read_private_json(path) != before:
        raise MigrationRecoveryError("migration_recovery_journal_changed")
    os.replace(temporary, path)
    _fsync_dir(path.parent)
    if _read_private_json(path) != after:
        raise MigrationRecoveryError("migration_recovery_journal_changed")


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


def _verify_stopped(receipt: QuiescentStopReceipt) -> dict[str, str]:
    current = _properties(receipt.unit)
    if (
        current.get("MainPID") != "0"
        or current.get("ActiveState") not in {"failed", "inactive"}
        or current.get("RefuseManualStart") != "yes"
        or current.get("Restart") != "no"
        or current.get("InvocationID") != receipt.invocation_id
        or current.get("ExecMainStartTimestampMonotonic") != receipt.start_monotonic
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
) -> str:
    """Resume a journaled pre-start migration, retaining every earlier backup.

    Caller holds all three capabilities continuously. This function never starts
    a service, deletes a backup, or acts after candidate startup was attempted.
    """
    try:
        transition_lease.validate(root)
        service_lease.validate(root)
        settings_lease.validate(root)
        journal = root / ".m6-cutover-journal.json"
        data = _read_private_json(journal)
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
        current = _verify_stopped(receipt)
        ref = DatabaseRefV1(root / "agentmonitor.db", root)
        # A killed SQLite writer may leave a valid WAL/SHM; recover and
        # checkpoint it while all service and settings locks remain held.
        checkpoint_sqlite_database(ref)
        transition_lease.validate(root)
        service_lease.validate(root)
        settings_lease.validate(root)
        if _verify_stopped(receipt) != current or _read_private_json(journal) != data:
            raise MigrationRecoveryError("migration_recovery_service_changed")
        view = InspectSchemaCompatibilityV1(
            ref, application_schema_range(), "runtime_read_write"
        )
        if view.integrity_state != "passed" or view.policy_state != "passed":
            raise MigrationRecoveryError("migration_recovery_database_invalid")
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
            _replace_journal(journal, data, updated)
            data = updated
            backup_id = replacement_id
            transition_lease.validate(root)
            service_lease.validate(root)
            settings_lease.validate(root)
            if (
                _verify_stopped(receipt) != current
                or _read_private_json(journal) != data
            ):
                raise MigrationRecoveryError("migration_recovery_service_changed")
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
        if _verify_stopped(receipt) != current or _read_private_json(journal) != data:
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
        _replace_journal(journal, data, {**data, "phase": "migrated"})
        return "migration_recovered"
    except MigrationRecoveryError:
        raise
    except Exception:  # noqa: BLE001 -- bounded, secret-free refusal.
        raise MigrationRecoveryError("migration_recovery_unavailable") from None

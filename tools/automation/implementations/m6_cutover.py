"""Candidate offline M6 cutover; caller must review recovery before use.

This command has not been run against the installed dashboard. It does not
claim M6 acceptance. It never signals a child process. Once candidate startup
is attempted it will not restore an old database snapshot automatically.
"""

# ruff: noqa: E402 -- this operator pins checkout source before backend imports.

from __future__ import annotations

import ctypes
import fcntl
import hashlib
import json
import os
import re
import secrets
import signal
import stat
import subprocess
import sys
import time
import urllib.request
from collections.abc import Callable
from contextlib import ExitStack
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend/src"))

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    checkpoint_sqlite_database,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    InspectActiveSchemaCompatibilityV1,
    InspectSchemaCompatibilityV1,
    application_schema_range,
    load_migration_catalog,
)
from agentmonitor.composition.iam_operator import exclusive_service_quiescence

from tools.automation.implementations.auto_m6_local_activate import (
    TOOL_ROOT,
    build_override,
    request,
    tree_digest,
)
from tools.automation.implementations.auto_m6_local_update import replace_override
from tools.automation.implementations.auto_migrate import (
    _hold_settings_lock,
    run_upgrade,
)
from tools.automation.implementations.m5_service_activation import (
    acquire_m5_service_activation_lock_v1,
    release_m5_service_activation_lock_v1,
    validate_m5_service_activation_lock_v1,
)
from tools.automation.implementations.m6_candidate_release import (
    prepare_candidate_release,
    verify_candidate_release,
)
from tools.automation.implementations.m6_migration_recovery import (
    _preserve_interrupted_journal,
    _receipt,
    _recover_migration_before_start,
    _validate_stopped_journal,
    _verify_stopped,
)
from tools.automation.implementations.m6_offline_restore import (
    _ensure_cgroup_empty,
    _read_private_json,
    classify_restore_recovery,
    restore_before_candidate_start,
    resume_prepared_restore,
)
from tools.automation.implementations.m6_quiescent_stop import (
    _process_identity,
    _properties,
    stop_quiescent_unit,
)
from tools.automation.implementations.m6_runtime_integrity import (
    _runtime_digest,
    _trusted_checkout_revision,
)
from tools.automation.implementations.m6_transition_journal import (
    _read_journal_at,
    _replace_journal,
)
from tools.automation.implementations.m6_transition_lease import (
    _hold_transition_locks,
    _TransitionLease,
)


def _systemd_environment() -> dict[str, str]:
    runtime = f"/run/user/{os.getuid()}"
    return {
        "PATH": "/usr/bin:/bin",
        "LANG": "C",
        "XDG_RUNTIME_DIR": runtime,
        "DBUS_SESSION_BUS_ADDRESS": "unix:path=" + runtime + "/bus",
    }


class CutoverError(RuntimeError):
    """A closed transition failure without paths or user data."""


def _ctl(*args: str) -> None:
    result = subprocess.run(
        ["/usr/bin/systemctl", "--user", *args],
        capture_output=True,
        env=_systemd_environment(),
        timeout=60,
        check=False,
    )
    if result.returncode:
        raise CutoverError("systemd_operation_failed")


def _cwd(unit: str) -> str:
    result = subprocess.run(
        [
            "/usr/bin/systemctl",
            "--user",
            "show",
            unit,
            "-p",
            "WorkingDirectory",
            "--value",
        ],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
        env=_systemd_environment(),
    )
    if result.returncode:
        raise CutoverError("systemd_identity_unavailable")
    return result.stdout.strip()


def _ticks(pid: int) -> str:
    fields = (Path("/proc") / str(pid) / "stat").read_text().rpartition(") ")[2].split()
    if len(fields) < 20:
        raise CutoverError("process_identity_unavailable")
    return fields[19]


def _private_directory(path: Path) -> None:
    metadata = path.lstat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_mode & 0o022
    ):
        raise CutoverError("directory_unsafe")


def _create(path: Path, content: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(content)
            stream.flush()
        os.fsync(fd)
    finally:
        os.close(fd)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _journal(
    path: Path,
    phase: str,
    backup_id: str | None = None,
    *,
    facts: dict[str, Any] | None = None,
) -> None:
    """Durably record a closed recovery phase, without secrets or account data."""
    raw = (
        json.dumps(
            {
                "format": "m6-cutover.v1",
                "phase": phase,
                "backup_id": backup_id,
                **(facts or {}),
            },
            sort_keys=True,
        ).encode()
        + b"\n"
    )
    tmp = path.with_name(path.name + ".next")
    _create(tmp, raw)
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _revision(root: Path) -> str:
    status = subprocess.run(
        ["/usr/bin/git", "status", "--porcelain"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    revision = subprocess.run(
        ["/usr/bin/git", "rev-parse", "--verify", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    value = revision.stdout.strip()
    if (
        status.returncode
        or status.stdout
        or revision.returncode
        or re.fullmatch(r"[0-9a-f]{40}", value) is None
    ):
        raise CutoverError("candidate_checkout_not_clean")
    return value


def _verify_active_source_schema(reference: DatabaseRefV1, source: str) -> None:
    state, revision = InspectActiveSchemaCompatibilityV1(reference)
    expected_state = (
        "compatible" if source == load_migration_catalog().head else "upgrade_required"
    )
    if state != expected_state or revision != source:
        raise CutoverError("source_schema_invalid")


def _cutover_engine(
    *,
    unit: str,
    data_root: Path,
    baseline: Path,
    candidate: Path,
    override: Path,
    source: str,
    expected_revision: str,
    expected_executable: Path,
    expected_build: str | None = None,
    baseline_private: bool = False,
    same_schema_update: bool = False,
) -> str:
    """Migrate one selected unit. Call only after candidate has been reviewed.

    A crash leaves a private journal and is not automatically recovered. The
    caller must never rerun over that journal; inspect state first. The baseline
    override must be the exact existing generated override.
    """
    if (
        source != load_migration_catalog().head
        if same_schema_update
        else source not in {"v1_0603", "v1_0707", "v1_0708"}
    ) or baseline == candidate:
        raise CutoverError("cutover_selection_invalid")
    if not all(
        path.is_absolute() and path.resolve() == path
        for path in (data_root, baseline, candidate, override)
    ):
        raise CutoverError("cutover_path_invalid")
    if re.fullmatch(r"[A-Za-z0-9_.@:-]+\.service", unit) is None:
        raise CutoverError("unit_invalid")
    expected_dir = Path.home() / ".config/systemd/user" / (unit + ".d")
    if override.parent != expected_dir or override.name != "90-m6-local.conf":
        raise CutoverError("override_selection_invalid")
    _private_directory(data_root)
    _private_directory(expected_dir)
    if not candidate.is_dir() or not baseline.is_dir():
        raise CutoverError("checkout_unavailable")
    if _revision(candidate) != expected_revision:
        raise CutoverError("candidate_revision_mismatch")
    built_page = candidate / "frontend/dist/dashboard.html"
    if built_page.is_symlink() or not built_page.is_file():
        raise CutoverError("candidate_build_unavailable")
    build_digest = tree_digest(candidate / "frontend/dist")
    if expected_build is not None and build_digest != expected_build:
        raise CutoverError("candidate_build_changed")
    before = (
        _candidate_override(baseline)
        if baseline_private and unit == _FIXED_UNIT
        else build_override(baseline)
    ).encode()
    after = (
        _candidate_override(candidate)
        if unit == _FIXED_UNIT
        else build_override(candidate)
    ).encode()
    if override.read_bytes() != before:
        raise CutoverError("override_changed")
    ref = DatabaseRefV1(data_root / "agentmonitor.db", data_root)
    ref.validate()
    _verify_active_source_schema(ref, source)
    baseline_props = _properties(unit)
    if baseline_props.get("ActiveState") != "active" or _cwd(unit) != str(baseline):
        raise CutoverError("service_identity_invalid")
    baseline_restart = baseline_props.get("Restart")
    if baseline_restart not in {
        "no",
        "always",
        "on-success",
        "on-failure",
        "on-abnormal",
        "on-watchdog",
        "on-abort",
    }:
        raise CutoverError("baseline_restart_policy_invalid")
    pid = int(baseline_props["MainPID"])
    group = baseline_props["ControlGroup"]
    ticks = _ticks(pid)
    if not expected_executable.is_absolute() or not expected_executable.is_file():
        raise CutoverError("service_executable_invalid")
    if Path(f"/proc/{pid}/exe").resolve() != expected_executable.resolve():
        raise CutoverError("service_executable_mismatch")
    if Path(f"/proc/{pid}/cwd").resolve() != baseline:
        raise CutoverError("service_identity_invalid")
    root_fd = os.open(
        data_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    root_identity = os.fstat(root_fd)
    if (
        root_identity.st_uid != os.getuid()
        or stat.S_IMODE(root_identity.st_mode) != 0o700
    ):
        os.close(root_fd)
        raise CutoverError("directory_unsafe")
    lock_name = ".m6-cutover.lock"
    lock_fd = os.open(
        lock_name,
        os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o600,
        dir_fd=root_fd,
    )
    lock_metadata = os.fstat(lock_fd)
    if (
        not stat.S_ISREG(lock_metadata.st_mode)
        or lock_metadata.st_uid != os.getuid()
        or lock_metadata.st_mode & 0o077
        or lock_metadata.st_nlink != 1
    ):
        os.close(lock_fd)
        os.close(root_fd)
        raise CutoverError("cutover_lock_unsafe")
    try:
        shared_lock = acquire_m5_service_activation_lock_v1()
    except Exception:  # noqa: BLE001 -- release local descriptor on refusal.
        os.close(lock_fd)
        os.close(root_fd)
        raise CutoverError("service_transition_lock_unavailable") from None
    guard = expected_dir / "95-m6-cutover-restart.conf"
    journal = data_root / ".m6-cutover-journal.json"
    guard_content = b"[Unit]\nRefuseManualStart=yes\n[Service]\nRestart=no\n"
    stopped = False
    journal_created = False
    guard_created = False
    backup_id = (
        None if same_schema_update else "migration-preflight-" + secrets.token_hex(16)
    )
    stop_receipt = None
    stop_attempted = False
    candidate_start_attempted = False
    operation_stack = ExitStack()
    barrier_stack = ExitStack()
    facts: dict[str, Any] = {
        "unit": unit,
        "baseline_restart": baseline_restart,
        "baseline_revision": _revision(baseline),
        "candidate_revision": expected_revision,
        "source_revision": source,
        "candidate_build_sha256": build_digest,
        "fixed_unit_sha256": _FIXED_UNIT_SHA256 if unit == _FIXED_UNIT else None,
        "fixed_baseline_override_sha256": hashlib.sha256(before).hexdigest()
        if unit == _FIXED_UNIT
        else None,
        "fixed_runtime_sha256": _FIXED_VENV_SHA256 if unit == _FIXED_UNIT else None,
        "fixed_python_sha256": _FIXED_PYTHON_SHA256 if unit == _FIXED_UNIT else None,
        "pid": pid,
        "cgroup": group,
        "start_ticks": ticks,
        "invocation_id": baseline_props.get("InvocationID"),
        "start_monotonic": baseline_props.get("ExecMainStartTimestampMonotonic"),
    }
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_now = os.fstat(lock_fd)
        lock_path_now = os.stat(lock_name, dir_fd=root_fd, follow_symlinks=False)
        root_now = os.stat(data_root, follow_symlinks=False)
        if (
            (root_now.st_dev, root_now.st_ino)
            != (root_identity.st_dev, root_identity.st_ino)
            or root_now.st_uid != os.getuid()
            or stat.S_IMODE(root_now.st_mode) != 0o700
            or (lock_now.st_dev, lock_now.st_ino)
            != (lock_path_now.st_dev, lock_path_now.st_ino)
            or lock_now.st_nlink != 1
            or lock_now.st_uid != os.getuid()
            or not stat.S_ISREG(lock_path_now.st_mode)
            or lock_now.st_mode & 0o077
        ):
            raise CutoverError("cutover_lock_changed")
        validate_m5_service_activation_lock_v1(shared_lock)
        if _properties(unit).get("Restart") != baseline_restart:
            raise CutoverError("baseline_restart_policy_changed")
        _create(
            journal,
            json.dumps(
                {
                    "format": "m6-cutover.v1",
                    "phase": "preparing",
                    "backup_id": backup_id,
                    **facts,
                },
                sort_keys=True,
            ).encode()
            + b"\n",
        )
        journal_created = True
        _create(guard, guard_content)
        guard_created = True
        _ctl("daemon-reload")
        guarded = _properties(unit)
        if (
            guarded.get("Restart") != "no"
            or guarded.get("RefuseManualStart") != "yes"
            or int(guarded.get("MainPID", "0")) != pid
            or guarded.get("ControlGroup") != group
            or _ticks(pid) != ticks
            or _cwd(unit) != str(baseline)
        ):
            raise CutoverError("service_changed")
        if (
            _revision(candidate) != expected_revision
            or tree_digest(candidate / "frontend/dist") != build_digest
        ):
            raise CutoverError("candidate_changed")
        settings_lease = operation_stack.enter_context(_hold_settings_lock(data_root))
        barrier_handle = barrier_stack.enter_context(
            open_sqlite_database(ref, "runtime_read_write")
        )
        barrier = barrier_stack.enter_context(barrier_handle.connect())
        barrier.exec_driver_sql("BEGIN IMMEDIATE")
        validate_m5_service_activation_lock_v1(shared_lock)
        if unit == _FIXED_UNIT:
            _fixed_unit_preflight(
                expected_revision,
                build_digest,
                guarded=True,
                private_baseline=baseline_private,
                update_baseline=baseline if same_schema_update else None,
            )
        _journal(journal, "stop_attempted", backup_id, facts=facts)
        stop_attempted = True
        executable_stat = expected_executable.stat()
        stop_receipt = stop_quiescent_unit(
            unit,
            expected_pid=pid,
            expected_cgroup=group,
            expected_start_ticks=ticks,
            expected_executable_identity=(
                executable_stat.st_dev,
                executable_stat.st_ino,
            ),
            expected_invocation_id=guarded["InvocationID"],
            expected_start_monotonic=guarded["ExecMainStartTimestampMonotonic"],
        )
        stopped = True
        facts["stop_receipt"] = asdict(stop_receipt)
        _journal(journal, "stopped", backup_id, facts=facts)
        service_lease = operation_stack.enter_context(
            exclusive_service_quiescence(data_root, ref)
        )
        barrier.rollback()
        barrier_stack.close()
        outcome, actual_backup_id = run_upgrade(
            data_root,
            source,
            service_lease=service_lease,
            settings_lease=settings_lease,
            planned_backup_id=backup_id,
        )
        if same_schema_update:
            if outcome != "already_current" or actual_backup_id is not None:
                raise CutoverError("current_schema_unverified")
        elif outcome != "upgraded" or actual_backup_id != backup_id:
            raise CutoverError("migration_not_applied")
        _journal(
            journal,
            "schema_verified" if same_schema_update else "migrated",
            backup_id,
            facts=facts,
        )
        if not replace_override(override, before, after):
            raise CutoverError("override_changed")
        _ctl("daemon-reload")
        # Mark before submitting the start job; never restore after this point.
        if (
            _revision(candidate) != expected_revision
            or tree_digest(candidate / "frontend/dist") != build_digest
        ):
            raise CutoverError("candidate_changed")
        validate_m5_service_activation_lock_v1(shared_lock)
        if unit == _FIXED_UNIT:
            _fixed_unit_preflight(
                expected_revision,
                build_digest,
                guarded=True,
                candidate=True,
                update_baseline=baseline if same_schema_update else None,
            )
        _journal(journal, "candidate_start_attempted", backup_id, facts=facts)
        candidate_start_attempted = True
        # Keep restart disabled, but permit the intended start after durable boundary.
        if guard.is_symlink() or guard.read_bytes() != guard_content:
            raise CutoverError("restart_override_changed")
        replacement = b"[Service]\nRestart=no\n"
        if not replace_override(guard, guard_content, replacement):
            raise CutoverError("restart_override_changed")
        guard_content = replacement
        _ctl("daemon-reload")
        if unit == _FIXED_UNIT:
            _fixed_unit_preflight(
                expected_revision,
                build_digest,
                guarded=True,
                candidate=True,
                start_block=False,
                update_baseline=baseline if same_schema_update else None,
            )
        operation_stack.close()
        _ctl("start", unit)
        if unit == _FIXED_UNIT:
            _fixed_unit_preflight(
                expected_revision,
                build_digest,
                guarded=True,
                candidate=True,
                start_block=False,
                update_baseline=baseline if same_schema_update else None,
            )
        current = _properties(unit)
        candidate_pid = int(current.get("MainPID", "0"))
        if (
            current.get("ActiveState") != "active"
            or _cwd(unit) != str(candidate)
            or candidate_pid <= 1
            or Path(f"/proc/{candidate_pid}/cwd").resolve() != candidate
            or _revision(candidate) != expected_revision
        ):
            raise CutoverError("candidate_start_unverified")
        if unit == _FIXED_UNIT:
            _verify_fixed_candidate_process(current, checkout=candidate)
        _journal(journal, "candidate_started", backup_id, facts=facts)
        # Keep restart disabled until a separate real product readiness check.
        return "candidate_started_product_verification_required"

    except Exception:  # noqa: BLE001 -- leave guarded state for reviewed recovery.
        if candidate_start_attempted:
            # Do not signal a process whose identity failed verification. Close
            # the manual-start path and preserve the durable candidate boundary.
            blocked = b"[Unit]\nRefuseManualStart=yes\n[Service]\nRestart=no\n"
            try:
                if guard_content != blocked:
                    if not replace_override(guard, guard_content, blocked):
                        raise CutoverError("restart_override_changed")
                    guard_content = blocked
                _ctl("daemon-reload")
            except Exception:  # noqa: BLE001 -- retain journal if the start block cannot be verified.
                raise CutoverError("candidate_start_block_unverified") from None
        # Never infer migration completion from a backup manifest, and never
        # start or restore automatically on an ambiguous partial transition.
        # The durable phase and disabled restart remain available for recovery.
        raise CutoverError("cutover_incomplete_review_journal") from None
    finally:
        barrier_stack.close()
        operation_stack.close()
        try:
            may_remove_guard = not stop_attempted
            if stop_attempted and not stopped:
                try:
                    observed = _properties(unit)
                    state = next(
                        line
                        for line in Path(f"/proc/{pid}/status").read_text().splitlines()
                        if line.startswith("State:")
                    )
                    may_remove_guard = (
                        observed.get("ActiveState") == "active"
                        and observed.get("MainPID") == str(pid)
                        and observed.get("InvocationID") == facts["invocation_id"]
                        and _ticks(pid) == ticks
                        and state.split()[1] not in {"T", "t"}
                    )
                except (OSError, ValueError, StopIteration, RuntimeError):
                    may_remove_guard = False
            if guard_created and may_remove_guard:
                if (
                    guard.is_symlink()
                    or not guard.exists()
                    or guard.read_bytes() != guard_content
                ):
                    raise CutoverError("restart_override_cleanup_failed")
                guard.unlink()
                _ctl("daemon-reload")
            if (
                journal_created
                and may_remove_guard
                and not stopped
                and journal.is_file()
                and not journal.is_symlink()
            ):
                recorded = _read_private_json(journal)
                if (
                    recorded.get("backup_id") != backup_id
                    or recorded.get("unit") != unit
                ):
                    raise CutoverError("journal_changed")
                journal.unlink()
                directory_fd = os.open(
                    data_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                )
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        finally:
            try:
                os.close(lock_fd)
                os.close(root_fd)
            finally:
                release_m5_service_activation_lock_v1(shared_lock)


# Installed target and private runtime are code-owned. Candidate revision and
# build are selected from the clean fixed worktree and pinned per operation.
_FIXED_UNIT = "agentmonitor-dashboard.service"
_FIXED_HOME = Path("/home/dev")
_FIXED_DATA = _FIXED_HOME / ".local/share/agentmonitor"
_FIXED_BASELINE = _FIXED_DATA / "worktrees/m6-integration"
_FIXED_SOURCE = _FIXED_DATA / "worktrees/m6-signal-composition"
_FIXED_CREDENTIAL_ENV_FILE = _FIXED_HOME / "Nextcloud/Code/AI/AgentMonitor/.env"
_FIXED_RELEASES = _FIXED_DATA / "releases"
_FIXED_UNIT_FILE = _FIXED_HOME / ".config/systemd/user" / _FIXED_UNIT
_FIXED_OVERRIDE = _FIXED_UNIT_FILE.parent / (_FIXED_UNIT + ".d") / "90-m6-local.conf"
_FIXED_BASELINE_REVISION = "86f27012275c8c2f52fa48098b53fae60a352c55"
_FIXED_UNIT_SHA256 = "7c233a1117a96e997ed81b5205e52c5e3e66a8efedb2c95aba0b80dada186852"
_FIXED_OVERRIDE_SHA256 = (
    "cd2445d6e6ab04fbe432c88aa21301d9fbd17dbebd053fba6406f5d5559acfcb"
)
_FIXED_EXECUTABLE = Path("/usr/bin/python3.12")
_FIXED_VENV = _FIXED_DATA / "releases/m6-runtime-2fedf0809fc9"
_FIXED_VENV_SHA256 = "84112363e7525a6ff42764bfaf7f9dfacbfb22399dfe8275898ac105b3d7edbc"
_FIXED_PYTHON_SHA256 = (
    "e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f"
)


def _candidate_override(candidate: Path) -> str:
    command = (
        str(_FIXED_VENV / "bin/python")
        + " -m agentmonitor.composition.bootstrap --config "
        + str(_FIXED_DATA / "service.env")
        + " --data-root "
        + str(_FIXED_DATA)
        + " --host 127.0.0.1 --port 43110 --authenticated-dashboard"
        + " --lan-host 192.168.1.18 --lan-network 192.168.1.0/24"
    )
    if candidate != _FIXED_BASELINE:
        command += " --credential-env-file " + str(_FIXED_CREDENTIAL_ENV_FILE)
    runtime_environment = "Environment=PYTHONDONTWRITEBYTECODE=1\n"
    return (
        build_override(candidate)
        + runtime_environment
        + "ExecStart=\nExecStart="
        + command
        + "\n"
    )


def _check_candidate_schema(candidate: Path) -> None:
    """Refuse a candidate whose schema differs from this migration controller."""
    code = (
        "import json; from dataclasses import asdict; "
        "from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility "
        "import load_migration_catalog, application_schema_range; "
        "c=load_migration_catalog(); "
        "print(json.dumps({'head':c.head,'digest':c.digest,'range':asdict(application_schema_range())},sort_keys=True))"
    )
    env = {
        "PATH": "/usr/bin:/bin",
        "LANG": "C",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(candidate / "backend/src"),
    }
    result = subprocess.run(
        [str(_FIXED_VENV / "bin/python"), "-c", code],
        cwd=candidate,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if result.returncode or len(result.stdout) > 8192:
        raise CutoverError("candidate_schema_unavailable")
    catalog = load_migration_catalog()
    expected = {
        "head": catalog.head,
        "digest": catalog.digest,
        "range": asdict(application_schema_range()),
    }
    try:
        observed = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise CutoverError("candidate_schema_unavailable") from None
    if observed != expected:
        raise CutoverError("candidate_schema_mismatch")


def _verify_retained_baseline(path: Path) -> tuple[str, str]:
    if path.parent != _FIXED_RELEASES:
        raise CutoverError("update_baseline_invalid")
    match = re.fullmatch(r"m6-candidate-([a-f0-9]{40})-([a-f0-9]{64})", path.name)
    if match is None:
        raise CutoverError("update_baseline_invalid")
    revision, build = match.groups()
    verify_candidate_release(path, _FIXED_RELEASES, revision, build)
    return revision, build


def _fixed_unit_preflight(
    expected_revision: str,
    expected_build: str,
    *,
    guarded: bool = False,
    candidate: bool = False,
    private_baseline: bool = False,
    start_block: bool = True,
    update_baseline: Path | None = None,
) -> None:
    candidate_path = _FIXED_RELEASES / (
        "m6-candidate-" + expected_revision + "-" + expected_build
    )
    verify_candidate_release(
        candidate_path, _FIXED_RELEASES, expected_revision, expected_build
    )
    if update_baseline is not None:
        _verify_retained_baseline(update_baseline)
    if os.getuid() != _FIXED_HOME.stat().st_uid:
        raise CutoverError("target_uid_mismatch")
    release_parent = _FIXED_VENV.parent.lstat()
    if (
        not stat.S_ISDIR(release_parent.st_mode)
        or release_parent.st_uid != os.getuid()
        or stat.S_IMODE(release_parent.st_mode) != 0o700
    ):
        raise CutoverError("runtime_parent_unsafe")
    for path, digest in (
        (_FIXED_UNIT_FILE, _FIXED_UNIT_SHA256),
        (
            _FIXED_OVERRIDE,
            hashlib.sha256(_candidate_override(candidate_path).encode()).hexdigest()
            if candidate
            else hashlib.sha256(
                _candidate_override(update_baseline or _FIXED_BASELINE).encode()
            ).hexdigest()
            if private_baseline or update_baseline is not None
            else _FIXED_OVERRIDE_SHA256,
        ),
    ):
        state = path.lstat()
        if (
            not stat.S_ISREG(state.st_mode)
            or state.st_uid != os.getuid()
            or state.st_mode & 0o022
            or state.st_nlink != 1
            or hashlib.sha256(path.read_bytes()).hexdigest() != digest
        ):
            raise CutoverError("target_unit_changed")
    guard_path = _FIXED_OVERRIDE.parent / "95-m6-cutover-restart.conf"
    if guarded and (
        guard_path.is_symlink()
        or guard_path.read_bytes()
        != (
            b"[Unit]\nRefuseManualStart=yes\n[Service]\nRestart=no\n"
            if start_block
            else b"[Service]\nRestart=no\n"
        )
    ):
        raise CutoverError("target_guard_changed")
    result = subprocess.run(
        [
            "/usr/bin/systemctl",
            "--user",
            "show",
            _FIXED_UNIT,
            "-p",
            "FragmentPath",
            "-p",
            "DropInPaths",
            "-p",
            "WorkingDirectory",
            "-p",
            "ExecStart",
        ],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
        env=_systemd_environment(),
    )
    if result.returncode or len(result.stdout) > 16384:
        raise CutoverError("target_unit_unavailable")
    fields = dict(
        line.split("=", 1) for line in result.stdout.splitlines() if "=" in line
    )
    expected_start = (
        str(_FIXED_VENV / "bin/python")
        if candidate or private_baseline or update_baseline is not None
        else str(
            _FIXED_DATA / "worktrees/m5-scheduled-quota-fix/backend/.venv/bin/python"
        )
    )
    if (
        fields.get("FragmentPath") != str(_FIXED_UNIT_FILE)
        or fields.get("DropInPaths")
        != (str(_FIXED_OVERRIDE) + (" " + str(guard_path) if guarded else ""))
        or fields.get("WorkingDirectory")
        != str(candidate_path if candidate else update_baseline or _FIXED_BASELINE)
        or not fields.get("ExecStart", "").startswith(
            "{ path="
            + expected_start
            + " ; argv[]="
            + expected_start
            + " -m agentmonitor.composition.bootstrap "
        )
    ):
        raise CutoverError("target_unit_changed")
    if (
        (
            update_baseline is None
            and _revision(_FIXED_BASELINE) != _FIXED_BASELINE_REVISION
        )
        or _revision(candidate_path) != expected_revision
        or tree_digest(candidate_path / "frontend/dist") != expected_build
        or _runtime_digest(_FIXED_VENV) != _FIXED_VENV_SHA256
        or hashlib.sha256(_FIXED_EXECUTABLE.read_bytes()).hexdigest()
        != _FIXED_PYTHON_SHA256
    ):
        raise CutoverError("release_identity_changed")
    # Do not execute candidate or private-runtime code until the pinned files
    # and clean source revision have passed the static checks above.
    _check_candidate_schema(candidate_path)


def _verify_fixed_update_prestart(
    data: dict[str, Any], baseline: Path, candidate: Path, guard: Path
) -> None:
    """Revalidate the selected releases and loaded unit before resume or start."""
    if _FIXED_UNIT != data.get("unit"):
        raise CutoverError("update_recovery_journal_invalid")
    blocked = b"[Unit]\nRefuseManualStart=yes\n[Service]\nRestart=no\n"
    content = _FIXED_OVERRIDE.read_bytes()
    baseline_content = _candidate_override(baseline).encode()
    candidate_content = _candidate_override(candidate).encode()
    if content not in {baseline_content, candidate_content}:
        raise CutoverError("update_recovery_override_changed")
    if guard.is_symlink() or not guard.is_file():
        raise CutoverError("update_recovery_guard_changed")
    guard_content = guard.read_bytes()
    if guard_content not in {blocked, b"[Service]\nRestart=no\n"}:
        raise CutoverError("update_recovery_guard_changed")
    _fixed_unit_preflight(
        data["candidate_revision"],
        data["candidate_build_sha256"],
        guarded=True,
        candidate=content == candidate_content,
        start_block=guard_content == blocked,
        update_baseline=baseline,
    )


def _verify_candidate_process(
    properties: dict[str, str],
    *,
    unit: str,
    executable: Path,
    expected_command: list[str],
) -> None:
    pid = int(properties.get("MainPID", "0"))
    group = properties.get("ControlGroup", "")
    invocation = properties.get("InvocationID", "")
    start = properties.get("ExecMainStartTimestampMonotonic", "")
    if pid <= 1 or not invocation or not start:
        raise CutoverError("candidate_identity_invalid")
    descriptor = os.pidfd_open(pid, 0)
    try:
        before = _process_identity(pid, group)
        expected = executable.stat()
        if before[1:] != (expected.st_dev, expected.st_ino):
            raise CutoverError("candidate_executable_invalid")
        fd = os.open(f"/proc/{pid}/cmdline", os.O_RDONLY | os.O_CLOEXEC)
        try:
            actual = os.read(fd, 16385)
        finally:
            os.close(fd)
        expected_cmdline = (
            b"\0".join(part.encode() for part in expected_command) + b"\0"
        )
        if actual != expected_cmdline or _process_identity(pid, group) != before:
            raise CutoverError("candidate_process_changed")
        current = _properties(unit)
        if (
            current.get("MainPID") != str(pid)
            or current.get("ControlGroup") != group
            or current.get("InvocationID") != invocation
            or current.get("ExecMainStartTimestampMonotonic") != start
        ):
            raise CutoverError("candidate_process_changed")
    finally:
        os.close(descriptor)


def _verify_fixed_candidate_process(
    properties: dict[str, str], *, checkout: Path
) -> None:
    command = (
        _candidate_override(checkout)
        .split("ExecStart=\nExecStart=", 1)[1]
        .strip()
        .split()
    )
    _verify_candidate_process(
        properties,
        unit=_FIXED_UNIT,
        executable=_FIXED_EXECUTABLE,
        expected_command=command,
    )


def cutover() -> str:
    """Cut over only the code-owned AgentMonitor service and pinned releases."""
    with _hold_transition_locks(_FIXED_DATA) as transition:
        retained_candidate, candidate_revision, candidate_build = (
            prepare_candidate_release(
                _FIXED_SOURCE,
                _FIXED_RELEASES,
                _FIXED_DATA,
                TOOL_ROOT / "frontend/node_modules",
            )
        )
        transition.validate(_FIXED_DATA)
        original = build_override(_FIXED_BASELINE).encode()
        private = _candidate_override(_FIXED_BASELINE).encode()
        active_override = _FIXED_OVERRIDE.read_bytes()
        if active_override not in {original, private}:
            raise CutoverError("target_unit_changed")
        baseline_private = active_override == private
        _fixed_unit_preflight(
            candidate_revision, candidate_build, private_baseline=baseline_private
        )
    return _cutover_engine(
        unit=_FIXED_UNIT,
        data_root=_FIXED_DATA,
        baseline=_FIXED_BASELINE,
        candidate=retained_candidate,
        override=_FIXED_OVERRIDE,
        source="v1_0707",
        expected_revision=candidate_revision,
        expected_build=candidate_build,
        expected_executable=_FIXED_EXECUTABLE,
        baseline_private=baseline_private,
    )


def update_current_schema() -> str:
    """Prepare one sealed release and update the fixed v1_0717 service."""
    with _hold_transition_locks(_FIXED_DATA) as transition:
        retained, revision, build = prepare_candidate_release(
            _FIXED_SOURCE,
            _FIXED_RELEASES,
            _FIXED_DATA,
            TOOL_ROOT / "frontend/node_modules",
        )
        transition.validate(_FIXED_DATA)
        baseline = Path(_cwd(_FIXED_UNIT))
        _verify_retained_baseline(baseline)
        if baseline == retained:
            raise CutoverError("candidate_already_running")
        _fixed_unit_preflight(revision, build, update_baseline=baseline)
        properties = _properties(_FIXED_UNIT)
        if properties.get("ActiveState") != "active":
            raise CutoverError("service_identity_invalid")
        _verify_fixed_candidate_process(properties, checkout=baseline)
    return _cutover_engine(
        unit=_FIXED_UNIT,
        data_root=_FIXED_DATA,
        baseline=baseline,
        candidate=retained,
        override=_FIXED_OVERRIDE,
        source=load_migration_catalog().head,
        expected_revision=revision,
        expected_build=build,
        expected_executable=_FIXED_EXECUTABLE,
        baseline_private=True,
        same_schema_update=True,
    )


def _recover_same_schema_update_engine_inner(
    root: Path,
    transition: _TransitionLease,
    *,
    unit: str,
    baseline: Path,
    candidate: Path,
    override: Path,
    guard: Path,
    verify_baseline: Callable[[], None],
    expected_executable: Path,
) -> str:
    """Resume only a proven pre-candidate-start same-schema transition."""
    transition.validate(root)
    data = _read_journal_at(transition)[0]
    if (
        data.get("format") != "m6-cutover.v1"
        or data.get("source_revision") != load_migration_catalog().head
        or data.get("backup_id") is not None
        or data.get("unit") != unit
        or data.get("phase")
        not in {
            "preparing",
            "stop_attempted",
            "stopped",
            "schema_verified",
            "baseline_start_attempted",
            "baseline_http_ready",
        }
        or data.get("baseline_revision") != _revision(baseline)
        or data.get("candidate_revision") != _revision(candidate)
        or data.get("candidate_build_sha256")
        != tree_digest(candidate / "frontend/dist")
    ):
        raise CutoverError("update_recovery_journal_invalid")
    receipt = None
    if data.get("stop_receipt") is None:
        expected = {
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
        }
        expected_group = (
            f"/user.slice/user-{os.getuid()}.slice/"
            f"user@{os.getuid()}.service/app.slice/{unit}"
        )
        if (
            set(data) != expected
            or type(data.get("pid")) is not int
            or data["pid"] <= 1
            or data.get("cgroup") != expected_group
            or not isinstance(data.get("start_ticks"), str)
            or not data["start_ticks"].isdigit()
            or not isinstance(data.get("invocation_id"), str)
            or re.fullmatch(r"[a-f0-9]{32}", data["invocation_id"]) is None
            or not isinstance(data.get("start_monotonic"), str)
            or not data["start_monotonic"].isdigit()
        ):
            raise CutoverError("update_recovery_journal_invalid")
    if data.get("stop_receipt") is not None:
        receipt = _receipt(data)
        _validate_stopped_journal(data, receipt)
    elif data["phase"] not in {
        "preparing",
        "stop_attempted",
        "baseline_start_attempted",
        "baseline_http_ready",
    }:
        raise CutoverError("update_recovery_journal_invalid")
    before = (
        _candidate_override(baseline)
        if unit == _FIXED_UNIT
        else build_override(baseline)
    ).encode()
    after = (
        _candidate_override(candidate)
        if unit == _FIXED_UNIT
        else build_override(candidate)
    ).encode()
    blocked = b"[Unit]\nRefuseManualStart=yes\n[Service]\nRestart=no\n"
    relaxed = b"[Service]\nRestart=no\n"
    if data["phase"] == "preparing":
        properties = _properties(unit)
        pid = data["pid"]
        group = data["cgroup"]
        executable = expected_executable.stat()
        if (
            properties.get("ActiveState") != "active"
            or properties.get("MainPID") != str(pid)
            or properties.get("ControlGroup") != group
            or properties.get("InvocationID") != data["invocation_id"]
            or properties.get("ExecMainStartTimestampMonotonic")
            != data["start_monotonic"]
            or _process_identity(pid, group)
            != (data["start_ticks"], executable.st_dev, executable.st_ino)
            or _cwd(unit) != str(baseline)
            or Path(f"/proc/{pid}/cwd").resolve() != baseline
            or override.is_symlink()
            or override.read_bytes() != before
        ):
            raise CutoverError("update_recovery_service_changed")
        if guard.exists():
            if guard.is_symlink():
                raise CutoverError("update_recovery_guard_changed")
            content = guard.read_bytes()
            if content != blocked and (
                not blocked.startswith(content)
                or not replace_override(guard, content, blocked)
            ):
                raise CutoverError("update_recovery_guard_changed")
        _ctl("daemon-reload")
        if guard.exists() and unit == _FIXED_UNIT:
            _verify_fixed_update_prestart(data, baseline, candidate, guard)
        verify_baseline()
        return _finish_restored_baseline_engine(
            root,
            transition,
            unit=unit,
            guard=guard,
            expected_restart=data["baseline_restart"],
            verify_ready=verify_baseline,
            verify_after=verify_baseline,
            existing_baseline=True,
        )
    if (
        data["phase"] in {"baseline_start_attempted", "baseline_http_ready"}
        and _properties(unit).get("ActiveState") == "active"
    ):
        if override.is_symlink() or override.read_bytes() != before:
            raise CutoverError("update_recovery_override_changed")
        if data["phase"] == "baseline_http_ready" and not guard.exists():
            _ctl("daemon-reload")
        verify_baseline()
        return _finish_restored_baseline_engine(
            root,
            transition,
            unit=unit,
            guard=guard,
            expected_restart=data["baseline_restart"],
            verify_ready=verify_baseline,
            verify_after=verify_baseline,
        )
    if data["phase"] == "stop_attempted":
        properties = _properties(unit)
        pid = data.get("pid")
        group = data.get("cgroup")
        if (
            type(pid) is not int
            or pid <= 1
            or not isinstance(group, str)
            or properties.get("ControlGroup") not in {"", group}
            or properties.get("Restart") != "no"
            or properties.get("RefuseManualStart") != "yes"
            or properties.get("InvocationID") != data.get("invocation_id")
            or properties.get("ExecMainStartTimestampMonotonic")
            != data.get("start_monotonic")
            or override.is_symlink()
            or override.read_bytes() != before
            or guard.is_symlink()
            or guard.read_bytes() != blocked
        ):
            raise CutoverError("update_recovery_service_changed")
        if unit == _FIXED_UNIT:
            _ctl("daemon-reload")
            _verify_fixed_update_prestart(data, baseline, candidate, guard)
            properties = _properties(unit)
        if (
            properties.get("ActiveState") == "active"
            and properties.get("MainPID") == str(pid)
            and properties.get("ControlGroup") == group
        ):
            descriptor = os.pidfd_open(pid, 0)
            try:
                executable = expected_executable.stat()
                if (
                    _process_identity(pid, group)
                    != (data.get("start_ticks"), executable.st_dev, executable.st_ino)
                    or _properties(unit) != properties
                    or _cwd(unit) != str(baseline)
                    or Path(f"/proc/{pid}/cwd").resolve() != baseline
                ):
                    raise CutoverError("update_recovery_service_changed")
                state = next(
                    line
                    for line in (Path("/proc") / str(pid) / "status")
                    .read_text()
                    .splitlines()
                    if line.startswith("State:")
                )
                if state.split()[1] in {"T", "t"}:
                    if unit == _FIXED_UNIT:
                        _verify_fixed_update_prestart(data, baseline, candidate, guard)
                    if (
                        _process_identity(pid, group)
                        != (
                            data.get("start_ticks"),
                            executable.st_dev,
                            executable.st_ino,
                        )
                        or _properties(unit) != properties
                        or Path(f"/proc/{pid}/cwd").resolve() != baseline
                    ):
                        raise CutoverError("update_recovery_service_changed")
                    signal.pidfd_send_signal(descriptor, signal.SIGCONT)
            finally:
                os.close(descriptor)
            _preserve_interrupted_journal(transition)
            updated = {**data, "phase": "baseline_start_attempted"}
            _replace_journal(transition, data, updated)
            deadline = time.monotonic() + 15
            while True:
                try:
                    verify_baseline()
                    break
                except (CutoverError, OSError):
                    if time.monotonic() >= deadline:
                        raise CutoverError(
                            "update_recovery_readiness_unavailable"
                        ) from None
                    time.sleep(0.1)
            return _finish_restored_baseline_engine(
                root,
                transition,
                unit=unit,
                guard=guard,
                expected_restart=data["baseline_restart"],
                verify_ready=verify_baseline,
                verify_after=verify_baseline,
            )
        if properties.get("MainPID") != "0" or properties.get("ActiveState") not in {
            "failed",
            "inactive",
        }:
            raise CutoverError("update_recovery_service_changed")
        _ensure_cgroup_empty(group)
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    with (
        exclusive_service_quiescence(root, reference) as service,
        _hold_settings_lock(root) as settings,
    ):
        transition.validate(root)
        service.validate(root)
        settings.validate(root)
        if _read_journal_at(transition)[0] != data:
            raise CutoverError("update_recovery_journal_changed")
        if data["phase"] in {"stop_attempted", "stopped", "schema_verified"}:
            if receipt is not None:
                _verify_stopped(receipt)
            else:
                _ensure_cgroup_empty(data["cgroup"])
            checkpoint_sqlite_database(reference)
            view = InspectSchemaCompatibilityV1(
                reference, application_schema_range(), "runtime_read_write"
            )
            if (
                view.state != "compatible"
                or view.current_revision != load_migration_catalog().head
            ):
                raise CutoverError("update_recovery_schema_invalid")
            _preserve_interrupted_journal(transition)
            if unit == _FIXED_UNIT:
                _ctl("daemon-reload")
                _verify_fixed_update_prestart(data, baseline, candidate, guard)
            current_override = override.read_bytes()
            if current_override not in {before, after}:
                raise CutoverError("update_recovery_override_changed")
            if current_override != before and not replace_override(
                override, current_override, before
            ):
                raise CutoverError("update_recovery_override_changed")
            if guard.is_symlink() or guard.read_bytes() != blocked:
                raise CutoverError("update_recovery_guard_changed")
            if unit == _FIXED_UNIT:
                _ctl("daemon-reload")
                _verify_fixed_update_prestart(data, baseline, candidate, guard)
            updated = {**data, "phase": "baseline_start_attempted"}
            _replace_journal(transition, data, updated)
            data = updated
        elif override.is_symlink() or override.read_bytes() != before:
            raise CutoverError("update_recovery_override_changed")
        guard_bytes = guard.read_bytes()
        if guard.is_symlink() or guard_bytes not in {blocked, relaxed}:
            raise CutoverError("update_recovery_guard_changed")
        if guard_bytes == blocked and not replace_override(guard, blocked, relaxed):
            raise CutoverError("update_recovery_guard_changed")
        _ctl("daemon-reload")
        if unit == _FIXED_UNIT:
            _verify_fixed_update_prestart(data, baseline, candidate, guard)
    current = _properties(unit)
    if current.get("ActiveState") != "active":
        if (
            current.get("MainPID") != "0"
            or current.get("ActiveState") not in {"inactive", "failed"}
            or current.get("RefuseManualStart") != "no"
            or current.get("Restart") != "no"
        ):
            raise CutoverError("update_recovery_service_changed")
        _ensure_cgroup_empty(data["cgroup"])
        _ctl("start", unit)
    deadline = time.monotonic() + 15
    while True:
        try:
            verify_baseline()
            break
        except (CutoverError, OSError):
            if time.monotonic() >= deadline:
                raise CutoverError("update_recovery_readiness_unavailable") from None
            time.sleep(0.1)
    return _finish_restored_baseline_engine(
        root,
        transition,
        unit=unit,
        guard=guard,
        expected_restart=data["baseline_restart"],
        verify_ready=verify_baseline,
        verify_after=verify_baseline,
    )


def _recover_same_schema_candidate_attempt_inner(
    root: Path,
    transition: _TransitionLease,
    *,
    unit: str,
    baseline: Path,
    candidate: Path,
    override: Path,
    guard: Path,
    verify_candidate: Callable[[], None],
) -> str:
    """Reconcile only the same candidate after an uncertain start request."""
    transition.validate(root)
    data = _read_journal_at(transition)[0]
    if (
        data.get("format") != "m6-cutover.v1"
        or data.get("phase") != "candidate_start_attempted"
        or data.get("source_revision") != load_migration_catalog().head
        or data.get("backup_id") is not None
        or data.get("unit") != unit
        or data.get("baseline_revision") != _revision(baseline)
        or data.get("candidate_revision") != _revision(candidate)
        or data.get("candidate_build_sha256")
        != tree_digest(candidate / "frontend/dist")
    ):
        raise CutoverError("update_recovery_journal_invalid")
    receipt = _receipt(data)
    _validate_stopped_journal(data, receipt)
    after = (
        _candidate_override(candidate)
        if unit == _FIXED_UNIT
        else build_override(candidate)
    ).encode()
    if override.is_symlink() or override.read_bytes() != after:
        raise CutoverError("update_recovery_override_changed")
    blocked = b"[Unit]\nRefuseManualStart=yes\n[Service]\nRestart=no\n"
    relaxed = b"[Service]\nRestart=no\n"
    if guard.is_symlink() or guard.read_bytes() not in {blocked, relaxed}:
        raise CutoverError("update_recovery_guard_changed")
    if unit == _FIXED_UNIT:
        _ctl("daemon-reload")
        _verify_fixed_update_prestart(data, baseline, candidate, guard)
    _preserve_interrupted_journal(transition)
    if guard.read_bytes() == blocked and not replace_override(guard, blocked, relaxed):
        raise CutoverError("update_recovery_guard_changed")
    _ctl("daemon-reload")
    if unit == _FIXED_UNIT:
        _verify_fixed_update_prestart(data, baseline, candidate, guard)
    current = _properties(unit)
    if current.get("ActiveState") != "active":
        if (
            current.get("MainPID") != "0"
            or current.get("ActiveState") not in {"inactive", "failed"}
            or current.get("RefuseManualStart") != "no"
            or current.get("Restart") != "no"
        ):
            raise CutoverError("update_recovery_service_changed")
        _ensure_cgroup_empty(receipt.cgroup)
        _ctl("start", unit)
    deadline = time.monotonic() + 15
    while True:
        try:
            verify_candidate()
            break
        except (CutoverError, OSError):
            if time.monotonic() >= deadline:
                raise CutoverError("update_recovery_readiness_unavailable") from None
            time.sleep(0.1)
    if _read_journal_at(transition)[0] != data:
        raise CutoverError("update_recovery_journal_changed")
    _replace_journal(transition, data, {**data, "phase": "candidate_started"})
    return "candidate_started_product_verification_required"


def _reblock_current_update_on_failure(root: Path, guard: Path) -> None:
    journal = root / ".m6-cutover-journal.json"
    if not journal.exists():
        return
    if journal.is_symlink() or guard.is_symlink():
        raise CutoverError("update_recovery_guard_changed")
    blocked = b"[Unit]\nRefuseManualStart=yes\n[Service]\nRestart=no\n"
    relaxed = b"[Service]\nRestart=no\n"
    if not guard.exists():
        data = _read_private_json(journal)
        if data.get("format") != "m6-cutover.v1" or data.get("phase") not in {
            "baseline_http_ready",
            "candidate_http_ready",
        }:
            return
        _create(guard, blocked)
    elif guard.read_bytes() == relaxed:
        if not replace_override(guard, relaxed, blocked):
            raise CutoverError("update_recovery_guard_changed")
    elif guard.read_bytes() != blocked:
        raise CutoverError("update_recovery_guard_changed")
    _ctl("daemon-reload")


def _recover_same_schema_update_engine(
    root: Path,
    transition: _TransitionLease,
    *,
    unit: str,
    baseline: Path,
    candidate: Path,
    override: Path,
    guard: Path,
    verify_baseline: Callable[[], None],
    expected_executable: Path,
) -> str:
    try:
        return _recover_same_schema_update_engine_inner(
            root,
            transition,
            unit=unit,
            baseline=baseline,
            candidate=candidate,
            override=override,
            guard=guard,
            verify_baseline=verify_baseline,
            expected_executable=expected_executable,
        )
    except Exception:
        _reblock_current_update_on_failure(root, guard)
        raise


def _recover_same_schema_candidate_attempt(
    root: Path,
    transition: _TransitionLease,
    *,
    unit: str,
    baseline: Path,
    candidate: Path,
    override: Path,
    guard: Path,
    verify_candidate: Callable[[], None],
) -> str:
    try:
        return _recover_same_schema_candidate_attempt_inner(
            root,
            transition,
            unit=unit,
            baseline=baseline,
            candidate=candidate,
            override=override,
            guard=guard,
            verify_candidate=verify_candidate,
        )
    except Exception:
        _reblock_current_update_on_failure(root, guard)
        raise


def _journal_update_baseline(data: dict[str, Any]) -> Path:
    revision = data.get("baseline_revision")
    if not isinstance(revision, str) or re.fullmatch(r"[a-f0-9]{40}", revision) is None:
        raise CutoverError("update_baseline_invalid")
    matches = [
        path
        for path in _FIXED_RELEASES.iterdir()
        if path.name.startswith("m6-candidate-" + revision + "-")
    ]
    if len(matches) != 1:
        raise CutoverError("update_baseline_invalid")
    baseline = matches[0]
    _verify_retained_baseline(baseline)
    if hashlib.sha256(_candidate_override(baseline).encode()).hexdigest() != data.get(
        "fixed_baseline_override_sha256"
    ):
        raise CutoverError("update_baseline_invalid")
    return baseline


def _validate_current_update_facts(data: dict[str, Any]) -> tuple[Path, Path, str, str]:
    """Bind a same-schema recovery journal to sealed local releases."""
    revision = data.get("candidate_revision")
    build = data.get("candidate_build_sha256")
    if (
        data.get("format") != "m6-cutover.v1"
        or data.get("source_revision") != load_migration_catalog().head
        or data.get("backup_id") is not None
        or data.get("unit") != _FIXED_UNIT
        or data.get("fixed_unit_sha256") != _FIXED_UNIT_SHA256
        or data.get("fixed_runtime_sha256") != _FIXED_VENV_SHA256
        or data.get("fixed_python_sha256") != _FIXED_PYTHON_SHA256
        or data.get("baseline_restart")
        not in {
            "no",
            "always",
            "on-success",
            "on-failure",
            "on-abnormal",
            "on-watchdog",
            "on-abort",
        }
        or not isinstance(revision, str)
        or re.fullmatch(r"[a-f0-9]{40}", revision) is None
        or not isinstance(build, str)
        or re.fullmatch(r"[a-f0-9]{64}", build) is None
    ):
        raise CutoverError("update_recovery_journal_invalid")
    baseline = _journal_update_baseline(data)
    candidate = _FIXED_RELEASES / ("m6-candidate-" + revision + "-" + build)
    verify_candidate_release(candidate, _FIXED_RELEASES, revision, build)
    unit_state = _FIXED_UNIT_FILE.lstat()
    if (
        not stat.S_ISREG(unit_state.st_mode)
        or unit_state.st_uid != os.getuid()
        or unit_state.st_mode & 0o022
        or unit_state.st_nlink != 1
        or hashlib.sha256(_FIXED_UNIT_FILE.read_bytes()).hexdigest()
        != _FIXED_UNIT_SHA256
    ):
        raise CutoverError("target_unit_changed")
    if (
        _runtime_digest(_FIXED_VENV) != _FIXED_VENV_SHA256
        or hashlib.sha256(_FIXED_EXECUTABLE.read_bytes()).hexdigest()
        != _FIXED_PYTHON_SHA256
    ):
        raise CutoverError("release_identity_changed")
    return baseline, candidate, revision, build


def recover_current_schema_update() -> str:
    """Resume one fixed same-schema update without restoring a database."""
    root = _FIXED_DATA
    controller = _trusted_checkout_revision(ROOT)
    finalize = False
    with _hold_transition_locks(root) as transition:
        data = _read_journal_at(transition)[0]
        phase = data.get("phase")
        baseline, candidate, revision, build = _validate_current_update_facts(data)
        guard = _FIXED_OVERRIDE.parent / "95-m6-cutover-restart.conf"
        blocked = b"[Unit]\nRefuseManualStart=yes\n[Service]\nRestart=no\n"

        def verify_running(checkout: Path) -> None:
            if _trusted_checkout_revision(ROOT) != controller:
                raise CutoverError("operator_checkout_changed")
            present = guard.exists()
            _fixed_unit_preflight(
                revision,
                build,
                guarded=present,
                candidate=checkout == candidate,
                start_block=present and guard.read_bytes() == blocked,
                update_baseline=baseline,
            )
            command = (
                _candidate_override(checkout)
                .split("ExecStart=\nExecStart=", 1)[1]
                .strip()
                .split()
            )
            _verify_candidate_runtime(
                root=root,
                unit=_FIXED_UNIT,
                checkout=checkout,
                origin="http://127.0.0.1:43110",
                executable=_FIXED_EXECUTABLE,
                expected_command=command,
            )

        if phase in {"candidate_started", "candidate_http_ready"}:
            finalize = True
        elif phase == "candidate_start_attempted":
            _recover_same_schema_candidate_attempt(
                root,
                transition,
                unit=_FIXED_UNIT,
                baseline=baseline,
                candidate=candidate,
                override=_FIXED_OVERRIDE,
                guard=guard,
                verify_candidate=lambda: verify_running(candidate),
            )
            finalize = True
        else:
            return _recover_same_schema_update_engine(
                root,
                transition,
                unit=_FIXED_UNIT,
                baseline=baseline,
                candidate=candidate,
                override=_FIXED_OVERRIDE,
                guard=guard,
                verify_baseline=lambda: verify_running(baseline),
                expected_executable=_FIXED_EXECUTABLE,
            )
    if finalize:
        return finalize_candidate()
    raise CutoverError("update_recovery_journal_invalid")


def _fixed_journal_facts(
    data: dict[str, Any], *, phase: str, allow_update: bool = False
) -> tuple[str, str, bool]:
    receipt = data.get("stop_receipt")
    candidate_revision = data.get("candidate_revision")
    candidate_build = data.get("candidate_build_sha256")
    executable = _FIXED_EXECUTABLE.stat()
    private_hash = hashlib.sha256(
        _candidate_override(_FIXED_BASELINE).encode()
    ).hexdigest()
    baseline_hash = data.get("fixed_baseline_override_sha256")
    is_update = (
        allow_update and data.get("source_revision") == load_migration_catalog().head
    )
    if is_update:
        _journal_update_baseline(data)
        if data.get("backup_id") is not None:
            raise CutoverError("migration_recovery_target_invalid")
    if (
        data.get("format") != "m6-cutover.v1"
        or data.get("phase") != phase
        or data.get("unit") != _FIXED_UNIT
        or (not is_update and data.get("source_revision") != "v1_0707")
        or (not is_update and data.get("baseline_revision") != _FIXED_BASELINE_REVISION)
        or data.get("fixed_unit_sha256") != _FIXED_UNIT_SHA256
        or (
            not is_update
            and baseline_hash not in {_FIXED_OVERRIDE_SHA256, private_hash}
        )
        or data.get("fixed_runtime_sha256") != _FIXED_VENV_SHA256
        or data.get("fixed_python_sha256") != _FIXED_PYTHON_SHA256
        or not isinstance(receipt, dict)
        or receipt.get("unit") != _FIXED_UNIT
        or receipt.get("executable_identity") != [executable.st_dev, executable.st_ino]
        or not isinstance(candidate_revision, str)
        or re.fullmatch(r"[a-f0-9]{40}", candidate_revision) is None
        or not isinstance(candidate_build, str)
        or re.fullmatch(r"[a-f0-9]{64}", candidate_build) is None
    ):
        raise CutoverError("migration_recovery_target_invalid")
    _validate_stopped_journal(data, _receipt(data))
    return candidate_revision, candidate_build, baseline_hash == private_hash


def recover_interrupted_migration() -> str:
    """Recover only the fixed dashboard's recorded pre-start migration.

    This retains the service start block and never starts a process. The
    selected source/build and installed unit must still match the journal.
    """
    root = _FIXED_DATA
    controller_revision = _trusted_checkout_revision(ROOT)

    def verify_controller() -> None:
        if _trusted_checkout_revision(ROOT) != controller_revision:
            raise CutoverError("operator_checkout_changed")

    with _hold_transition_locks(root) as transition:
        journal = root / ".m6-cutover-journal.json"
        data = _read_private_json(journal)
        candidate_revision, candidate_build, baseline_private = _fixed_journal_facts(
            data, phase="stopped"
        )
        transition.validate(root)
        _fixed_unit_preflight(
            candidate_revision,
            candidate_build,
            guarded=True,
            private_baseline=baseline_private,
        )

        def verify_recovery_provenance() -> None:
            verify_controller()
            _fixed_unit_preflight(
                candidate_revision,
                candidate_build,
                guarded=True,
                private_baseline=baseline_private,
            )

        return _recover_migration_engine(
            root,
            transition,
            data,
            verify_provenance=verify_recovery_provenance,
        )


def _recover_migration_engine(
    root: Path,
    transition: _TransitionLease,
    expected_journal: dict[str, Any],
    *,
    verify_provenance: Callable[[], None] | None = None,
) -> str:
    """Hold the same service and settings locks for the entire recovery."""
    journal = root / ".m6-cutover-journal.json"
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    with (
        exclusive_service_quiescence(root, reference) as service,
        _hold_settings_lock(root) as settings,
    ):
        transition.validate(root)
        if _read_private_json(journal) != expected_journal:
            raise CutoverError("migration_recovery_journal_changed")
        return _recover_migration_before_start(
            root,
            transition_lease=transition,
            service_lease=service,
            settings_lease=settings,
            verify_provenance=verify_provenance,
        )


def restore_interrupted_migration() -> str:
    """Restore the fixed dashboard backup before any candidate start."""
    root = _FIXED_DATA
    controller_revision = _trusted_checkout_revision(ROOT)
    with _hold_transition_locks(root) as transition:
        data = _read_private_json(root / ".m6-cutover-journal.json")
        phase = data.get("phase")
        facts: dict[str, Any]
        if phase == "migrated":
            facts = data
        elif phase in {"restore_prepared", "restore_activated"}:
            nested = data.get("cutover_facts")
            if not isinstance(nested, dict):
                raise CutoverError("restore_recovery_journal_invalid")
            facts = nested
        else:
            raise CutoverError("restore_recovery_phase_invalid")
        candidate_revision, candidate_build, baseline_private = _fixed_journal_facts(
            facts, phase="migrated"
        )

        def verify_provenance() -> None:
            if _trusted_checkout_revision(ROOT) != controller_revision:
                raise CutoverError("operator_checkout_changed")
            _fixed_unit_preflight(
                candidate_revision,
                candidate_build,
                guarded=True,
                private_baseline=baseline_private,
            )

        verify_provenance()
        return _restore_interrupted_migration_engine(
            root, transition, data, facts, verify_provenance=verify_provenance
        )


def _restore_interrupted_migration_engine(
    root: Path,
    transition: _TransitionLease,
    expected_journal: dict[str, Any],
    facts: dict[str, Any],
    *,
    verify_provenance: Callable[[], None] | None = None,
) -> str:
    """Restore/reconcile genuine pre-start backup while every lock is held."""
    journal = root / ".m6-cutover-journal.json"
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    with (
        exclusive_service_quiescence(root, reference) as service,
        _hold_settings_lock(root) as settings,
    ):
        transition.validate(root)
        if _read_private_json(journal) != expected_journal:
            raise CutoverError("restore_recovery_journal_changed")
        if verify_provenance is not None:
            verify_provenance()
        if expected_journal.get("phase") == "migrated":
            receipt = _receipt(facts)
            status = restore_before_candidate_start(
                root,
                facts["backup_id"],
                receipt=receipt,
                journal=journal,
                transition_lease=transition,
                service_lease=service,
                settings_lease=settings,
                verify_provenance=verify_provenance,
            )
            if status != "restored":
                raise CutoverError("restore_recovery_unverified")
        else:
            status = resume_prepared_restore(
                root,
                transition_lease=transition,
                service_lease=service,
                settings_lease=settings,
                verify_provenance=verify_provenance,
            )
            if status not in {"activated", "already_activated"}:
                raise CutoverError("restore_recovery_unverified")
        if verify_provenance is not None:
            verify_provenance()
        transition.validate(root)
        service.validate(root)
        settings.validate(root)
        return "baseline_restored_service_stopped"


def _start_restored_baseline_engine(
    root: Path,
    transition: _TransitionLease,
    facts: dict[str, Any],
    *,
    unit: str,
    guard: Path,
    override: Path,
    expected_override: bytes,
    start_override: bytes,
    baseline: Path,
    executable: Path,
    verify_before: Callable[[], None] | None = None,
    verify_after: Callable[[], None] | None = None,
) -> str:
    """Start only the selected restored unit after a durable no-rollback fence.

    On error a start block is restored when possible; no unknown process is
    signalled and no old snapshot is restored after the start boundary.
    """
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    receipt = _receipt(facts)
    if receipt.unit != unit:
        raise CutoverError("baseline_restart_target_invalid")
    blocked = b"[Unit]\nRefuseManualStart=yes\n[Service]\nRestart=no\n"
    relaxed = b"[Service]\nRestart=no\n"
    guard_relaxed = False
    try:
        with (
            exclusive_service_quiescence(root, reference) as service,
            _hold_settings_lock(root) as settings,
        ):
            transition.validate(root)
            service.validate(root)
            settings.validate(root)
            data = _read_journal_at(transition)[0]
            if (
                data.get("phase") != "restore_activated"
                or data.get("cutover_facts") != facts
            ):
                raise CutoverError("baseline_restart_journal_invalid")
            if (
                classify_restore_recovery(root, root / ".m6-cutover-journal.json")
                != "activated"
            ):
                raise CutoverError("baseline_restore_unverified")
            _verify_stopped(receipt)
            if verify_before is not None:
                verify_before()
            transition.validate(root)
            service.validate(root)
            settings.validate(root)
            if _read_journal_at(transition)[0] != data:
                raise CutoverError("baseline_restart_journal_changed")
            _replace_journal(
                transition, data, {**data, "phase": "baseline_start_attempted"}
            )
            if expected_override != start_override and not replace_override(
                override, expected_override, start_override
            ):
                raise CutoverError("baseline_restart_override_changed")
            if not replace_override(guard, blocked, relaxed):
                raise CutoverError("baseline_restart_guard_changed")
            guard_relaxed = True
            _ctl("daemon-reload")
        transition.validate(root)
        if verify_after is not None:
            verify_after()
        _ctl("start", unit)
        current = _properties(unit)
        pid = int(current.get("MainPID", "0"))
        if (
            current.get("ActiveState") != "active"
            or pid <= 1
            or current.get("ControlGroup") != receipt.cgroup
        ):
            raise CutoverError("baseline_start_unverified")
        descriptor = os.pidfd_open(pid, 0)
        try:
            identity = _process_identity(pid, receipt.cgroup)
            expected = executable.stat()
            if (
                identity[1:] != (expected.st_dev, expected.st_ino)
                or Path(f"/proc/{pid}/cwd").resolve() != baseline
            ):
                raise CutoverError("baseline_start_unverified")
            if _process_identity(pid, receipt.cgroup) != identity or _properties(
                unit
            ).get("MainPID") != str(pid):
                raise CutoverError("baseline_start_unverified")
        finally:
            os.close(descriptor)
        return "baseline_started_readiness_unverified"
    except Exception:
        if guard_relaxed:
            try:
                if not replace_override(guard, relaxed, blocked):
                    raise CutoverError("baseline_restart_guard_changed")
                _ctl("daemon-reload")
            except Exception:  # noqa: BLE001 -- preserve closed recovery result.
                raise CutoverError("baseline_restart_block_unverified") from None
        raise


def _retry_stopped_baseline_engine(
    root: Path,
    transition: _TransitionLease,
    *,
    unit: str,
    guard: Path,
    override: Path,
    baseline: Path,
    executable: Path,
    verify_before: Callable[[], None] | None = None,
    verify_after: Callable[[], None] | None = None,
) -> str:
    """Retry an already-attempted baseline without restoring any database."""
    blocked = b"[Unit]\nRefuseManualStart=yes\n[Service]\nRestart=no\n"
    relaxed = b"[Service]\nRestart=no\n"
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    relaxed_guard = False
    try:
        with (
            exclusive_service_quiescence(root, reference) as service,
            _hold_settings_lock(root) as settings,
        ):
            transition.validate(root)
            data = _read_journal_at(transition)[0]
            if data.get("phase") not in {
                "baseline_start_attempted",
                "baseline_http_ready",
            }:
                raise CutoverError("baseline_restart_journal_invalid")
            receipt = _receipt(data["cutover_facts"])
            if not guard.exists() and data["phase"] == "baseline_http_ready":
                _create(guard, blocked)
                _ctl("daemon-reload")
            current = _properties(unit)
            if (
                receipt.unit != unit
                or current.get("MainPID") != "0"
                or current.get("ActiveState") not in {"inactive", "failed"}
                or current.get("Restart") != "no"
                or current.get("RefuseManualStart") != "yes"
                or current.get("ControlGroup", "") not in {"", receipt.cgroup}
            ):
                raise CutoverError("baseline_restart_service_changed")
            _ensure_cgroup_empty(receipt.cgroup)
            expected = (
                _candidate_override(baseline)
                if unit == _FIXED_UNIT
                else build_override(baseline)
            ).encode()
            original = build_override(baseline).encode()
            actual_override = override.read_bytes()
            if (
                override.is_symlink()
                or actual_override not in {expected, original}
                or guard.is_symlink()
                or guard.read_bytes() != blocked
            ):
                raise CutoverError("baseline_restart_guard_changed")
            if verify_before is not None:
                verify_before()
            transition.validate(root)
            service.validate(root)
            settings.validate(root)
            if actual_override != expected and not replace_override(
                override, actual_override, expected
            ):
                raise CutoverError("baseline_restart_override_changed")
            if _read_journal_at(transition)[0] != data or not replace_override(
                guard, blocked, relaxed
            ):
                raise CutoverError("baseline_restart_guard_changed")
            relaxed_guard = True
            _ctl("daemon-reload")
        if verify_after is not None:
            verify_after()
        _ctl("start", unit)
        current = _properties(unit)
        pid = int(current.get("MainPID", "0"))
        if (
            current.get("ActiveState") != "active"
            or pid <= 1
            or current.get("ControlGroup") != receipt.cgroup
        ):
            raise CutoverError("baseline_start_unverified")
        descriptor = os.pidfd_open(pid, 0)
        try:
            identity = _process_identity(pid, receipt.cgroup)
            expected_exe = executable.stat()
            if (
                identity[1:] != (expected_exe.st_dev, expected_exe.st_ino)
                or Path(f"/proc/{pid}/cwd").resolve() != baseline
                or _process_identity(pid, receipt.cgroup) != identity
                or _properties(unit).get("MainPID") != str(pid)
            ):
                raise CutoverError("baseline_start_unverified")
        finally:
            os.close(descriptor)
        return "baseline_started_readiness_unverified"
    except Exception:
        if relaxed_guard:
            if not replace_override(guard, relaxed, blocked):
                raise CutoverError("baseline_restart_block_unverified") from None
            _ctl("daemon-reload")
        raise


def _finish_restored_baseline_engine(
    root: Path,
    transition: _TransitionLease,
    *,
    unit: str,
    guard: Path,
    expected_restart: str,
    verify_ready: Callable[[], None] | None = None,
    verify_after: Callable[[], None] | None = None,
    candidate: bool = False,
    existing_baseline: bool = False,
) -> str:
    """Restore restart policy and archive the successful transition."""
    transition.validate(root)
    data = _read_journal_at(transition)[0]
    start_phase, ready_phase = (
        ("candidate_started", "candidate_http_ready")
        if candidate
        else (
            "preparing" if existing_baseline else "baseline_start_attempted",
            "baseline_http_ready",
        )
    )
    if data.get("phase") not in {start_phase, ready_phase}:
        raise CutoverError("baseline_finish_journal_invalid")
    original_phase = data["phase"]
    before = _properties(unit)
    pid = int(before.get("MainPID", "0"))
    if before.get("ActiveState") != "active" or pid <= 1:
        raise CutoverError("baseline_start_unverified")
    if verify_ready is not None:
        verify_ready()
    if data["phase"] == start_phase:
        updated = {**data, "phase": ready_phase}
        _replace_journal(transition, data, updated)
        data = updated
    directory = os.open(
        guard.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    try:
        root_info = os.fstat(directory)
        if root_info.st_uid != os.getuid() or root_info.st_mode & 0o022:
            raise CutoverError("baseline_restart_guard_changed")
        try:
            descriptor = os.open(
                guard.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory
            )
        except FileNotFoundError:
            descriptor = None
        if (
            descriptor is None
            and original_phase != ready_phase
            and not existing_baseline
        ):
            raise CutoverError("baseline_restart_guard_changed")
        if descriptor is not None:
            try:
                state = os.fstat(descriptor)
                content = os.read(descriptor, 128)
                if (
                    not stat.S_ISREG(state.st_mode)
                    or state.st_uid != os.getuid()
                    or stat.S_IMODE(state.st_mode) != 0o600
                    or state.st_nlink != 1
                    or content
                    not in {
                        b"[Service]\nRestart=no\n",
                        b"[Unit]\nRefuseManualStart=yes\n[Service]\nRestart=no\n",
                    }
                ):
                    raise CutoverError("baseline_restart_guard_changed")
                guard_path_state = os.stat(
                    guard.name, dir_fd=directory, follow_symlinks=False
                )
                if (guard_path_state.st_dev, guard_path_state.st_ino) != (
                    state.st_dev,
                    state.st_ino,
                ):
                    raise CutoverError("baseline_restart_guard_changed")
                os.unlink(guard.name, dir_fd=directory)
                os.fsync(directory)
            finally:
                os.close(descriptor)
    finally:
        os.close(directory)
    # A previous attempt may have removed the guard and died before reload.
    _ctl("daemon-reload")
    after = _properties(unit)
    if (
        after.get("ActiveState") != "active"
        or after.get("MainPID") != str(pid)
        or after.get("InvocationID") != before.get("InvocationID")
        or after.get("Restart") != expected_restart
        or after.get("RefuseManualStart") != "no"
    ):
        raise CutoverError("baseline_restart_policy_unverified")
    if verify_after is not None:
        verify_after()

    def same_running_invocation() -> None:
        current = _properties(unit)
        if current.get("ActiveState") != "active" or any(
            current.get(key) != before.get(key)
            for key in (
                "MainPID",
                "ControlGroup",
                "InvocationID",
                "ExecMainStartTimestampMonotonic",
            )
        ):
            raise CutoverError("baseline_restart_process_changed")

    same_running_invocation()
    transition.validate(root)
    current, identity = _read_journal_at(transition)
    if current != data:
        raise CutoverError("baseline_restart_journal_changed")
    archive_name = ".m6-completed-journals"
    try:
        os.mkdir(archive_name, 0o700, dir_fd=transition.directory)
    except FileExistsError:
        pass
    archive = os.open(
        archive_name,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        dir_fd=transition.directory,
    )
    try:
        state = os.fstat(archive)
        if state.st_uid != os.getuid() or stat.S_IMODE(state.st_mode) != 0o700:
            raise CutoverError("baseline_restart_archive_unsafe")
        os.fsync(transition.directory)
        target = "journal-" + secrets.token_hex(16)
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
        same_running_invocation()
        if (
            renameat2(
                transition.directory,
                b".m6-cutover-journal.json",
                archive,
                os.fsencode(target),
                1,
            )
            != 0
        ):
            raise CutoverError("baseline_restart_archive_failed")
        os.fsync(archive)
        os.fsync(transition.directory)
        moved = os.stat(target, dir_fd=archive, follow_symlinks=False)
        if (moved.st_dev, moved.st_ino) != identity:
            raise CutoverError("baseline_restart_archive_changed")
    finally:
        os.close(archive)
    return (
        "candidate_ready_restart_restored"
        if candidate
        else "baseline_ready_restart_restored"
    )


def _verify_active_schema(reference: DatabaseRefV1) -> None:
    """Verify the active SQLite schema through a consistent read-only snapshot."""
    state, revision = InspectActiveSchemaCompatibilityV1(reference)
    if state != "compatible" or revision != load_migration_catalog().head:
        raise CutoverError("candidate_schema_unverified")


def _request_loopback_login(origin: str) -> tuple[int, bytes]:
    if re.fullmatch(r"http://127\.0\.0\.1:[1-9][0-9]{0,4}", origin) is None:
        raise CutoverError("candidate_http_unverified")
    from tools.automation.implementations.auto_m6_local_activate import NoRedirect

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(origin + "/login", timeout=3) as response:
        body = response.read(1048577)
        if len(body) > 1048576:
            raise CutoverError("candidate_http_unverified")
        return response.status, body


def _verify_loopback_listener(pid: int, origin: str) -> None:
    """Require the exact PID to own the IPv4 loopback listening socket."""
    match = re.fullmatch(r"http://127\.0\.0\.1:([1-9][0-9]{0,4})", origin)
    if match is None or not 1 <= int(match.group(1)) <= 65535:
        raise CutoverError("candidate_listener_unverified")
    expected = "0100007F:" + format(int(match.group(1)), "04X")
    try:
        proc = Path("/proc") / str(pid)
        with (proc / "net/tcp").open() as stream:
            content = stream.read(4_194_305)
        if len(content) > 4_194_304:
            raise CutoverError("candidate_listener_unverified")
        listeners = set()
        for line in content.splitlines()[1:]:
            fields = line.split()
            if len(fields) > 9 and fields[1] == expected and fields[3] == "0A":
                listeners.add(fields[9])
        owned = set()
        descriptors = list((proc / "fd").iterdir())
        if len(descriptors) > 4096:
            raise CutoverError("candidate_listener_unverified")
        for descriptor in descriptors:
            try:
                target = os.readlink(descriptor)
            except FileNotFoundError:
                continue
            socket_match = re.fullmatch(r"socket:\[([0-9]+)\]", target)
            if socket_match:
                owned.add(socket_match.group(1))
        if len(listeners) != 1 or not listeners <= owned:
            raise CutoverError("candidate_listener_unverified")
    except (OSError, ValueError):
        raise CutoverError("candidate_listener_unverified") from None


def _verify_candidate_runtime(
    *,
    root: Path,
    unit: str,
    checkout: Path,
    origin: str,
    executable: Path,
    expected_command: list[str],
) -> None:
    """Verify one actual candidate process, active SQLite snapshot and HTTP."""
    current = _properties(unit)
    if current.get("ActiveState") != "active" or _cwd(unit) != str(checkout):
        raise CutoverError("candidate_start_unverified")
    _verify_candidate_process(
        current, unit=unit, executable=executable, expected_command=expected_command
    )
    _verify_loopback_listener(int(current["MainPID"]), origin)
    _verify_active_schema(DatabaseRefV1(root / "agentmonitor.db", root))
    status, body = _request_loopback_login(origin)
    if status != 200 or b"agentmonitor-dashboard-root" not in body:
        raise CutoverError("candidate_http_unverified")
    after = _properties(unit)
    if after.get("ActiveState") != "active" or any(
        after.get(key) != current.get(key)
        for key in (
            "MainPID",
            "ControlGroup",
            "InvocationID",
            "ExecMainStartTimestampMonotonic",
        )
    ):
        raise CutoverError("candidate_process_changed")
    _verify_candidate_process(
        after, unit=unit, executable=executable, expected_command=expected_command
    )
    _verify_loopback_listener(int(after["MainPID"]), origin)


def finalize_candidate() -> str:
    """Verify the fixed running candidate before restoring its restart policy."""
    root = _FIXED_DATA
    controller_revision = _trusted_checkout_revision(ROOT)
    with _hold_transition_locks(root) as transition:
        data = _read_journal_at(transition)[0]
        phase = data.get("phase")
        if phase not in {"candidate_started", "candidate_http_ready"}:
            raise CutoverError("candidate_finish_journal_invalid")
        revision, build, _ = _fixed_journal_facts(data, phase=phase, allow_update=True)
        checkout = _FIXED_RELEASES / ("m6-candidate-" + revision + "-" + build)
        update_baseline = (
            _journal_update_baseline(data)
            if data.get("source_revision") == load_migration_catalog().head
            else None
        )
        guard = _FIXED_OVERRIDE.parent / "95-m6-cutover-restart.conf"
        blocked = b"[Unit]\nRefuseManualStart=yes\n[Service]\nRestart=no\n"
        relaxed = b"[Service]\nRestart=no\n"
        if guard.is_symlink():
            raise CutoverError("candidate_restart_guard_changed")
        if not guard.exists():
            if phase != "candidate_http_ready":
                raise CutoverError("candidate_restart_guard_changed")
            _ctl("daemon-reload")

        def verify() -> None:
            if _trusted_checkout_revision(ROOT) != controller_revision:
                raise CutoverError("operator_checkout_changed")
            present = guard.exists()
            if guard.is_symlink() or (
                present and guard.read_bytes() not in {blocked, relaxed}
            ):
                raise CutoverError("candidate_restart_guard_changed")
            _fixed_unit_preflight(
                revision,
                build,
                guarded=present,
                candidate=True,
                start_block=present and guard.read_bytes() == blocked,
                update_baseline=update_baseline,
            )
            _verify_candidate_runtime(
                root=root,
                unit=_FIXED_UNIT,
                checkout=checkout,
                origin="http://127.0.0.1:43110",
                executable=_FIXED_EXECUTABLE,
                expected_command=_candidate_override(checkout)
                .split("ExecStart=\nExecStart=", 1)[1]
                .strip()
                .split(),
            )

        try:
            return _finish_restored_baseline_engine(
                root,
                transition,
                unit=_FIXED_UNIT,
                guard=guard,
                expected_restart=data["baseline_restart"],
                verify_ready=verify,
                verify_after=verify,
                candidate=True,
            )
        except Exception:
            # Do not stop an unverified process or roll back a database after start.
            _reblock_current_update_on_failure(root, guard)
            raise


def start_restored_baseline() -> str:
    """Start the verified restored dashboard and restore its restart policy."""
    root = _FIXED_DATA
    controller_revision = _trusted_checkout_revision(ROOT)
    with _hold_transition_locks(root) as transition:
        data = _read_journal_at(transition)[0]
        phase = data.get("phase")
        facts = data.get("cutover_facts")
        if phase not in {
            "restore_activated",
            "baseline_start_attempted",
            "baseline_http_ready",
        } or not isinstance(facts, dict):
            raise CutoverError("baseline_restart_journal_invalid")
        candidate_revision, candidate_build, baseline_private = _fixed_journal_facts(
            facts, phase="migrated"
        )
        guard = _FIXED_OVERRIDE.parent / "95-m6-cutover-restart.conf"
        blocked = b"[Unit]\nRefuseManualStart=yes\n[Service]\nRestart=no\n"
        relaxed = b"[Service]\nRestart=no\n"

        def verify_controller() -> None:
            if _trusted_checkout_revision(ROOT) != controller_revision:
                raise CutoverError("operator_checkout_changed")

        def verify_before() -> None:
            verify_controller()
            _fixed_unit_preflight(
                candidate_revision,
                candidate_build,
                guarded=True,
                private_baseline=baseline_private,
            )

        def verify_after() -> None:
            verify_controller()
            _fixed_unit_preflight(
                candidate_revision,
                candidate_build,
                guarded=True,
                private_baseline=True,
                start_block=False,
            )

        try:
            if phase == "restore_activated":
                status = _start_restored_baseline_engine(
                    root,
                    transition,
                    facts,
                    unit=_FIXED_UNIT,
                    guard=guard,
                    override=_FIXED_OVERRIDE,
                    expected_override=(
                        _candidate_override(_FIXED_BASELINE)
                        if baseline_private
                        else build_override(_FIXED_BASELINE)
                    ).encode(),
                    start_override=_candidate_override(_FIXED_BASELINE).encode(),
                    baseline=_FIXED_BASELINE,
                    executable=_FIXED_EXECUTABLE,
                    verify_before=verify_before,
                    verify_after=verify_after,
                )
                if status != "baseline_started_readiness_unverified":
                    raise CutoverError("baseline_start_unverified")
            else:
                # A prior process may have started the baseline already. Never
                # restore an old database or issue another start on this path.
                if guard.is_symlink():
                    raise CutoverError("baseline_restart_guard_changed")
                guard_present = guard.exists()
                if not guard_present and phase != "baseline_http_ready":
                    raise CutoverError("baseline_restart_guard_changed")
                if guard_present and guard.read_bytes() not in {blocked, relaxed}:
                    raise CutoverError("baseline_restart_guard_changed")
                if (
                    not guard_present
                    and phase == "baseline_http_ready"
                    and _properties(_FIXED_UNIT).get("ActiveState")
                    in {"failed", "inactive"}
                ):
                    _create(guard, blocked)
                    guard_present = True
                _ctl("daemon-reload")
                current_override = _FIXED_OVERRIDE.read_bytes()
                private_override = _candidate_override(_FIXED_BASELINE).encode()
                original_override = build_override(_FIXED_BASELINE).encode()
                if current_override not in {private_override, original_override}:
                    raise CutoverError("baseline_restart_override_changed")
                private_now = current_override == private_override
                _fixed_unit_preflight(
                    candidate_revision,
                    candidate_build,
                    guarded=guard_present,
                    private_baseline=private_now,
                    start_block=guard_present and guard.read_bytes() == blocked,
                )
                if phase in {
                    "baseline_start_attempted",
                    "baseline_http_ready",
                } and _properties(_FIXED_UNIT).get("ActiveState") in {
                    "failed",
                    "inactive",
                }:
                    verify_controller()
                    if guard.read_bytes() == relaxed:
                        if not replace_override(guard, relaxed, blocked):
                            raise CutoverError("baseline_restart_guard_changed")
                        _ctl("daemon-reload")
                    _retry_stopped_baseline_engine(
                        root,
                        transition,
                        unit=_FIXED_UNIT,
                        guard=guard,
                        override=_FIXED_OVERRIDE,
                        baseline=_FIXED_BASELINE,
                        executable=_FIXED_EXECUTABLE,
                        verify_before=lambda: _fixed_unit_preflight(
                            candidate_revision,
                            candidate_build,
                            guarded=True,
                            private_baseline=private_now,
                        ),
                        verify_after=verify_after,
                    )

            def verify_ready(*, after_guard: bool = False) -> None:
                verify_controller()
                present = guard.exists()
                if after_guard and present:
                    raise CutoverError("baseline_restart_guard_changed")
                _fixed_unit_preflight(
                    candidate_revision,
                    candidate_build,
                    guarded=present,
                    private_baseline=True,
                    start_block=present and guard.read_bytes() == blocked,
                )
                current = _properties(_FIXED_UNIT)
                if current.get("ActiveState") != "active":
                    raise CutoverError("baseline_start_unverified")
                _verify_fixed_candidate_process(current, checkout=_FIXED_BASELINE)
                status, body = request("http://127.0.0.1:43110", "/login")
                if status != 200 or b"agentmonitor-dashboard-root" not in body:
                    raise CutoverError("baseline_http_unverified")

            return _finish_restored_baseline_engine(
                root,
                transition,
                unit=_FIXED_UNIT,
                guard=guard,
                expected_restart=facts["baseline_restart"],
                verify_ready=verify_ready,
                verify_after=lambda: verify_ready(after_guard=True),
            )
        except Exception:
            # Never signal a process whose identity or readiness is uncertain.
            # Once started, an old database snapshot must not be restored.
            try:
                if (
                    guard.is_file()
                    and not guard.is_symlink()
                    and guard.read_bytes() == relaxed
                ):
                    if not replace_override(guard, relaxed, blocked):
                        raise CutoverError("baseline_restart_guard_changed")
                    _ctl("daemon-reload")
            except Exception:  # noqa: BLE001 -- preserve closed recovery result.
                raise CutoverError("baseline_restart_block_unverified") from None
            raise


def main() -> int:
    if len(sys.argv) != 1:
        print("M6 CUTOVER: BLOCKED — this command accepts no target arguments")
        return 3
    try:
        result = cutover()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        print(
            "M6 CUTOVER: BLOCKED — review private transition journal and service state"
        )
        return 3
    print(f"M6 CUTOVER: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

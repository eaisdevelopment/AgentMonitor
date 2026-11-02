"""Candidate offline M6 cutover; caller must review recovery before use.

This command has not been run against the installed dashboard. It does not
claim M6 acceptance. It never signals a child process. Once candidate startup
is attempted it will not restore an old database snapshot automatically.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import secrets
import stat
import subprocess
import sys
from contextlib import ExitStack
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend/src"))

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    InspectSchemaCompatibilityV1,
    application_schema_range,
    load_migration_catalog,
)
from agentmonitor.composition.iam_operator import exclusive_service_quiescence

from tools.automation.implementations.auto_m6_local_activate import (
    TOOL_ROOT,
    build_override,
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
from tools.automation.implementations.m6_frontend_build import build_clean_frontend
from tools.automation.implementations.m6_migration_recovery import (
    _recover_migration_before_start,
)
from tools.automation.implementations.m6_offline_restore import (
    _read_private_json,
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
from tools.automation.implementations.m6_transition_lease import _hold_transition_locks


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
    path: Path, phase: str, backup_id: str | None = None, *, facts: dict | None = None
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
) -> str:
    """Migrate one selected unit. Call only after candidate has been reviewed.

    A crash leaves a private journal and is not automatically recovered. The
    caller must never rerun over that journal; inspect state first. The baseline
    override must be the exact existing generated override.
    """
    if source not in {"v1_0603", "v1_0707", "v1_0708"} or baseline == candidate:
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
    before = build_override(baseline).encode()
    after = (
        _candidate_override(candidate)
        if unit == _FIXED_UNIT
        else build_override(candidate)
    ).encode()
    if override.read_bytes() != before:
        raise CutoverError("override_changed")
    ref = DatabaseRefV1(data_root / "agentmonitor.db", data_root)
    ref.validate()
    view = InspectSchemaCompatibilityV1(
        ref, application_schema_range(), "runtime_read_write"
    )
    if view.current_revision != source or view.state != "upgrade_required":
        raise CutoverError("source_schema_invalid")
    baseline_props = _properties(unit)
    if baseline_props.get("ActiveState") != "active" or _cwd(unit) != str(baseline):
        raise CutoverError("service_identity_invalid")
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
    backup_id = "migration-preflight-" + secrets.token_hex(16)
    stop_receipt = None
    stop_attempted = False
    candidate_start_attempted = False
    operation_stack = ExitStack()
    barrier_stack = ExitStack()
    facts = {
        "unit": unit,
        "baseline_revision": _revision(baseline),
        "candidate_revision": expected_revision,
        "source_revision": source,
        "candidate_build_sha256": build_digest,
        "fixed_unit_sha256": _FIXED_UNIT_SHA256 if unit == _FIXED_UNIT else None,
        "fixed_baseline_override_sha256": _FIXED_OVERRIDE_SHA256
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
            _fixed_unit_preflight(expected_revision, build_digest, guarded=True)
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
        if outcome != "upgraded" or actual_backup_id != backup_id:
            raise CutoverError("migration_not_applied")
        _journal(journal, "migrated", backup_id, facts=facts)
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
                expected_revision, build_digest, guarded=True, candidate=True
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
            _verify_fixed_candidate_process(current)
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
_FIXED_CANDIDATE = _FIXED_DATA / "worktrees/m6-next"
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
        + " --host 127.0.0.1 --port 43110 --authenticated-dashboard --lan-host 192.168.1.18 --lan-network 192.168.1.0/24"
    )
    return build_override(candidate) + "ExecStart=\nExecStart=" + command + "\n"


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


def _fixed_unit_preflight(
    expected_revision: str,
    expected_build: str,
    *,
    guarded: bool = False,
    candidate: bool = False,
    start_block: bool = True,
) -> None:
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
            hashlib.sha256(_candidate_override(_FIXED_CANDIDATE).encode()).hexdigest()
            if candidate
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
        if candidate
        else str(
            _FIXED_DATA / "worktrees/m5-scheduled-quota-fix/backend/.venv/bin/python"
        )
    )
    if (
        fields.get("FragmentPath") != str(_FIXED_UNIT_FILE)
        or fields.get("DropInPaths")
        != (str(_FIXED_OVERRIDE) + (" " + str(guard_path) if guarded else ""))
        or fields.get("WorkingDirectory")
        != str(_FIXED_CANDIDATE if candidate else _FIXED_BASELINE)
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
        _revision(_FIXED_BASELINE) != _FIXED_BASELINE_REVISION
        or _revision(_FIXED_CANDIDATE) != expected_revision
        or tree_digest(_FIXED_CANDIDATE / "frontend/dist") != expected_build
        or _runtime_digest(_FIXED_VENV) != _FIXED_VENV_SHA256
        or hashlib.sha256(_FIXED_EXECUTABLE.read_bytes()).hexdigest()
        != _FIXED_PYTHON_SHA256
    ):
        raise CutoverError("release_identity_changed")
    # Do not execute candidate or private-runtime code until the pinned files
    # and clean source revision have passed the static checks above.
    _check_candidate_schema(_FIXED_CANDIDATE)


def _verify_fixed_candidate_process(properties: dict[str, str]) -> None:
    pid = int(properties.get("MainPID", "0"))
    group = properties.get("ControlGroup", "")
    invocation = properties.get("InvocationID", "")
    start = properties.get("ExecMainStartTimestampMonotonic", "")
    if pid <= 1 or not invocation or not start:
        raise CutoverError("candidate_identity_invalid")
    descriptor = os.pidfd_open(pid, 0)
    try:
        before = _process_identity(pid, group)
        expected = _FIXED_EXECUTABLE.stat()
        if before[1:] != (expected.st_dev, expected.st_ino):
            raise CutoverError("candidate_executable_invalid")
        fd = os.open(f"/proc/{pid}/cmdline", os.O_RDONLY | os.O_CLOEXEC)
        try:
            actual = os.read(fd, 16385)
        finally:
            os.close(fd)
        expected_command = (
            _candidate_override(_FIXED_CANDIDATE)
            .split("ExecStart=\nExecStart=", 1)[1]
            .strip()
            .split()
        )
        expected_cmdline = (
            b"\0".join(part.encode() for part in expected_command) + b"\0"
        )
        if actual != expected_cmdline or _process_identity(pid, group) != before:
            raise CutoverError("candidate_process_changed")
        current = _properties(_FIXED_UNIT)
        if (
            current.get("MainPID") != str(pid)
            or current.get("ControlGroup") != group
            or current.get("InvocationID") != invocation
            or current.get("ExecMainStartTimestampMonotonic") != start
        ):
            raise CutoverError("candidate_process_changed")
    finally:
        os.close(descriptor)


def cutover() -> str:
    """Cut over only the code-owned AgentMonitor service and pinned releases."""
    with _hold_transition_locks(_FIXED_DATA) as transition:
        candidate_revision, candidate_build = build_clean_frontend(
            _FIXED_CANDIDATE, _FIXED_DATA, TOOL_ROOT / "frontend/node_modules"
        )
        transition.validate(_FIXED_DATA)
        _fixed_unit_preflight(candidate_revision, candidate_build)
    return _cutover_engine(
        unit=_FIXED_UNIT,
        data_root=_FIXED_DATA,
        baseline=_FIXED_BASELINE,
        candidate=_FIXED_CANDIDATE,
        override=_FIXED_OVERRIDE,
        source="v1_0707",
        expected_revision=candidate_revision,
        expected_build=candidate_build,
        expected_executable=_FIXED_EXECUTABLE,
    )


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
        receipt = data.get("stop_receipt")
        candidate_revision = data.get("candidate_revision")
        candidate_build = data.get("candidate_build_sha256")
        executable = _FIXED_EXECUTABLE.stat()
        if (
            data.get("format") != "m6-cutover.v1"
            or data.get("phase") != "stopped"
            or data.get("unit") != _FIXED_UNIT
            or data.get("source_revision") != "v1_0707"
            or data.get("baseline_revision") != _FIXED_BASELINE_REVISION
            or data.get("fixed_unit_sha256") != _FIXED_UNIT_SHA256
            or data.get("fixed_baseline_override_sha256") != _FIXED_OVERRIDE_SHA256
            or data.get("fixed_runtime_sha256") != _FIXED_VENV_SHA256
            or data.get("fixed_python_sha256") != _FIXED_PYTHON_SHA256
            or not isinstance(receipt, dict)
            or receipt.get("unit") != _FIXED_UNIT
            or receipt.get("executable_identity")
            != [executable.st_dev, executable.st_ino]
            or not isinstance(candidate_revision, str)
            or re.fullmatch(r"[a-f0-9]{40}", candidate_revision) is None
            or not isinstance(candidate_build, str)
            or re.fullmatch(r"[a-f0-9]{64}", candidate_build) is None
        ):
            raise CutoverError("migration_recovery_target_invalid")
        transition.validate(root)
        _fixed_unit_preflight(candidate_revision, candidate_build, guarded=True)

        def verify_recovery_provenance() -> None:
            verify_controller()
            _fixed_unit_preflight(candidate_revision, candidate_build, guarded=True)

        return _recover_migration_engine(
            root,
            transition,
            data,
            verify_provenance=verify_recovery_provenance,
        )


def _recover_migration_engine(
    root: Path, transition, expected_journal: dict, *, verify_provenance=None
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

"""Isolated main-process stop primitive; not a deployment or restore command.

Callers must establish the target's identity and cooperative deployment lock.
This module intentionally has no CLI and never modifies service configuration.
"""

from __future__ import annotations

import os
import re
import signal
import subprocess
import time
from pathlib import Path


class QuiescentStopError(RuntimeError):
    """Closed, non-sensitive inability to establish safe quiescence."""


def _properties(unit: str) -> dict[str, str]:
    if re.fullmatch(r"[A-Za-z0-9_.@:-]+\.service", unit) is None:
        raise QuiescentStopError("unit_invalid")
    result = subprocess.run(
        [
            "systemctl",
            "--user",
            "show",
            unit,
            "-p",
            "MainPID",
            "-p",
            "ControlGroup",
            "-p",
            "Restart",
            "-p",
            "ActiveState",
            "-p",
            "RefuseManualStart",
            "-p",
            "InvocationID",
            "-p",
            "ExecMainStartTimestampMonotonic",
        ],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if result.returncode:
        raise QuiescentStopError("unit_unavailable")
    return dict(
        line.split("=", 1) for line in result.stdout.splitlines() if "=" in line
    )


def _process_identity(pid: int, cgroup: str) -> tuple[str, int, int]:
    root = Path("/proc") / str(pid)
    if root.stat().st_uid != os.getuid():
        raise QuiescentStopError("unit_uid_mismatch")
    lines = (root / "cgroup").read_text().splitlines()
    if lines != ["0::" + cgroup]:
        raise QuiescentStopError("unit_cgroup_mismatch")
    fields = (root / "stat").read_text().rpartition(") ")[2].split()
    if len(fields) < 20:
        raise QuiescentStopError("unit_identity_unavailable")
    executable = (root / "exe").stat()
    return fields[19], executable.st_dev, executable.st_ino


def _frozen_without_children(pid: int, cgroup: str) -> bool:
    if not cgroup.startswith("/user.slice/") or ".." in Path(cgroup).parts:
        return False
    root = Path("/sys/fs/cgroup") / cgroup.lstrip("/")
    if not root.is_dir() or root.is_symlink():
        return False
    try:
        tasks = sorted((Path("/proc") / str(pid) / "task").iterdir())
        if not tasks:
            return False
        for task in tasks:
            state = next(
                line
                for line in (task / "status").read_text().splitlines()
                if line.startswith("State:")
            )
            if state.split()[1] not in {"T", "t"}:
                return False
            if (task / "children").read_text().strip():
                return False
        members: set[int] = set()
        for directory, child_dirs, files in os.walk(root, followlinks=False):
            if any((Path(directory) / child).is_symlink() for child in child_dirs):
                return False
            if "cgroup.procs" not in files:
                return False
            members.update(
                int(item)
                for item in (Path(directory) / "cgroup.procs").read_text().split()
            )
        if members != {pid}:
            return False
        return tasks == sorted((Path("/proc") / str(pid) / "task").iterdir())
    except (OSError, ValueError, StopIteration):
        return False


def stop_quiescent_unit(
    unit: str,
    *,
    expected_pid: int,
    expected_cgroup: str,
    expected_start_ticks: str,
    expected_executable_identity: tuple[int, int],
    expected_invocation_id: str,
    expected_start_monotonic: str,
) -> str:
    """Freeze, inspect, and kill only the exact main PID; resume on refusal.

    Only call after independent executable/start-identity proof and exclusive
    operator authorization. Restart must already be disabled and verified.
    """
    props = _properties(unit)
    if (
        props.get("Restart") != "no"
        or props.get("ActiveState") != "active"
        or props.get("RefuseManualStart") != "yes"
    ):
        raise QuiescentStopError("unit_not_quiescent_ready")
    try:
        pid = int(props["MainPID"])
        cgroup = props["ControlGroup"]
        if (
            pid != expected_pid
            or cgroup != expected_cgroup
            or props.get("InvocationID") != expected_invocation_id
            or props.get("ExecMainStartTimestampMonotonic") != expected_start_monotonic
        ):
            raise QuiescentStopError("unit_identity_changed")
        if pid <= 1:
            raise ValueError
        descriptor = os.pidfd_open(pid)
    except (KeyError, ValueError, OSError) as error:
        raise QuiescentStopError("unit_identity_unavailable") from error
    killed = False
    frozen = False
    try:
        identity = _process_identity(pid, cgroup)
        if (
            identity[0] != expected_start_ticks
            or identity[1:] != expected_executable_identity
            or _properties(unit) != props
        ):
            raise QuiescentStopError("unit_identity_changed")
        if not props.get("InvocationID") or props.get(
            "ExecMainStartTimestampMonotonic"
        ) in {None, "0"}:
            raise QuiescentStopError("unit_identity_unavailable")
        signal.pidfd_send_signal(descriptor, signal.SIGSTOP)
        frozen = True
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if _frozen_without_children(pid, cgroup):
                break
            time.sleep(0.025)
        else:
            raise QuiescentStopError("unit_has_children_or_not_stopped")
        if (
            _properties(unit) != props
            or _process_identity(pid, cgroup) != identity
            or not _frozen_without_children(pid, cgroup)
        ):
            raise QuiescentStopError("unit_changed")
        signal.pidfd_send_signal(descriptor, signal.SIGKILL)
        killed = True
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            current = _properties(unit)
            if current.get("MainPID") == "0" and current.get("ActiveState") in {
                "failed",
                "inactive",
            }:
                return "stopped"
            time.sleep(0.025)
        raise QuiescentStopError("unit_stop_unconfirmed")
    except OSError as error:
        raise QuiescentStopError("unit_signal_unavailable") from error
    finally:
        if frozen and not killed:
            try:
                signal.pidfd_send_signal(descriptor, signal.SIGCONT)
            except ProcessLookupError:
                pass
        os.close(descriptor)

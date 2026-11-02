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


def stop_quiescent_unit(unit: str) -> str:
    """Freeze, inspect, and kill only the exact main PID; resume on refusal.

    Only call after independent executable/start-identity proof and exclusive
    operator authorization. Restart must already be disabled and verified.
    """
    props = _properties(unit)
    if props.get("Restart") != "no" or props.get("ActiveState") != "active":
        raise QuiescentStopError("unit_not_quiescent_ready")
    try:
        pid = int(props["MainPID"])
        cgroup = props["ControlGroup"]
        if pid <= 1:
            raise ValueError
        descriptor = os.pidfd_open(pid)
    except (KeyError, ValueError, OSError) as error:
        raise QuiescentStopError("unit_identity_unavailable") from error
    killed = False
    frozen = False
    try:
        signal.pidfd_send_signal(descriptor, signal.SIGSTOP)
        frozen = True
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if _frozen_without_children(pid, cgroup):
                break
            time.sleep(0.025)
        else:
            raise QuiescentStopError("unit_has_children_or_not_stopped")
        if _properties(unit) != props or not _frozen_without_children(pid, cgroup):
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

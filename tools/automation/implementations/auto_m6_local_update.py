"""Preflight for a future M6 local dashboard update; never changes the service."""

from __future__ import annotations

import argparse
import hashlib
import os
import stat
import subprocess
from pathlib import Path

from tools.automation.implementations.auto_m6_local_activate import (
    DROPIN,
    ORIGINS,
    ROOT,
    SERVICE_PYTHON,
    UNIT,
    UNIT_FILE,
    build_override,
    cgroup_pids,
    ctl,
    login_identity,
    prop,
    safe_cgroup,
    service_identity,
)
from tools.automation.implementations.m5_service_activation import (
    acquire_m5_service_activation_lock_v1,
    release_m5_service_activation_lock_v1,
    validate_m5_service_activation_lock_v1,
)
from tools.automation.implementations.m6_local_update_policy import update_preflight

BASELINE = Path("/home/dev/.local/share/agentmonitor/worktrees/m6-integration")


def revision(root: Path) -> str:
    status = subprocess.run(
        ["/usr/bin/git", "status", "--porcelain"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if status.returncode or status.stdout:
        raise RuntimeError("checkout_not_clean")
    result = subprocess.run(
        ["/usr/bin/git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    value = result.stdout.strip()
    if (
        result.returncode
        or len(value) != 40
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise RuntimeError("revision_unavailable")
    return value


def service_snapshot() -> tuple[tuple[int, str, str], str, tuple[tuple[str, str], ...]]:
    if ctl("is-active", "--quiet", UNIT).returncode:
        raise RuntimeError("dashboard_not_active")
    if prop("FragmentPath") != str(UNIT_FILE) or prop("WorkingDirectory") != str(
        BASELINE
    ):
        raise RuntimeError("unexpected_dashboard_configuration")
    if prop("KillMode") != "control-group" or prop("DropInPaths").split() != [
        str(DROPIN)
    ]:
        raise RuntimeError("unexpected_dashboard_dropin")
    if "path=" + str(SERVICE_PYTHON) not in prop("ExecStart"):
        raise RuntimeError("unexpected_dashboard_executable")
    unit = UNIT_FILE.lstat()
    metadata = DROPIN.lstat()
    if (
        not stat.S_ISREG(unit.st_mode)
        or not stat.S_ISREG(metadata.st_mode)
        or unit.st_uid != os.getuid()
        or metadata.st_uid != os.getuid()
        or unit.st_mode & 0o022
        or metadata.st_mode & 0o022
    ):
        raise RuntimeError("unsafe_dashboard_configuration")
    original = DROPIN.read_bytes()
    if original != build_override(BASELINE).encode():
        raise RuntimeError("unexpected_dashboard_override")
    identity = service_identity()
    if not safe_cgroup(identity[0], cgroup_pids(identity[2])):
        raise RuntimeError("dashboard_has_unclassified_children")
    actual = tuple(login_identity(origin) for origin in ORIGINS)
    return identity, hashlib.sha256(original).hexdigest(), actual


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    held = None
    try:
        held = acquire_m5_service_activation_lock_v1()
        old = (str(BASELINE), revision(BASELINE))
        candidate = (str(ROOT), revision(ROOT))
        snapshot = service_snapshot()
        validate_m5_service_activation_lock_v1(held)
        if not update_preflight(
            old,
            (str(BASELINE), revision(BASELINE)),
            candidate,
            (str(ROOT), revision(ROOT)),
            snapshot == service_snapshot(),
        ):
            raise RuntimeError("dashboard_changed_during_preflight")
        print(
            "M6 LOCAL UPDATE PREFLIGHT: PASSED — current service and source trees stable"
        )
        print("M6 LOCAL UPDATE: NOT IMPLEMENTED — no service changes were made")
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"M6 LOCAL UPDATE PREFLIGHT: BLOCKED — {exc}")
        return 3
    finally:
        if held is not None:
            release_m5_service_activation_lock_v1(held)


if __name__ == "__main__":
    raise SystemExit(main())

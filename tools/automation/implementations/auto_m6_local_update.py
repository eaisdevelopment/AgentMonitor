"""Bounded M6 local dashboard update, with guarded rollback."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import signal
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

from tools.automation.implementations.auto_m6_local_activate import (
    DROPIN,
    OLD_ROOT,
    ORIGINS,
    ROOT,
    SERVICE_PYTHON,
    TOOL_ROOT,
    UNIT,
    UNIT_FILE,
    build_override,
    candidate_runtime,
    cgroup_pids,
    create_tool_link,
    ctl,
    login_identity,
    prop,
    safe_cgroup,
    service_identity,
    tree_digest,
    wait_ready,
)
from tools.automation.implementations.auto_m6_local_admit import source_digest
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


def replace_override(path: Path, expected: bytes, replacement: bytes) -> bool:
    """Replace an unchanged owner-only file; callers must hold the service lock.

    The inode/content checks are not a compare-and-swap against non-cooperating
    processes. The caller must still verify resulting service state.
    """
    metadata = path.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_mode & 0o077
        or path.read_bytes() != expected
    ):
        return False
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=".agentmonitor-update-", delete=False
        ) as handle:
            temporary = Path(handle.name)
            os.fchmod(handle.fileno(), 0o600)
            handle.write(replacement)
            handle.flush()
            os.fsync(handle.fileno())
        current = path.lstat()
        if (current.st_dev, current.st_ino) != (
            metadata.st_dev,
            metadata.st_ino,
        ) or path.read_bytes() != expected:
            return False
        os.replace(temporary, path)
        temporary = None
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return True
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def prepare_candidate(expected_revision: str) -> tuple[str, str]:
    """Build and test a clean candidate without changing the running service."""
    links: list[tuple[Path, Path]] = []
    try:
        for path, target in (
            (ROOT / "backend/.venv", OLD_ROOT / "backend/.venv"),
            (ROOT / "frontend/node_modules", TOOL_ROOT / "frontend/node_modules"),
        ):
            if create_tool_link(path, target):
                links.append((path, target))
        result = subprocess.run(
            [sys.executable, "tools/automation/run.py", "AUTO-M6-LOCAL-ADMIT"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=240,
            check=False,
        )
        match = re.search(
            r"Selected source-and-test digest: ([0-9a-f]{64})", result.stdout
        )
        if result.returncode or match is None or match.group(1) != source_digest():
            raise RuntimeError("candidate_admission_failed")
        source = match.group(1)
        build = tree_digest(ROOT / "frontend/dist")
    finally:
        for path, target in reversed(links):
            if not path.is_symlink() or path.resolve(strict=True) != target.resolve(
                strict=True
            ):
                raise RuntimeError("temporary_tool_link_changed")
            path.unlink()
    if revision(ROOT) != expected_revision or source_digest() != source:
        raise RuntimeError("candidate_changed_during_admission")
    return source, build


def apply_update(held, old, candidate, snapshot) -> None:
    """Apply one prepared update; never restart unclassified service children."""
    source, build = prepare_candidate(candidate[1])
    page = (ROOT / "frontend/dist/dashboard.html").read_bytes()
    match = re.search(rb'src="(/assets/[A-Za-z0-9_.-]+\.js)"', page)
    if match is None:
        raise RuntimeError("candidate_asset_missing")
    asset = ROOT / "frontend/dist" / match.group(1).decode("ascii").lstrip("/")
    if asset.is_symlink() or not asset.is_file():
        raise RuntimeError("candidate_asset_invalid")
    expected = (
        hashlib.sha256(page).hexdigest(),
        hashlib.sha256(asset.read_bytes()).hexdigest(),
    )
    validate_m5_service_activation_lock_v1(held)
    if (
        service_snapshot() != snapshot
        or revision(BASELINE) != old[1]
        or revision(ROOT) != candidate[1]
        or source_digest() != source
        or tree_digest(ROOT / "frontend/dist") != build
    ):
        raise RuntimeError("dashboard_or_candidate_changed")
    before = build_override(BASELINE).encode()
    after = build_override(ROOT).encode()
    unit_hash = hashlib.sha256(UNIT_FILE.read_bytes()).hexdigest()
    switched = False
    restarted = False
    job_unknown = False
    candidate_identity = None
    try:
        # Replacement may succeed before a later fsync failure is reported.
        switched = True
        if not replace_override(DROPIN, before, after):
            switched = False
            raise RuntimeError("dashboard_override_changed")
        validate_m5_service_activation_lock_v1(held)
        if (
            service_identity() != snapshot[0]
            or not safe_cgroup(snapshot[0][0], cgroup_pids(snapshot[0][2]))
            or revision(BASELINE) != old[1]
            or revision(ROOT) != candidate[1]
            or source_digest() != source
            or tree_digest(ROOT / "frontend/dist") != build
            or hashlib.sha256(UNIT_FILE.read_bytes()).hexdigest() != unit_hash
        ):
            raise RuntimeError("dashboard_or_candidate_changed")
        job_unknown = True
        reload_result = ctl("daemon-reload")
        job_unknown = False
        if reload_result.returncode:
            raise RuntimeError("dashboard_reload_failed")
        if service_identity() != snapshot[0] or not safe_cgroup(
            snapshot[0][0], cgroup_pids(snapshot[0][2])
        ):
            raise RuntimeError("dashboard_became_busy")
        job_unknown = True
        restarted = True
        result = ctl("restart", UNIT)
        job_unknown = False
        if result.returncode:
            raise RuntimeError("dashboard_restart_failed")
        candidate_identity = service_identity()
        if (
            not wait_ready((expected, expected), candidate=True)
            or not candidate_runtime()
        ):
            raise RuntimeError("candidate_not_ready")
        if (
            revision(ROOT) != candidate[1]
            or source_digest() != source
            or tree_digest(ROOT / "frontend/dist") != build
        ):
            raise RuntimeError("candidate_changed_after_restart")
        switched = False
        print("M6 LOCAL UPDATE: PASSED — candidate running on loopback and LAN")
    except BaseException:
        if switched:
            if job_unknown:
                print(
                    "M6 LOCAL UPDATE: rollback requires attention — systemd job status unknown"
                )
            elif hashlib.sha256(UNIT_FILE.read_bytes()).hexdigest() != unit_hash:
                print("M6 LOCAL UPDATE: rollback blocked — service unit changed")
            elif DROPIN.read_bytes() != after:
                print("M6 LOCAL UPDATE: rollback blocked — override changed")
            else:
                current = service_identity()
                pids = cgroup_pids(snapshot[0][2], allow_missing=True)
                # Restoring a drop-in without a restart cannot terminate children.
                safe = not restarted and current == snapshot[0]
                safe |= (
                    restarted
                    and candidate_identity is not None
                    and current == candidate_identity
                    and safe_cgroup(current[0], pids)
                )
                safe |= (
                    restarted
                    and candidate_identity is None
                    and current[0] == 0
                    and not pids
                    and prop("ActiveState") in {"inactive", "failed"}
                )
                if not safe:
                    print(
                        "M6 LOCAL UPDATE: rollback blocked — service changed or has children"
                    )
                elif (
                    not replace_override(DROPIN, after, before)
                    or ctl("daemon-reload").returncode
                ):
                    print(
                        "M6 LOCAL UPDATE: rollback requires attention — configuration restore failed"
                    )
                elif restarted and (
                    ctl("restart" if current[0] else "start", UNIT).returncode
                    or not wait_ready(snapshot[2], candidate=False)
                ):
                    print(
                        "M6 LOCAL UPDATE: rollback requires attention — original dashboard not ready"
                    )
                else:
                    print("M6 LOCAL UPDATE: original configuration restored")
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--prepare", action="store_true")
    options = parser.parse_args()
    if options.apply and options.prepare:
        parser.error("--apply already prepares the candidate")
    if options.apply:
        print("M6 LOCAL UPDATE: BLOCKED — restart safety review not complete")
        return 3
    held = None
    old_signal = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        held = acquire_m5_service_activation_lock_v1()
        old = (str(BASELINE), revision(BASELINE))
        candidate = (str(ROOT), revision(ROOT))
        snapshot = service_snapshot()
        if options.prepare:
            prepared_source, prepared_build = prepare_candidate(candidate[1])
            print(
                f"M6 LOCAL UPDATE: candidate admission passed; source {prepared_source}, build {prepared_build}"
            )
        validate_m5_service_activation_lock_v1(held)
        if not update_preflight(
            old,
            (str(BASELINE), revision(BASELINE)),
            candidate,
            (str(ROOT), revision(ROOT)),
            snapshot == service_snapshot(),
        ):
            raise RuntimeError("dashboard_changed_during_preflight")
        if options.apply:
            apply_update(held, old, candidate, snapshot)
        else:
            print("M6 LOCAL UPDATE PREFLIGHT: PASSED — no service changes were made")
        return 0
    except (
        OSError,
        ValueError,
        RuntimeError,
        subprocess.SubprocessError,
        KeyboardInterrupt,
    ) as exc:
        print(f"M6 LOCAL UPDATE: FAILED — {exc or 'interrupted'}")
        return 3
    finally:
        if held is not None:
            release_m5_service_activation_lock_v1(held)
        signal.signal(signal.SIGTERM, old_signal)


if __name__ == "__main__":
    raise SystemExit(main())

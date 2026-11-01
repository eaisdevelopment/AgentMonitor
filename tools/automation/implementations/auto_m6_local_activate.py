"""Controlled local dashboard rollout; never controls user agent processes.

The endpoint check is deliberately unauthenticated. It does not claim a live
browser/account verification or full M6 completion. A cooperative lock cannot
prevent unrelated tools or a child spawn between the final cgroup check and
systemd restart. Crash/SIGKILL recovery requires manual inspection; no
power-loss atomicity is claimed.
"""

from __future__ import annotations

import hashlib
import os
import re
import signal
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from tools.automation.implementations.auto_m6_local_admit import source_digest
from tools.automation.implementations.m5_service_activation import (
    acquire_m5_service_activation_lock_v1,
    release_m5_service_activation_lock_v1,
    validate_m5_service_activation_lock_v1,
)

ROOT = Path(__file__).resolve().parents[3]
DATA = Path("/home/dev/.local/share/agentmonitor")
EXPECTED_ROOT = DATA / "worktrees/m6-integration"
OLD_ROOT = DATA / "worktrees/m5-scheduled-quota-fix"
TOOL_ROOT = DATA / "worktrees/dashboard-product-promotion"
SERVICE_PYTHON = OLD_ROOT / "backend/.venv/bin/python"
UNIT = "agentmonitor-dashboard.service"
UNIT_FILE = Path("/home/dev/.config/systemd/user") / UNIT
DROPIN_DIR = UNIT_FILE.parent / (UNIT + ".d")
DROPIN = DROPIN_DIR / "90-m6-local.conf"
ORIGINS = ("http://127.0.0.1:43110", "http://192.168.1.18:43110")
MAX_BYTES = 2 * 1024 * 1024


def build_override(root: Path) -> str:
    text = str(root)
    if not re.fullmatch(r"/[A-Za-z0-9_./-]+", text):
        raise ValueError("checkout_path_invalid")
    return f"[Service]\nWorkingDirectory={text}\nEnvironment=PYTHONPATH={text}/backend/src\n"


def activation_preflight(proofs: frozenset[str]) -> tuple[str, ...]:
    """Pure checklist; labels alone never establish real-world readiness."""
    required = (
        "quiescence",
        "authenticated_dual_listener",
        "runtime_identity",
        "candidate_identity",
        "rollback_identity",
        "exclusive_transition",
    )
    return tuple(value for value in required if value not in proofs)


def safe_cgroup(main_pid: int, pids: frozenset[int]) -> bool:
    """A snapshot admits only the dashboard parent and no unclassified child."""
    return main_pid > 1 and pids == frozenset({main_pid})


def clean_status(lines: tuple[str, ...]) -> bool:
    return all(
        line in {"?? backend/.venv", "?? frontend/node_modules"} for line in lines
    )


def same_identity(expected: tuple[int, int] | None, actual: tuple[int, int]) -> bool:
    return expected is not None and expected == actual


def rollback_permitted(
    expected: tuple[int, str, str] | None,
    current: tuple[int, str, str],
    pids: frozenset[int],
    job_unknown: bool,
) -> bool:
    """Never restart an unclassified or changed candidate, or overlap a job."""
    return (
        not job_unknown
        and expected is not None
        and expected == current
        and safe_cgroup(current[0], pids)
    )


def inactive_start_permitted(
    state: str, main_pid: int, pids: frozenset[int], job_unknown: bool
) -> bool:
    """Only start an old service if the stopped unit has no remaining tasks."""
    return (
        not job_unknown
        and state in {"inactive", "failed"}
        and main_pid == 0
        and not pids
    )


def ctl(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/usr/bin/systemctl", "--user", *args],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def prop(name: str) -> str:
    result = ctl("show", UNIT, "--property=" + name, "--value")
    if result.returncode:
        raise RuntimeError("service_property_unavailable")
    return result.stdout.strip()


def service_identity() -> tuple[int, str, str]:
    return (
        int(prop("MainPID")),
        prop("ExecMainStartTimestampMonotonic"),
        prop("ControlGroup"),
    )


def unit_snapshot() -> tuple[str, str, int, str]:
    if ctl("is-active", "--quiet", UNIT).returncode:
        raise RuntimeError("service_not_active")
    fragment = prop("FragmentPath")
    if fragment != str(UNIT_FILE) or prop("DropInPaths"):
        raise RuntimeError("unexpected_service_configuration")
    if prop("KillMode") != "control-group" or prop("WorkingDirectory") != str(OLD_ROOT):
        raise RuntimeError("unexpected_service_runtime")
    exec_start = prop("ExecStart")
    if "path=" + str(SERVICE_PYTHON) not in exec_start:
        raise RuntimeError("unexpected_service_interpreter")
    st = UNIT_FILE.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o022:
        raise RuntimeError("unsafe_service_unit")
    unit_hash = hashlib.sha256(UNIT_FILE.read_bytes()).hexdigest()
    return (
        unit_hash,
        prop("ControlGroup"),
        int(prop("MainPID")),
        prop("ExecMainStartTimestampMonotonic"),
    )


def candidate_runtime() -> bool:
    pid = int(prop("MainPID"))
    if pid <= 1 or prop("WorkingDirectory") != str(ROOT):
        return False
    if str(DROPIN) not in prop("DropInPaths").split():
        return False
    return Path(f"/proc/{pid}/cwd").resolve(strict=True) == ROOT and Path(
        f"/proc/{pid}/exe"
    ).resolve(strict=True) == SERVICE_PYTHON.resolve(strict=True)


def cgroup_pids(group: str, *, allow_missing: bool = False) -> frozenset[int]:
    if not re.fullmatch(
        r"/user\.slice/user-[0-9]+\.slice/user@[0-9]+\.service/app\.slice/agentmonitor-dashboard\.service",
        group,
    ):
        raise RuntimeError("unexpected_service_cgroup")
    root = Path("/sys/fs/cgroup") / group.lstrip("/")
    if allow_missing and not root.exists() and not root.is_symlink():
        return frozenset()
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("service_cgroup_unavailable")
    paths = [root / "cgroup.procs", *root.glob("**/cgroup.procs")]
    pids: set[int] = set()
    for path in paths:
        if path.is_symlink():
            raise RuntimeError("unsafe_service_cgroup")
        content = path.read_text()
        pids.update(int(value) for value in content.split())
    return frozenset(pids)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(origin: str, path: str) -> tuple[int, bytes]:
    if origin not in ORIGINS or not re.fullmatch(
        r"/(?:login|api/v1/providers/ollama/local-catalog|assets/[A-Za-z0-9_.-]+\.js)",
        path,
    ):
        raise ValueError("readiness_target_invalid")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(origin + path, timeout=3) as response:
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ValueError("readiness_response_large")
            return response.status, body
    except urllib.error.HTTPError as error:
        return error.code, b""


def login_identity(origin: str) -> tuple[str, str]:
    status, page = request(origin, "/login")
    if status != 200 or b"agentmonitor-dashboard-root" not in page:
        raise RuntimeError("login_not_ready")
    script = re.search(rb'src="(/assets/[A-Za-z0-9_.-]+\.js)"', page)
    if script is None:
        raise RuntimeError("dashboard_asset_missing")
    asset_status, asset = request(origin, script.group(1).decode("ascii"))
    if asset_status != 200:
        raise RuntimeError("dashboard_asset_unavailable")
    return hashlib.sha256(page).hexdigest(), hashlib.sha256(asset).hexdigest()


def tree_digest(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_symlink() or not path.is_dir():
        raise RuntimeError("build_unavailable")
    for item in sorted(path.rglob("*")):
        if item.is_symlink():
            raise RuntimeError("build_symlink")
        if item.is_file():
            digest.update(
                str(item.relative_to(path)).encode() + b"\0" + item.read_bytes()
            )
    return digest.hexdigest()


def clean_revision() -> str:
    status = subprocess.run(
        ["/usr/bin/git", "status", "--porcelain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if status.returncode or not clean_status(tuple(status.stdout.splitlines())):
        raise RuntimeError("checkout_not_clean")
    revision = subprocess.run(
        ["/usr/bin/git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if revision.returncode or not re.fullmatch(r"[0-9a-f]{40}\n", revision.stdout):
        raise RuntimeError("checkout_revision_unavailable")
    return revision.stdout.strip()


def create_tool_link(path: Path, target: Path) -> bool:
    if path.is_symlink() and path.resolve(strict=True) == target.resolve(strict=True):
        return False
    if path.exists() or path.is_symlink() or not target.exists():
        raise RuntimeError("tool_environment_unavailable")
    path.symlink_to(target, target_is_directory=True)
    return True


def wait_ready(expected: tuple[tuple[str, str], ...], candidate: bool) -> bool:
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        try:
            if ctl("is-active", "--quiet", UNIT).returncode == 0:
                actual = tuple(login_identity(origin) for origin in ORIGINS)
                if actual == expected and (
                    not candidate
                    or all(
                        request(origin, "/api/v1/providers/ollama/local-catalog")[0]
                        in {401, 403}
                        for origin in ORIGINS
                    )
                ):
                    return True
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
            pass
        time.sleep(1)
    return False


def main() -> int:
    if ROOT != EXPECTED_ROOT:
        print("M6 LOCAL ACTIVATION: BLOCKED — wrong checkout")
        return 3
    override = build_override(ROOT)
    held = None
    links: list[tuple[Path, Path]] = []
    created_dir = False
    created_dropin = False
    dropin_identity: tuple[int, int] | None = None
    activated = False
    restarted = False
    job_unknown = False
    candidate_identity: tuple[int, str, str] | None = None
    cleanup_failed = False
    baseline: tuple[tuple[str, str], ...] | None = None
    old_snapshot: tuple[str, str, int, str] | None = None
    old_signal = signal.getsignal(signal.SIGTERM)

    def interrupt(_signum, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupt)
    try:
        held = acquire_m5_service_activation_lock_v1()
        revision = clean_revision()
        old_snapshot = unit_snapshot()
        if not safe_cgroup(old_snapshot[2], cgroup_pids(old_snapshot[1])):
            raise RuntimeError("service_has_unclassified_children")
        baseline = tuple(login_identity(origin) for origin in ORIGINS)
        for path, target in (
            (ROOT / "backend/.venv", OLD_ROOT / "backend/.venv"),
            (ROOT / "frontend/node_modules", TOOL_ROOT / "frontend/node_modules"),
        ):
            if create_tool_link(path, target):
                links.append((path, target))
        admission = subprocess.run(
            [sys.executable, "tools/automation/run.py", "AUTO-M6-LOCAL-ADMIT"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=240,
            check=False,
        )
        if admission.returncode:
            raise RuntimeError("local_admission_failed")
        match = re.search(
            r"Selected source-and-test digest: ([0-9a-f]{64})", admission.stdout
        )
        if not match or match.group(1) != source_digest():
            raise RuntimeError("admission_digest_mismatch")
        selected_source = match.group(1)
        build = tree_digest(ROOT / "frontend/dist")
        candidate_page = (ROOT / "frontend/dist/dashboard.html").read_bytes()
        candidate_script = re.search(
            rb'src="(/assets/[A-Za-z0-9_.-]+\.js)"', candidate_page
        )
        if candidate_script is None:
            raise RuntimeError("candidate_asset_missing")
        asset_path = (
            ROOT
            / "frontend/dist"
            / candidate_script.group(1).decode("ascii").lstrip("/")
        )
        if not asset_path.is_file() or asset_path.is_symlink():
            raise RuntimeError("candidate_asset_invalid")
        asset = asset_path.read_bytes()
        if b"Ollama local models" not in asset:
            raise RuntimeError("candidate_ui_missing")
        expected = (
            hashlib.sha256(candidate_page).hexdigest(),
            hashlib.sha256(asset).hexdigest(),
        )
        for path, target in reversed(links):
            if not path.is_symlink() or path.resolve(strict=True) != target.resolve(
                strict=True
            ):
                raise RuntimeError("tool_environment_changed")
            path.unlink()
        links.clear()
        validate_m5_service_activation_lock_v1(held)
        if (
            clean_revision() != revision
            or source_digest() != selected_source
            or tree_digest(ROOT / "frontend/dist") != build
        ):
            raise RuntimeError("candidate_changed")
        if unit_snapshot() != old_snapshot or not safe_cgroup(
            old_snapshot[2], cgroup_pids(old_snapshot[1])
        ):
            raise RuntimeError("service_changed_or_busy")
        if DROPIN_DIR.is_symlink() or DROPIN.exists() or DROPIN.is_symlink():
            raise RuntimeError("existing_dropin")
        if not DROPIN_DIR.exists():
            DROPIN_DIR.mkdir(mode=0o700, parents=False)
            created_dir = True
        metadata = DROPIN_DIR.lstat()
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or metadata.st_mode & 0o022
        ):
            raise RuntimeError("unsafe_dropin_directory")
        # From the first filesystem mutation, the enclosing finally owns cleanup.
        fd = os.open(
            DROPIN, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
        )
        created_dropin = True
        opened = os.fstat(fd)
        dropin_identity = (opened.st_dev, opened.st_ino)
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(override)
            output.flush()
            os.fsync(output.fileno())
        validate_m5_service_activation_lock_v1(held)
        if (
            source_digest() != selected_source
            or tree_digest(ROOT / "frontend/dist") != build
        ):
            raise RuntimeError("candidate_changed")
        if unit_snapshot() != old_snapshot or not safe_cgroup(
            old_snapshot[2], cgroup_pids(old_snapshot[1])
        ):
            raise RuntimeError("service_changed_or_busy")
        job_unknown = True
        reload_result = ctl("daemon-reload")
        job_unknown = False
        if reload_result.returncode:
            raise RuntimeError("daemon_reload_failed")
        # A child can spawn after this check. Only the named dashboard unit is restarted.
        if not safe_cgroup(old_snapshot[2], cgroup_pids(old_snapshot[1])):
            raise RuntimeError("service_became_busy")
        restarted = True
        # Until the command returns, interruption may leave a manager-side job
        # running even if the local systemctl client has exited.
        job_unknown = True
        try:
            restart_result = ctl("restart", UNIT)
        except subprocess.TimeoutExpired:
            raise RuntimeError("restart_job_status_unknown") from None
        job_unknown = False
        if restart_result.returncode:
            raise RuntimeError("dashboard_restart_failed")
        candidate_identity = service_identity()
        if not wait_ready((expected, expected), candidate=True):
            raise RuntimeError("candidate_readiness_failed")
        if not candidate_runtime():
            raise RuntimeError("candidate_runtime_mismatch")
        if (
            clean_revision() != revision
            or source_digest() != selected_source
            or tree_digest(ROOT / "frontend/dist") != build
        ):
            raise RuntimeError("candidate_changed")
        activated = True
        return 0
    except (Exception, KeyboardInterrupt) as error:  # noqa: BLE001 - always run rollback
        reason = (
            str(error) if isinstance(error, RuntimeError) else "transition_interrupted"
        )
        print(f"M6 LOCAL ACTIVATION: FAILED — {reason}")
        return 1
    finally:
        for path, target in reversed(links):
            try:
                if path.is_symlink() and path.resolve(strict=True) == target.resolve(
                    strict=True
                ):
                    path.unlink()
            except OSError:
                print("M6 LOCAL ACTIVATION: temporary tool link needs attention")
                cleanup_failed = True
        if created_dropin and not activated and job_unknown:
            # The systemd manager may still be executing the timed-out job.
            # Do not remove its configuration or issue another job concurrently.
            print(
                "M6 LOCAL ACTIVATION: rollback needs operator attention — restart job status unknown"
            )
            cleanup_failed = True
        elif created_dropin and not activated:
            try:
                # Only remove the inode we created; never overwrite another tool's state.
                metadata = DROPIN.lstat()
                if not stat.S_ISREG(metadata.st_mode) or not same_identity(
                    dropin_identity, (metadata.st_dev, metadata.st_ino)
                ):
                    print("M6 LOCAL ACTIVATION: rollback blocked — drop-in changed")
                    cleanup_failed = True
                else:
                    DROPIN.unlink()
                    if created_dir:
                        try:
                            DROPIN_DIR.rmdir()
                        except OSError:
                            pass
                    if (
                        old_snapshot is None
                        or hashlib.sha256(UNIT_FILE.read_bytes()).hexdigest()
                        != old_snapshot[0]
                    ):
                        print(
                            "M6 LOCAL ACTIVATION: rollback needs attention — original unit changed"
                        )
                        cleanup_failed = True
                    elif ctl("daemon-reload").returncode:
                        print(
                            "M6 LOCAL ACTIVATION: rollback needs attention — reload failed"
                        )
                        cleanup_failed = True
                    elif restarted:
                        current_identity = service_identity()
                        can_restart = rollback_permitted(
                            candidate_identity,
                            current_identity,
                            cgroup_pids(current_identity[2])
                            if current_identity[2]
                            else frozenset(),
                            job_unknown,
                        )
                        can_start = (
                            candidate_identity is None
                            and old_snapshot is not None
                            and inactive_start_permitted(
                                prop("ActiveState"),
                                current_identity[0],
                                cgroup_pids(old_snapshot[1], allow_missing=True),
                                job_unknown,
                            )
                        )
                        if not can_restart and not can_start:
                            print(
                                "M6 LOCAL ACTIVATION: rollback needs operator attention — candidate changed or has unclassified children"
                            )
                            cleanup_failed = True
                        elif (
                            ctl("restart" if can_restart else "start", UNIT).returncode
                            or baseline is None
                            or not wait_ready(baseline, candidate=False)
                        ):
                            print(
                                "M6 LOCAL ACTIVATION: rollback needs attention — readiness failed"
                            )
                            cleanup_failed = True
                        elif old_snapshot is None or prop("WorkingDirectory") != str(
                            OLD_ROOT
                        ):
                            print(
                                "M6 LOCAL ACTIVATION: rollback needs attention — runtime mismatch"
                            )
                            cleanup_failed = True
                        else:
                            print(
                                "M6 LOCAL ACTIVATION: previous loopback/LAN build restored"
                            )
                    else:
                        print("M6 LOCAL ACTIVATION: drop-in removed before restart")
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
                print("M6 LOCAL ACTIVATION: rollback needs operator attention")
                cleanup_failed = True
        elif created_dir and not created_dropin:
            try:
                DROPIN_DIR.rmdir()
            except OSError:
                pass
        if held is not None:
            try:
                release_m5_service_activation_lock_v1(held)
            except Exception:  # noqa: BLE001 - report lock cleanup failure
                print("M6 LOCAL ACTIVATION: transition lock release needs attention")
                cleanup_failed = True
        signal.signal(signal.SIGTERM, old_signal)
        if cleanup_failed:
            raise SystemExit(1)
        if activated:
            print(
                "M6 LOCAL ACTIVATION: PASSED — loopback and LAN unauthenticated checks"
            )
            print("Authenticated live-browser check and full M6 completion: NOT RUN.")
            print(
                "Agent cgroup snapshot cannot eliminate a concurrent child-spawn race."
            )


if __name__ == "__main__":
    raise SystemExit(main())

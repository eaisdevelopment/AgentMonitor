"""Safe current-revision V1-M3 exit over read-only installed-service views."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import select
import signal
import stat
import subprocess
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[3]
BACKEND_PYTHON = ROOT / "backend/.venv/bin/python"
RECEIPT_RECORD_TYPE = "agentmonitor.m3_current_gate_receipt"
CANONICAL_COMMAND = "python3 tools/automation/run.py AUTO-M3-EXIT"
RECEIPT_DIRECTORY_NAME = ".agentmonitor-local"
RECEIPT_BASENAME = "m3-current-gate-receipt.json"
RECEIPT_PATH = ROOT / RECEIPT_DIRECTORY_NAME / RECEIPT_BASENAME
REQUIRED_LANES = (
    "selected_account_preflight",
    "fresh_quota_lineage",
    "registry_unchanged",
    "revision_bound_service",
    "current_browser",
    "runtime_regression",
    "technical_suite",
    "quality",
    "build",
    "mutation",
    "documentation",
    "git_preflight",
)
PRE_BROWSER_ROUTINES = (("build", "AUTO-BUILD"),)
LOCAL_ROUTINES = (
    ("technical_suite", "AUTO-M3-TEST"),
    ("quality", "AUTO-QUALITY"),
    ("mutation", "AUTO-MUTATION"),
    ("documentation", "AUTO-DOCS-CHECK"),
    ("git_preflight", "AUTO-GIT-PREFLIGHT"),
)
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_REVISION = re.compile(r"[0-9a-f]{40}\Z")
_SAFE_EVIDENCE = re.compile(r"[A-Za-z0-9_.:+-]{1,160}\Z")


class M3CurrentExitErrorV1(ValueError):
    """One sanitized fail-closed current-gate reason."""


class M3CurrentServiceCleanupErrorV1(M3CurrentExitErrorV1):
    """A failed replacement service could not be proven stopped."""


@dataclass(frozen=True, slots=True)
class ServiceLaunchV1:
    """Closed current-dashboard launch plan without secret values."""

    command: tuple[str, ...]
    config: Path
    data_root: Path
    host: str
    port: int


@dataclass(frozen=True, slots=True)
class ServiceProcessV1:
    """Linux process identity for the service launched by this gate."""

    pid: int
    start_time_ticks: int
    pidfd: int


def _utc_text(value: datetime) -> str:
    if value.utcoffset() is None or value.utcoffset().total_seconds() != 0:
        raise M3CurrentExitErrorV1("m3_current_receipt_time_invalid")
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def build_passed_receipt_v1(
    *,
    implementation_revision: str,
    started_at: datetime,
    completed_at: datetime,
    selected_account_digest: str,
    lane_evidence: Mapping[str, str],
) -> dict[str, object]:
    """Build the closed, privacy-minimized receipt for one passing run."""

    if (
        _REVISION.fullmatch(implementation_revision) is None
        or _SHA256.fullmatch(selected_account_digest) is None
        or completed_at < started_at
    ):
        raise M3CurrentExitErrorV1("m3_current_receipt_identity_invalid")
    if set(lane_evidence) != set(REQUIRED_LANES) or any(
        not isinstance(value, str) or _SAFE_EVIDENCE.fullmatch(value) is None
        for value in lane_evidence.values()
    ):
        raise M3CurrentExitErrorV1("m3_current_lane_set_invalid")
    completed_text = _utc_text(completed_at)
    return {
        "schema_version": "1.0.0",
        "record_type": RECEIPT_RECORD_TYPE,
        "receipt_id": "M3-CURRENT-GATE-"
        + completed_text.replace(":", "").replace("-", ""),
        "milestone_id": "V1-M3",
        "command_id": "AUTO-M3-EXIT",
        "command": CANONICAL_COMMAND,
        "implementation_revision": implementation_revision,
        "started_at": _utc_text(started_at),
        "completed_at": completed_text,
        "status": "passed",
        "exit_code": 0,
        "skips": [],
        "selected_account_digest": selected_account_digest,
        "required_lanes": [
            {
                "lane_id": lane,
                "status": "passed",
                "evidence": lane_evidence[lane],
            }
            for lane in REQUIRED_LANES
        ],
    }


def _validate_receipt_target_v1(path: Path) -> None:
    try:
        directory = path.parent.lstat()
    except OSError as error:
        raise M3CurrentExitErrorV1("m3_current_receipt_path_invalid") from error
    if (
        not path.is_absolute()
        or path.name != RECEIPT_BASENAME
        or path.parent.name != RECEIPT_DIRECTORY_NAME
        or not stat.S_ISDIR(directory.st_mode)
        or directory.st_uid != os.getuid()
        or stat.S_IMODE(directory.st_mode) != 0o700
        or path.exists()
        or path.is_symlink()
    ):
        raise M3CurrentExitErrorV1("m3_current_receipt_path_invalid")


def write_private_receipt_v1(path: Path, receipt: Mapping[str, object]) -> None:
    """Create one owner-only receipt without replacing any existing file."""

    _validate_receipt_target_v1(path)
    payload = json.dumps(receipt, indent=2, sort_keys=False) + "\n"
    descriptor = -1
    created = False
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        created = True
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        descriptor = -1
        directory_descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except BaseException:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if created:
            path.unlink(missing_ok=True)
        raise


def parse_service_command_v1(command: tuple[str, ...], origin: str) -> ServiceLaunchV1:
    """Parse only the reviewed AgentMonitor bootstrap command shape."""

    if (
        len(command) < 10
        or command[0] not in {str(BACKEND_PYTHON), "backend/.venv/bin/python"}
        or command[1:3] != ("-m", "agentmonitor.composition.bootstrap")
        or any(not isinstance(item, str) or not item for item in command)
    ):
        raise M3CurrentExitErrorV1("m3_current_service_command_invalid")
    values: dict[str, str] = {}
    authenticated = False
    allowed_values = {
        "--config",
        "--data-root",
        "--host",
        "--port",
        "--lan-host",
        "--lan-network",
    }
    index = 3
    while index < len(command):
        option = command[index]
        if option == "--authenticated-dashboard" and not authenticated:
            authenticated = True
            index += 1
            continue
        if (
            option not in allowed_values
            or option in values
            or index + 1 >= len(command)
        ):
            raise M3CurrentExitErrorV1("m3_current_service_command_invalid")
        values[option] = command[index + 1]
        index += 2
    if (
        set(values)
        not in (
            {"--config", "--data-root", "--host", "--port"},
            {
                "--config",
                "--data-root",
                "--host",
                "--port",
                "--lan-host",
                "--lan-network",
            },
        )
        or not authenticated
    ):
        raise M3CurrentExitErrorV1("m3_current_service_command_invalid")
    try:
        port = int(values["--port"])
        parsed_origin = urlsplit(origin)
        origin_port = parsed_origin.port
        config = Path(values["--config"])
        data_root = Path(values["--data-root"])
    except (TypeError, ValueError):
        raise M3CurrentExitErrorV1("m3_current_service_command_invalid") from None
    host = values["--host"]
    if (
        host != "127.0.0.1"
        or not 1 <= port <= 65535
        or parsed_origin.scheme != "http"
        or parsed_origin.hostname != host
        or origin_port != port
        or parsed_origin.path not in {"", "/"}
        or parsed_origin.query
        or parsed_origin.fragment
        or not config.is_absolute()
        or not data_root.is_absolute()
        or config != data_root / "service.env"
    ):
        raise M3CurrentExitErrorV1("m3_current_service_command_invalid")
    if "--lan-host" in values:
        try:
            lan_host = ipaddress.ip_address(values["--lan-host"])
            lan_network = ipaddress.ip_network(values["--lan-network"], strict=True)
        except ValueError:
            raise M3CurrentExitErrorV1("m3_current_service_command_invalid") from None
        if (
            lan_host.version != 4
            or lan_network.version != 4
            or not lan_host.is_private
            or not lan_network.is_private
            or lan_host not in lan_network
        ):
            raise M3CurrentExitErrorV1("m3_current_service_command_invalid")
    canonical = [
        str(BACKEND_PYTHON),
        "-m",
        "agentmonitor.composition.bootstrap",
        "--config",
        str(config),
        "--data-root",
        str(data_root),
        "--host",
        host,
        "--port",
        str(port),
        "--authenticated-dashboard",
    ]
    if "--lan-host" in values:
        canonical.extend(
            (
                "--lan-host",
                values["--lan-host"],
                "--lan-network",
                values["--lan-network"],
            )
        )
    return ServiceLaunchV1(tuple(canonical), config, data_root, host, port)


def _process_start_ticks(pid: int) -> int:
    try:
        process = Path(f"/proc/{pid}")
        if process.stat().st_uid != os.getuid():
            raise OSError
        fields = (
            (process / "stat").read_text(encoding="ascii").rsplit(") ", 1)[1].split()
        )
        return int(fields[19])
    except (IndexError, OSError, UnicodeError, ValueError):
        raise M3CurrentExitErrorV1("m3_current_service_process_invalid") from None


def _read_service_launch(pid: int, origin: str) -> ServiceLaunchV1:
    try:
        process = Path(f"/proc/{pid}")
        if process.joinpath("cwd").resolve(strict=True) != ROOT:
            raise OSError
        raw = process.joinpath("cmdline").read_bytes()
        if not raw or len(raw) > 8192:
            raise OSError
        command = tuple(item.decode("utf-8") for item in raw.rstrip(b"\0").split(b"\0"))
        launch = parse_service_command_v1(command, origin)
        root_info = launch.data_root.lstat()
        config_info = launch.config.lstat()
        database_info = (launch.data_root / "agentmonitor.db").lstat()
        if (
            not BACKEND_PYTHON.is_file()
            or not os.access(BACKEND_PYTHON, os.X_OK)
            or not stat.S_ISDIR(root_info.st_mode)
            or root_info.st_uid != os.getuid()
            or stat.S_IMODE(root_info.st_mode) != 0o700
            or launch.data_root.resolve(strict=True) != launch.data_root
            or not stat.S_ISREG(config_info.st_mode)
            or config_info.st_uid != os.getuid()
            or config_info.st_nlink != 1
            or stat.S_IMODE(config_info.st_mode) != 0o600
            or launch.config.resolve(strict=True) != launch.config
            or not stat.S_ISREG(database_info.st_mode)
            or database_info.st_uid != os.getuid()
            or database_info.st_nlink != 1
            or stat.S_IMODE(database_info.st_mode) != 0o600
        ):
            raise OSError
        return launch
    except M3CurrentExitErrorV1:
        raise
    except (OSError, UnicodeError):
        raise M3CurrentExitErrorV1("m3_current_service_process_invalid") from None


def _pidfd(pid: int) -> int:
    try:
        return os.pidfd_open(pid, 0)
    except (AttributeError, OSError):
        raise M3CurrentExitErrorV1("m3_current_service_process_invalid") from None


def _pidfd_exited(pidfd: int, timeout: float = 0) -> bool:
    try:
        readable, _, _ = select.select([pidfd], [], [], timeout)
    except (OSError, ValueError):
        raise M3CurrentExitErrorV1("m3_current_service_process_invalid") from None
    return bool(readable)


def _signal_pidfd(pidfd: int, signum: signal.Signals) -> None:
    try:
        signal.pidfd_send_signal(pidfd, signum)
    except (AttributeError, OSError):
        raise M3CurrentExitErrorV1("m3_current_service_stop_failed") from None


def _stop_spawned_service(
    process: subprocess.Popen[bytes],
    pidfd: int,
    *,
    graceful_timeout: float = 30,
    kill_timeout: float = 10,
) -> bool:
    if _pidfd_exited(pidfd):
        process.poll()
        return True
    try:
        signal.pidfd_send_signal(pidfd, signal.SIGTERM)
    except (AttributeError, OSError):
        return False
    if not _pidfd_exited(pidfd, graceful_timeout):
        try:
            signal.pidfd_send_signal(pidfd, signal.SIGKILL)
        except (AttributeError, OSError):
            return False
        if not _pidfd_exited(pidfd, kill_timeout):
            return False
    process.poll()
    return process.returncode is not None


def _stop_unbound_child(process: subprocess.Popen[bytes]) -> bool:
    """Stop a just-spawned unreaped child when pidfd acquisition failed."""

    if process.poll() is not None:
        return True
    try:
        process.terminate()
        process.wait(timeout=30)
        return True
    except subprocess.TimeoutExpired:
        try:
            process.kill()
            process.wait(timeout=10)
            return True
        except (OSError, subprocess.TimeoutExpired):
            return False
    except OSError:
        return False


def _cleanup_failed_service_launch(
    process: subprocess.Popen[bytes], pidfd: int
) -> bool:
    try:
        if pidfd >= 0:
            return _stop_spawned_service(process, pidfd)
        return _stop_unbound_child(process)
    except M3CurrentExitErrorV1:
        return False
    finally:
        if pidfd >= 0:
            try:
                os.close(pidfd)
            except OSError:
                pass


def is_exact_service_ready_event_v1(event: object, origin: str) -> bool:
    """Accept only the bootstrap child's closed exact-origin ready event."""

    return (
        isinstance(event, dict)
        and set(event) == {"event", "origin"}
        and event.get("event") == "ready"
        and event.get("origin") == origin
    )


def start_service_output_drainer_v1(stream: BinaryIO) -> subprocess.Popen[bytes]:
    """Continuously discard service output without retaining it on disk."""

    drainer = subprocess.Popen(
        [
            str(BACKEND_PYTHON),
            "-c",
            "import os\nwhile data := os.read(0, 65536):\n    pass\n",
        ],
        cwd=ROOT,
        env={"PATH": os.environ.get("PATH", os.defpath)},
        stdin=stream,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    if drainer.poll() is not None:
        raise M3CurrentExitErrorV1("m3_current_service_start_failed")
    return drainer


def _launch_service(launch: ServiceLaunchV1, origin: str) -> ServiceProcessV1:
    process: subprocess.Popen[bytes] | None = None
    pidfd = -1
    try:
        environment = {
            "PATH": os.environ.get("PATH", os.defpath),
            "PYTHONPATH": str(ROOT / "backend/src"),
        }
        process = subprocess.Popen(
            launch.command,
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        if process.stdout is None:
            raise M3CurrentExitErrorV1("m3_current_service_start_failed")
        pidfd = _pidfd(process.pid)
        start_ticks = _process_start_ticks(process.pid)
        deadline = time.monotonic() + 30
        buffer = b""
        captured = 0
        while time.monotonic() < deadline:
            if _pidfd_exited(pidfd) or process.poll() is not None:
                raise M3CurrentExitErrorV1("m3_current_service_start_failed")
            readable, _, _ = select.select(
                [process.stdout.fileno()],
                [],
                [],
                min(0.1, max(0, deadline - time.monotonic())),
            )
            if not readable:
                continue
            chunk = os.read(process.stdout.fileno(), 4096)
            if not chunk:
                raise M3CurrentExitErrorV1("m3_current_service_start_failed")
            captured += len(chunk)
            if captured > 16_384:
                raise M3CurrentExitErrorV1("m3_current_service_start_failed")
            buffer += chunk
            while b"\n" in buffer:
                raw_line, buffer = buffer.split(b"\n", 1)
                if len(raw_line) > 4096:
                    raise M3CurrentExitErrorV1("m3_current_service_start_failed")
                try:
                    line = raw_line.decode("utf-8")
                except UnicodeDecodeError:
                    continue
                if line:
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if is_exact_service_ready_event_v1(event, origin):
                        start_service_output_drainer_v1(process.stdout)
                        process.stdout.close()
                        return ServiceProcessV1(process.pid, start_ticks, pidfd)
            if len(buffer) > 4096:
                raise M3CurrentExitErrorV1("m3_current_service_start_failed")
        raise M3CurrentExitErrorV1("m3_current_service_start_failed")
    except M3CurrentExitErrorV1:
        if process is not None and not _cleanup_failed_service_launch(process, pidfd):
            raise M3CurrentServiceCleanupErrorV1(
                "m3_current_service_restore_failed"
            ) from None
        if process is None and pidfd >= 0:
            os.close(pidfd)
        raise
    except (OSError, UnicodeError):
        if process is not None and not _cleanup_failed_service_launch(process, pidfd):
            raise M3CurrentServiceCleanupErrorV1(
                "m3_current_service_restore_failed"
            ) from None
        if process is None and pidfd >= 0:
            os.close(pidfd)
        raise M3CurrentExitErrorV1("m3_current_service_start_failed") from None
    finally:
        if (
            process is not None
            and process.stdout is not None
            and not process.stdout.closed
        ):
            process.stdout.close()


def _restart_service(pid: int, origin: str) -> ServiceProcessV1:
    old_pidfd = _pidfd(pid)
    try:
        old_ticks = _process_start_ticks(pid)
        launch = _read_service_launch(pid, origin)
        if _process_start_ticks(pid) != old_ticks or _pidfd_exited(old_pidfd):
            raise M3CurrentExitErrorV1("m3_current_service_process_invalid")
        _signal_pidfd(old_pidfd, signal.SIGTERM)
        if not _pidfd_exited(old_pidfd, 30):
            raise M3CurrentExitErrorV1("m3_current_service_stop_failed")
    finally:
        os.close(old_pidfd)
    try:
        return _launch_service(launch, origin)
    except M3CurrentServiceCleanupErrorV1:
        raise
    except M3CurrentExitErrorV1 as start_error:
        try:
            restored = _launch_service(launch, origin)
        except M3CurrentExitErrorV1:
            raise M3CurrentExitErrorV1("m3_current_service_restore_failed") from None
        os.close(restored.pidfd)
        raise M3CurrentExitErrorV1("m3_current_service_start_failed") from start_error


def _verify_service_process(process: ServiceProcessV1) -> None:
    if _pidfd_exited(process.pidfd) or (
        _process_start_ticks(process.pid) != process.start_time_ticks
    ):
        raise M3CurrentExitErrorV1("m3_current_service_changed")
    try:
        if Path(f"/proc/{process.pid}/cwd").resolve(strict=True) != ROOT:
            raise OSError
    except OSError:
        raise M3CurrentExitErrorV1("m3_current_service_changed") from None


def _checkout_output(*arguments: str) -> str:
    result = subprocess.run(
        arguments,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        raise M3CurrentExitErrorV1("m3_current_git_read_failed")
    return result.stdout.strip()


def _clean_revision() -> str:
    revision = _checkout_output("git", "rev-parse", "HEAD")
    if _REVISION.fullmatch(revision) is None:
        raise M3CurrentExitErrorV1("m3_current_git_revision_invalid")
    if _checkout_output("git", "status", "--porcelain"):
        raise M3CurrentExitErrorV1("m3_current_checkout_not_clean")
    return revision


def _run_browser(
    environment: dict[str, str], *, preflight: bool = False
) -> dict[str, object]:
    child_environment = environment.copy()
    if preflight:
        child_environment["AGENTMONITOR_M3_PREFLIGHT_ONLY"] = "1"
    else:
        child_environment.pop("AGENTMONITOR_M3_PREFLIGHT_ONLY", None)
    result = subprocess.run(
        ["node", "tools/ui/verify_m3_current.mjs"],
        cwd=ROOT,
        env=child_environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=120 if preflight else 900,
    )
    if result.stdout:
        print(result.stdout.rstrip(), flush=True)
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr, flush=True)
    if result.returncode == 3:
        raise M3CurrentExitErrorV1("m3_current_browser_blocked")
    if result.returncode != 0:
        raise M3CurrentExitErrorV1("m3_current_browser_failed")
    expected_event = (
        "m3_current_browser_preflight" if preflight else "m3_current_browser_witness"
    )
    witnesses: list[dict[str, object]] = []
    for line in result.stdout.splitlines():
        try:
            candidate = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict) and candidate.get("event") == expected_event:
            witnesses.append(candidate)
    if len(witnesses) != 1:
        raise M3CurrentExitErrorV1("m3_current_browser_receipt_missing")
    return witnesses[0]


def _run_routine(routine: str) -> None:
    result = subprocess.run(
        [sys.executable, "tools/automation/run.py", routine],
        cwd=ROOT,
        check=False,
        timeout=3600,
    )
    if result.returncode == 3:
        raise M3CurrentExitErrorV1(f"m3_current_{routine.lower()}_blocked")
    if result.returncode != 0:
        raise M3CurrentExitErrorV1(f"m3_current_{routine.lower()}_failed")


def validate_browser_transition_v1(
    preflight: Mapping[str, object],
    witness: Mapping[str, object],
    account_digest: str,
) -> tuple[str, str]:
    """Bind the post-restart browser result to the exact preflight registry tuple."""

    metadata_digest = preflight.get("selected_account_metadata_digest")
    if (
        preflight.get("selected_account_digest") != account_digest
        or not isinstance(metadata_digest, str)
        or _SHA256.fullmatch(metadata_digest) is None
        or preflight.get("identity_match") is not True
        or preflight.get("registry_unchanged") is not True
        or preflight.get("mutations") != 0
    ):
        raise M3CurrentExitErrorV1("m3_current_browser_preflight_invalid")
    if witness.get("selected_account_digest") != account_digest:
        raise M3CurrentExitErrorV1("m3_current_browser_account_mismatch")
    if witness.get("selected_account_metadata_digest") != metadata_digest:
        raise M3CurrentExitErrorV1("m3_current_browser_metadata_changed")
    run_digest = witness.get("collection_run_digest")
    runtime_state = witness.get("runtime_state")
    if (
        witness.get("identity_match") is not True
        or witness.get("registry_unchanged") is not True
        or witness.get("mutations") != 0
        or not isinstance(run_digest, str)
        or _SHA256.fullmatch(run_digest) is None
        or runtime_state not in {"available", "partial"}
    ):
        raise M3CurrentExitErrorV1("m3_current_browser_lineage_invalid")
    return run_digest, runtime_state


def write_verified_receipt_v1(
    process: ServiceProcessV1,
    path: Path,
    receipt: Mapping[str, object],
) -> None:
    """Write a receipt only while the exact restarted service remains alive."""

    _verify_service_process(process)
    write_private_receipt_v1(path, receipt)
    try:
        _verify_service_process(process)
    except M3CurrentExitErrorV1:
        path.unlink(missing_ok=True)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        raise


def main() -> int:
    service: ServiceProcessV1 | None = None
    try:
        account_id = os.environ.get("AGENTMONITOR_M3_ACCOUNT_ID", "")
        service_pid_value = os.environ.get("AGENTMONITOR_M3_SERVICE_PID", "")
        browser_origin = os.environ.get("AGENTMONITOR_TEST_DASHBOARD_ORIGIN", "")
        if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", account_id) is None:
            raise M3CurrentExitErrorV1("m3_current_account_selector_required")
        if re.fullmatch(r"[1-9][0-9]{0,9}", service_pid_value) is None:
            raise M3CurrentExitErrorV1("m3_current_service_pid_required")
        _validate_receipt_target_v1(RECEIPT_PATH)
        revision = _clean_revision()
        started_at = datetime.now(UTC)
        account_digest = hashlib.sha256(account_id.encode("utf-8")).hexdigest()
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT / "backend/src")
        preflight = _run_browser(environment, preflight=True)
        if (
            preflight.get("selected_account_digest") != account_digest
            or not isinstance(preflight.get("selected_account_metadata_digest"), str)
            or _SHA256.fullmatch(preflight["selected_account_metadata_digest"]) is None
            or preflight.get("identity_match") is not True
            or preflight.get("registry_unchanged") is not True
            or preflight.get("mutations") != 0
        ):
            raise M3CurrentExitErrorV1("m3_current_browser_preflight_invalid")
        lane_evidence: dict[str, str] = {}
        for lane, routine in PRE_BROWSER_ROUTINES:
            _run_routine(routine)
            lane_evidence[lane] = f"{routine.lower()}_passed"
        service = _restart_service(int(service_pid_value), browser_origin)
        lane_evidence["revision_bound_service"] = "service_restarted_from_clean_head"
        witness = _run_browser(environment)
        run_digest, runtime_state = validate_browser_transition_v1(
            preflight, witness, account_digest
        )
        lane_evidence.update(
            selected_account_preflight="browser_api_account_verified",
            fresh_quota_lineage=f"run_sha256:{run_digest}",
            registry_unchanged="browser_get_only_registry_unchanged",
            current_browser="visible_shared_chrome_passed",
            runtime_regression=f"runtime_query:{runtime_state}",
        )
        for lane, routine in LOCAL_ROUTINES:
            _run_routine(routine)
            lane_evidence[lane] = f"{routine.lower()}_passed"
        if revision != _clean_revision():
            raise M3CurrentExitErrorV1("m3_current_checkout_revision_changed")
        completed_at = datetime.now(UTC)
        receipt = build_passed_receipt_v1(
            implementation_revision=revision,
            started_at=started_at,
            completed_at=completed_at,
            selected_account_digest=account_digest,
            lane_evidence=lane_evidence,
        )
        write_verified_receipt_v1(service, RECEIPT_PATH, receipt)
    except M3CurrentExitErrorV1 as error:
        print(f"M3 CURRENT EXIT: BLOCKED — {error}")
        return 3
    except (OSError, subprocess.TimeoutExpired, ValueError):
        print("M3 CURRENT EXIT: FAILED — execution_unavailable")
        return 1
    finally:
        if service is not None:
            try:
                os.close(service.pidfd)
            except OSError:
                pass
    print(
        "M3 CURRENT EXIT: PASSED — current read-only quota/browser/runtime "
        "regression and canonical local lanes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

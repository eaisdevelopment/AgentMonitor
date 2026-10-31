"""Safe current-revision acceptance of the complete V1-M4 Claude fleet."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from tools.automation.implementations.auto_m3_current_exit import (
    M3CurrentExitErrorV1,
    ServiceLaunchV1,
    ServiceProcessV1,
    _clean_revision,
    _process_start_ticks,
    _read_service_launch,
    _restart_service,
    _verify_service_process,
)
from tools.automation.implementations.auto_m4_exit import (
    STORY_ARTIFACTS,
    TEST_PATHS,
)

ROOT = Path(__file__).resolve().parents[3]
RECEIPT_RECORD_TYPE = "agentmonitor.m4_current_gate_receipt"
CANONICAL_COMMAND = "python3 tools/automation/run.py AUTO-M4-EXIT"
RECEIPT_DIRECTORY_NAME = ".agentmonitor-local"
RECEIPT_BASENAME = "m4-current-gate-receipt.json"
RECEIPT_PATH = ROOT / RECEIPT_DIRECTORY_NAME / RECEIPT_BASENAME
REQUIRED_LANES = (
    "fleet_preflight",
    "build",
    "revision_bound_service",
    "technical_suite",
    "fleet_browser",
    "alerts_browser",
    "operations_browser",
    "registry_unchanged",
    "fresh_fleet_lineage",
    "planning",
    "quality",
    "mutation",
    "documentation",
    "git_preflight",
)
PRE_SERVICE_ROUTINES = (("build", "AUTO-BUILD"),)
LOCAL_ROUTINES = (
    ("planning", "AUTO-PLAN-CHECK"),
    ("quality", "AUTO-QUALITY"),
    ("mutation", "AUTO-MUTATION"),
    ("documentation", "AUTO-DOCS-CHECK"),
    ("git_preflight", "AUTO-GIT-PREFLIGHT"),
)
LIVE_SELECTORS = (
    "AGENTMONITOR_TEST_OWNER_DATA_ROOT",
    "AGENTMONITOR_TEST_DATA_ROOT",
    "AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT",
    "AGENTMONITOR_TEST_DASHBOARD_ORIGIN",
    "AGENTMONITOR_TEST_M4_OWNER_OUTCOMES",
    "AGENTMONITOR_M4_SERVICE_PID",
)
BROWSER_CHECKS = (
    ("fleet_browser", "tools/ui/verify_dashboard_overview.mjs"),
    ("alerts_browser", "tools/ui/verify_m4_alerts.mjs"),
    ("operations_browser", "tools/ui/verify_m4_operations.mjs"),
)
DEPENDENCY_ROUTINES = ("AUTO-M3-TEST",)
CURRENT_VERSION_TEST_PATHS = (
    "backend/tests/adapters/providers/claude/live/test_authentication.py",
    "backend/tests/adapters/providers/claude/test_authentication_health.py",
    "backend/tests/adapters/providers/claude/test_capacity_mapper.py",
    "backend/tests/adapters/providers/claude/test_manifest.py",
    "backend/tests/adapters/providers/claude/test_subscription_source_parser.py",
    "backend/tests/live/claude/test_installation.py",
    "backend/tests/live/claude/test_otel_version_gate.py",
    "backend/tests/live/claude/test_subscription_quota.py",
    "backend/tests/registry/test_installation_reconciliation_policy.py",
    "backend/tests/integration/registry/test_claude_installation_reconciliation.py",
)
STORY_PYTEST_FLAGS = (
    "-q",
    "--tb=short",
    "-p",
    "tools.automation.pytest_no_skip",
    "--import-mode=importlib",
)
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_REVISION = re.compile(r"[0-9a-f]{40}\Z")
_SAFE_EVIDENCE = re.compile(r"[A-Za-z0-9_.:+-]{1,160}\Z")


class M4CurrentExitErrorV1(ValueError):
    """One sanitized fail-closed current-gate reason."""


class M4CurrentExitFailedV1(M4CurrentExitErrorV1):
    """A required implemented boundary failed."""


@dataclass(frozen=True, slots=True)
class SelectedServiceV1:
    """The exact already-running AgentMonitor process authorized for restart."""

    pid: int
    start_time_ticks: int
    launch: ServiceLaunchV1


def _utc_text(value: datetime) -> str:
    if value.utcoffset() is None or value.utcoffset().total_seconds() != 0:
        raise M4CurrentExitErrorV1("m4_current_receipt_time_invalid")
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def build_passed_receipt_v1(
    *,
    implementation_revision: str,
    started_at: datetime,
    completed_at: datetime,
    owner_outcomes_digest: str,
    fleet_metadata_digest: str,
    identity_set_digest: str,
    test_count: int,
    lane_evidence: Mapping[str, str],
) -> dict[str, object]:
    """Build one privacy-minimized receipt only for the exact complete lane set."""

    if (
        _REVISION.fullmatch(implementation_revision) is None
        or any(
            _SHA256.fullmatch(value) is None
            for value in (
                owner_outcomes_digest,
                fleet_metadata_digest,
                identity_set_digest,
            )
        )
        or type(test_count) is not int
        or test_count < 1
        or completed_at < started_at
    ):
        raise M4CurrentExitErrorV1("m4_current_receipt_identity_invalid")
    if set(lane_evidence) != set(REQUIRED_LANES) or any(
        not isinstance(value, str) or _SAFE_EVIDENCE.fullmatch(value) is None
        for value in lane_evidence.values()
    ):
        raise M4CurrentExitErrorV1("m4_current_lane_set_invalid")
    completed_text = _utc_text(completed_at)
    return {
        "schema_version": "1.0.0",
        "record_type": RECEIPT_RECORD_TYPE,
        "receipt_id": "M4-CURRENT-GATE-"
        + completed_text.replace(":", "").replace("-", ""),
        "milestone_id": "V1-M4",
        "command_id": "AUTO-M4-EXIT",
        "command": CANONICAL_COMMAND,
        "implementation_revision": implementation_revision,
        "started_at": _utc_text(started_at),
        "completed_at": completed_text,
        "status": "passed",
        "exit_code": 0,
        "skips": [],
        "test_count": test_count,
        "account_count": 6,
        "organization_count": 2,
        "distinct_identity_count": 6,
        "owner_outcomes_digest": owner_outcomes_digest,
        "fleet_metadata_digest": fleet_metadata_digest,
        "identity_set_digest": identity_set_digest,
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
        raise M4CurrentExitErrorV1("m4_current_receipt_path_invalid") from error
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
        raise M4CurrentExitErrorV1("m4_current_receipt_path_invalid")


def write_private_receipt_v1(path: Path, receipt: Mapping[str, object]) -> None:
    """Create one owner-only receipt without following or replacing a file."""

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
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except BaseException:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if created:
            path.unlink(missing_ok=True)
        raise


def write_verified_receipt_v1(
    process: ServiceProcessV1,
    path: Path,
    receipt: Mapping[str, object],
) -> None:
    """Create a receipt only while the exact restarted service stays alive."""

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


def _private_file_digest(path: Path) -> str:
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) & 0o077
            or metadata.st_nlink != 1
            or metadata.st_size < 2
            or metadata.st_size > 8192
        ):
            raise OSError
        chunks: list[bytes] = []
        remaining = metadata.st_size
        while remaining:
            chunk = os.read(descriptor, remaining)
            if not chunk:
                raise OSError
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        if len(payload) != metadata.st_size:
            raise OSError
        return hashlib.sha256(payload).hexdigest()
    except OSError:
        raise M4CurrentExitErrorV1("m4_current_owner_outcomes_invalid") from None
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _validate_live_selection(
    environment: Mapping[str, str],
) -> tuple[SelectedServiceV1, str]:
    if not all(environment.get(key) for key in LIVE_SELECTORS):
        raise M4CurrentExitErrorV1("m4_current_live_selectors_required")
    service_pid = environment["AGENTMONITOR_M4_SERVICE_PID"]
    if re.fullmatch(r"[1-9][0-9]{0,9}", service_pid) is None:
        raise M4CurrentExitErrorV1("m4_current_service_pid_required")
    try:
        owner_root = Path(environment["AGENTMONITOR_TEST_OWNER_DATA_ROOT"])
        test_root = Path(environment["AGENTMONITOR_TEST_DATA_ROOT"])
        root_info = owner_root.lstat()
        outcomes = Path(environment["AGENTMONITOR_TEST_M4_OWNER_OUTCOMES"])
        pid = int(service_pid)
        start_time_ticks = _process_start_ticks(pid)
        launch = _read_service_launch(
            pid, environment["AGENTMONITOR_TEST_DASHBOARD_ORIGIN"]
        )
        if (
            not owner_root.is_absolute()
            or owner_root.resolve(strict=True) != owner_root
            or test_root != owner_root
            or not stat.S_ISDIR(root_info.st_mode)
            or root_info.st_uid != os.getuid()
            or stat.S_IMODE(root_info.st_mode) != 0o700
            or launch.data_root != owner_root
            or outcomes != owner_root / "m4-owner-outcomes.json"
            or _process_start_ticks(pid) != start_time_ticks
        ):
            raise OSError
    except (M3CurrentExitErrorV1, OSError, RuntimeError):
        raise M4CurrentExitErrorV1("m4_current_service_selection_invalid") from None
    return (
        SelectedServiceV1(pid, start_time_ticks, launch),
        _private_file_digest(outcomes),
    )


def _run_command(
    command: tuple[str, ...] | list[str],
    environment: Mapping[str, str],
    *,
    timeout: int,
    blocked_reason: str,
    failed_reason: str,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        capture_output=capture,
        text=True,
        check=False,
        timeout=timeout,
    )
    if capture:
        if result.stdout:
            print(result.stdout.rstrip(), flush=True)
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr, flush=True)
    if result.returncode == 3:
        raise M4CurrentExitErrorV1(blocked_reason)
    if result.returncode != 0:
        raise M4CurrentExitFailedV1(failed_reason)
    return result


def _run_routine(routine: str, environment: Mapping[str, str]) -> None:
    _run_command(
        [sys.executable, "tools/automation/run.py", routine],
        environment,
        timeout=3600,
        blocked_reason=f"m4_current_{routine.lower()}_blocked",
        failed_reason=f"m4_current_{routine.lower()}_failed",
    )


def _run_story_suite(environment: Mapping[str, str]) -> int:
    _run_command(
        ["node", "--test", "tools/ui/test_m4_fleet_policy.mjs"],
        environment,
        timeout=60,
        blocked_reason="m4_current_fleet_policy_blocked",
        failed_reason="m4_current_fleet_policy_failed",
    )
    with tempfile.TemporaryDirectory(prefix="agentmonitor-m4-current-") as raw:
        report = Path(raw) / "results.xml"
        _run_command(
            [
                str(ROOT / "backend/.venv/bin/python"),
                "-m",
                "pytest",
                "tools/automation/test_m4_current_exit.py",
                *CURRENT_VERSION_TEST_PATHS,
                *TEST_PATHS,
                *STORY_PYTEST_FLAGS,
                f"--junitxml={report}",
            ],
            environment,
            timeout=1800,
            blocked_reason="m4_current_story_suite_blocked",
            failed_reason="m4_current_story_suite_failed",
        )
        try:
            suites = tuple(ET.parse(report).getroot().iter("testsuite"))
            test_count = sum(int(suite.get("tests", "0")) for suite in suites)
            skip_count = sum(int(suite.get("skipped", "0")) for suite in suites)
        except (OSError, ValueError, ET.ParseError):
            raise M4CurrentExitFailedV1("m4_current_story_report_invalid") from None
        if not suites or test_count < 1:
            raise M4CurrentExitFailedV1("m4_current_story_suite_empty")
        if skip_count:
            raise M4CurrentExitErrorV1("m4_current_story_suite_skipped")
        return test_count


def _run_fleet_browser(
    environment: Mapping[str, str], *, preflight: bool
) -> dict[str, object]:
    child_environment = dict(environment)
    if preflight:
        child_environment["AGENTMONITOR_M4_PREFLIGHT_ONLY"] = "1"
        child_environment.pop("AGENTMONITOR_M4_SERVICE_STARTED_AT", None)
    else:
        child_environment.pop("AGENTMONITOR_M4_PREFLIGHT_ONLY", None)
    result = _run_command(
        ["node", "tools/ui/verify_m4_fleet.mjs"],
        child_environment,
        timeout=450 if preflight else 900,
        blocked_reason=(
            "m4_current_fleet_preflight_blocked"
            if preflight
            else "m4_current_fleet_browser_blocked"
        ),
        failed_reason=(
            "m4_current_fleet_preflight_failed"
            if preflight
            else "m4_current_fleet_browser_failed"
        ),
        capture=True,
    )
    expected_event = "m4_fleet_preflight" if preflight else "m4_fleet_witness"
    witnesses: list[dict[str, object]] = []
    for line in result.stdout.splitlines():
        try:
            candidate = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict) and candidate.get("event") == expected_event:
            witnesses.append(candidate)
    if len(witnesses) != 1:
        raise M4CurrentExitFailedV1("m4_current_fleet_receipt_missing")
    return witnesses[0]


def _valid_witness_digest(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _validate_fleet_preflight_v1(preflight: Mapping[str, object]) -> None:
    if (
        preflight.get("event") != "m4_fleet_preflight"
        or preflight.get("account_count") != 6
        or preflight.get("organization_count") != 2
        or preflight.get("distinct_identity_count") != 6
        or preflight.get("current_history_count") != 6
        or preflight.get("mutations") != 0
        or not all(
            _valid_witness_digest(preflight.get(key))
            for key in (
                "fleet_metadata_digest",
                "identity_set_digest",
                "collection_run_set_digest",
            )
        )
    ):
        raise M4CurrentExitErrorV1("m4_current_fleet_preflight_invalid")


def validate_fleet_transition_v1(
    preflight: Mapping[str, object], witness: Mapping[str, object]
) -> tuple[str, str]:
    """Prove the same six identities received fresh current-revision readings."""

    _validate_fleet_preflight_v1(preflight)
    if witness.get("fleet_metadata_digest") != preflight.get("fleet_metadata_digest"):
        raise M4CurrentExitErrorV1("m4_current_fleet_metadata_changed")
    if witness.get("identity_set_digest") != preflight.get("identity_set_digest"):
        raise M4CurrentExitErrorV1("m4_current_fleet_identity_changed")
    if witness.get("collection_run_set_digest") == preflight.get(
        "collection_run_set_digest"
    ):
        raise M4CurrentExitErrorV1("m4_current_collection_not_fresh")
    if (
        witness.get("event") != "m4_fleet_witness"
        or witness.get("account_count") != 6
        or witness.get("organization_count") != 2
        or witness.get("distinct_identity_count") != 6
        or witness.get("current_history_count") != 6
        or witness.get("fresh_after_restart_count") != 6
        or witness.get("mutations") != 0
        or not _valid_witness_digest(witness.get("collection_run_set_digest"))
    ):
        raise M4CurrentExitErrorV1("m4_current_fleet_witness_invalid")
    return (
        str(preflight["fleet_metadata_digest"]),
        str(preflight["identity_set_digest"]),
    )


def main() -> int:
    service: ServiceProcessV1 | None = None
    try:
        missing = tuple(
            (story, path)
            for story, paths in STORY_ARTIFACTS.items()
            for path in paths
            if not (ROOT / path).is_file()
        )
        if missing:
            raise M4CurrentExitFailedV1("m4_current_story_artifact_missing")
        _validate_receipt_target_v1(RECEIPT_PATH)
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT / "backend/src")
        selected_service, owner_outcomes_digest = _validate_live_selection(environment)
        revision = _clean_revision()
        started_at = datetime.now(UTC)
        preflight = _run_fleet_browser(environment, preflight=True)
        _validate_fleet_preflight_v1(preflight)
        lane_evidence: dict[str, str] = {
            "fleet_preflight": "six_distinct_registered_identities_verified"
        }
        for lane, routine in PRE_SERVICE_ROUTINES:
            _run_routine(routine, environment)
            lane_evidence[lane] = f"{routine.lower()}_passed"
        service = _restart_service(
            selected_service.pid,
            environment["AGENTMONITOR_TEST_DASHBOARD_ORIGIN"],
            expected_launch=selected_service.launch,
            expected_start_ticks=selected_service.start_time_ticks,
        )
        service_started_at = datetime.now(UTC)
        environment["AGENTMONITOR_M4_SERVICE_STARTED_AT"] = (
            service_started_at.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        )
        lane_evidence["revision_bound_service"] = "service_restarted_from_clean_head"
        for routine in DEPENDENCY_ROUTINES:
            _run_routine(routine, environment)
        test_count = _run_story_suite(environment)
        lane_evidence["technical_suite"] = (
            f"auto_m3_test_and_pytest_{test_count}_passed_zero_skips"
        )
        witness = _run_fleet_browser(environment, preflight=False)
        fleet_digest, identity_digest = validate_fleet_transition_v1(preflight, witness)
        lane_evidence.update(
            registry_unchanged="pre_post_fleet_digest_matched",
            fresh_fleet_lineage="six_post_restart_runs_with_history",
        )
        for lane, script in BROWSER_CHECKS:
            _run_command(
                ["node", script],
                environment,
                timeout=900,
                blocked_reason=f"m4_current_{lane}_blocked",
                failed_reason=f"m4_current_{lane}_failed",
            )
            lane_evidence[lane] = f"{lane}_passed"
        for lane, routine in LOCAL_ROUTINES:
            _run_routine(routine, environment)
            lane_evidence[lane] = f"{routine.lower()}_passed"
        if revision != _clean_revision():
            raise M4CurrentExitErrorV1("m4_current_checkout_revision_changed")
        outcomes_path = Path(environment["AGENTMONITOR_TEST_M4_OWNER_OUTCOMES"])
        if owner_outcomes_digest != _private_file_digest(outcomes_path):
            raise M4CurrentExitErrorV1("m4_current_owner_outcomes_changed")
        completed_at = datetime.now(UTC)
        receipt = build_passed_receipt_v1(
            implementation_revision=revision,
            started_at=started_at,
            completed_at=completed_at,
            owner_outcomes_digest=owner_outcomes_digest,
            fleet_metadata_digest=fleet_digest,
            identity_set_digest=identity_digest,
            test_count=test_count,
            lane_evidence=lane_evidence,
        )
        write_verified_receipt_v1(service, RECEIPT_PATH, receipt)
    except M4CurrentExitFailedV1 as error:
        print(f"M4 CURRENT EXIT: FAILED — {error}")
        return 1
    except (M4CurrentExitErrorV1, M3CurrentExitErrorV1) as error:
        print(f"M4 CURRENT EXIT: BLOCKED — {error}")
        return 3
    except (OSError, subprocess.TimeoutExpired, ValueError):
        print("M4 CURRENT EXIT: FAILED — execution_unavailable")
        return 1
    finally:
        if service is not None:
            try:
                os.close(service.pidfd)
            except OSError:
                pass
    print(
        "M4 CURRENT EXIT: PASSED — exact revision, six distinct Claude identities, "
        "fresh fleet lineage, Overview, alerts, operations and local gates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Execute bounded M7 checks without treating a partial slice as milestone proof.

Pure calculations, critical mutations and an explicit registry metadata slice
execute real tests. Full registry setup and other named boundaries remain Not Run
until their real implementation lands.
No ticket flag, owner-entered result or historical receipt can make them pass.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from tools.automation.implementations.auto_m6_exit import (
    M6ExitErrorV1,
    _temporary_tool_environment,
)

ROOT = Path(__file__).resolve().parents[3]
Status = Literal["passed", "failed", "blocked", "not_run"]
Lane = Literal[
    "pure",
    "mutation",
    "registry_metadata",
    "technical",
    "live",
    "browser",
    "deploy",
    "exit",
]

PURE_TARGETS = (
    "backend/tests/capacity/pure/test_budget_exact_arithmetic.py",
    "backend/tests/capacity/pure/test_budget_money.py",
    "backend/tests/capacity/pure/test_budget_aggregation.py",
    "backend/tests/contracts/test_budget_report_contract.py",
    "backend/tests/capacity/pure/test_budget_report_selection.py",
    "backend/tests/capacity/test_quantity_and_health.py",
)
REGISTRY_METADATA_TARGETS = (
    "backend/tests/registry/test_billing_credential_status.py",
    "backend/tests/integration/registry/test_billing_account_intent.py",
    "backend/tests/integration/registry/test_billing_connections.py",
    "backend/tests/integration/registry/test_billing_credential_binding.py",
    "backend/tests/integration/api/test_billing_enrollment_http.py",
)
REQUIRED_CHECKS: dict[str, tuple[str, ...]] = {
    "pure": ("pure",),
    "mutation": ("mutation",),
    "registry_metadata": ("registry_metadata",),
    "technical": (
        "pure",
        "registry_metadata",
        "registry_http",
        "persistence",
        "collection",
        "budget_http",
        "compatibility",
        "mutation",
    ),
    "live": ("anthropic", "openai", "ollama", "configured_inventory", "recovery"),
    "browser": ("owner_setup", "overview", "detail_history", "accessibility"),
    "deploy": ("candidate", "backup_recovery", "installed_revision", "continuity"),
    "exit": ("technical", "live", "browser", "deploy"),
}


@dataclass(frozen=True, slots=True)
class CheckResult:
    """One execution result; never contains account, credential or provider data."""

    name: str
    status: Status
    reason_code: str | None = None


@dataclass(frozen=True, slots=True)
class LaneResult:
    """A scope-bearing result, not an owner-acceptance or publication receipt."""

    lane: str
    status: Status
    checks: tuple[CheckResult, ...]


def evaluate_lane(lane: str, checks: tuple[CheckResult, ...]) -> LaneResult:
    """Require each named boundary once; absent/unexecuted evidence cannot pass."""
    if lane not in REQUIRED_CHECKS:
        raise ValueError("m7_lane_unknown")
    names = tuple(check.name for check in checks)
    required = set(REQUIRED_CHECKS[lane])
    if len(set(names)) != len(names) or set(names) - required:
        return LaneResult(lane, "failed", checks)
    if any(check.status == "failed" for check in checks):
        return LaneResult(lane, "failed", checks)
    if set(names) != required or any(check.status != "passed" for check in checks):
        return LaneResult(lane, "blocked", checks)
    return LaneResult(lane, "passed", checks)


def _run_pytest(name: str, targets: tuple[str, ...]) -> CheckResult:
    missing = tuple(target for target in targets if not (ROOT / target).is_file())
    if missing:
        # Paths are fixed repository-owned selections, not external input.
        for target in missing:
            print(f"M7 REQUIRED SUITE NOT RUN: {target}", flush=True)
        return CheckResult(name, "not_run", "m7_required_suite_missing")
    command = [
        str(ROOT / "backend/.venv/bin/python"),
        "-m",
        "pytest",
        "-c",
        "backend/pyproject.toml",
        *targets,
        "-q",
        "--tb=short",
        "-p",
        "tools.automation.pytest_no_skip",
    ]
    try:
        with _temporary_tool_environment():
            result = subprocess.run(command, cwd=ROOT, timeout=180, check=False)
    except subprocess.TimeoutExpired:
        return CheckResult(name, "failed", "m7_test_timeout")
    except (OSError, M6ExitErrorV1):
        return CheckResult(name, "blocked", "m7_test_toolchain_unavailable")
    if result.returncode != 0:
        return CheckResult(name, "failed", "m7_tests_failed_or_empty")
    return CheckResult(name, "passed")


def execute_lane(lane: str) -> LaneResult:
    """Run implemented boundaries; report the rest without inventing evidence."""
    if lane not in REQUIRED_CHECKS:
        raise ValueError("m7_lane_unknown")
    checks: list[CheckResult] = []
    for name in REQUIRED_CHECKS[lane]:
        if name == "pure":
            check = _run_pytest("pure", PURE_TARGETS)
        elif name == "mutation":
            check = _run_pytest(
                "mutation", ("tools/automation/test_m7_budget_mutation_policies.py",)
            )
        elif name == "registry_metadata":
            print(
                "M7 SLICE: account intent, connection metadata and nonsecret binding "
                "lifecycle over real SQLite/HTTP; secret entry, "
                "credential verification "
                "and full registry flow remain separate",
                flush=True,
            )
            check = _run_pytest("registry_metadata", REGISTRY_METADATA_TARGETS)
        elif lane == "exit":
            child = execute_lane(name)
            check = CheckResult(name, child.status)
        else:
            check = CheckResult(name, "not_run", "m7_boundary_runner_not_implemented")
        checks.append(check)
        reason = f" ({check.reason_code})" if check.reason_code else ""
        print(f"M7 CHECK {name}: {check.status.upper()}{reason}", flush=True)
    return evaluate_lane(lane, tuple(checks))


def validate_selection(lane: str, check: str | None, expected: str | None) -> None:
    """Only the existing deployment lane admits this explicit operational slice."""
    if check is None and expected is None:
        return
    if (
        lane != "deploy"
        or check != "setup_activation"
        or expected is None
        or re.fullmatch(r"[a-f0-9]{40}", expected) is None
    ):
        raise ValueError("m7_selection_invalid")


def selected_setup_revision(controller: Path, expected: str) -> str:
    """Observe the selected revision from real Git, without installed actions."""
    from tools.automation.implementations.m6_frontend_build import _clean_revision

    if (
        re.fullmatch(r"[a-f0-9]{40}", expected) is None
        or not controller.is_absolute()
        or controller.resolve() != controller
    ):
        raise RuntimeError("m7_setup_controller_invalid")
    revision = _clean_revision(controller)
    if revision != expected:
        raise RuntimeError("m7_setup_revision_mismatch")
    return revision


def verify_setup_controller(controller: Path, expected: str) -> None:
    """Require the existing fixed retained-release seal before service access."""
    from tools.automation.implementations.m6_cutover import (
        _FIXED_RELEASES,
        _verify_retained_baseline,
    )

    selected_setup_revision(controller, expected)
    if controller.parent != _FIXED_RELEASES:
        raise RuntimeError("m7_setup_controller_not_retained")
    revision, _ = _verify_retained_baseline(controller)
    if revision != expected:
        raise RuntimeError("m7_setup_revision_mismatch")


def setup_activation_result(checks: tuple[CheckResult, ...]) -> LaneResult:
    """Operational readiness alone cannot accept installed product workflows."""
    remaining = tuple(
        CheckResult(name, "not_run", "m7_separate_real_evidence_required")
        for name in ("authenticated_setup", "collector_continuity", "backup_recovery")
    )
    return LaneResult(
        "deploy/setup_activation",
        "failed" if any(check.status == "failed" for check in checks) else "blocked",
        checks + remaining,
    )


def closed_setup_command_reason(output: bytes) -> str:
    """Expose only exact known wrapper messages as fixed codes, never raw output."""
    messages = {
        "M6 CUTOVER: BLOCKED — review the transition journal and service state": (
            "m7_setup_cutover_journal_review"
        ),
        (
            "M6 CANDIDATE FINALIZE: BLOCKED — "
            "review the transition journal and service state"
        ): ("m7_setup_finalize_journal_review"),
        "M6 CUTOVER: BLOCKED — expected checkout revision does not match": (
            "m7_setup_revision_mismatch"
        ),
        "M6 CUTOVER: BLOCKED — operator checkout or runtime unavailable": (
            "m7_setup_runtime_unavailable"
        ),
        "M6 CANDIDATE FINALIZE: BLOCKED — operator checkout or runtime unavailable": (
            "m7_setup_runtime_unavailable"
        ),
        "M6 CUTOVER: BLOCKED — private runtime unavailable": (
            "m7_setup_runtime_unavailable"
        ),
        "M6 CANDIDATE FINALIZE: BLOCKED — private runtime unavailable": (
            "m7_setup_runtime_unavailable"
        ),
    }
    return {key.encode(): value for key, value in messages.items()}.get(
        output.strip(), "m7_setup_command_failed"
    )


def _setup_process(arguments: list[str], *, timeout: int) -> None:
    """Run fixed owned code with no inherited credentials or captured output leaks."""
    from tools.automation.implementations.m6_cutover import _FIXED_VENV

    completed = subprocess.run(
        [str(_FIXED_VENV / "bin/python"), "-B", *arguments],
        cwd=ROOT,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": "/home/dev",
            "LANG": "C",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(ROOT / "backend/src") + os.pathsep + str(ROOT),
        },
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if len(completed.stdout) > 16384:
        raise RuntimeError("m7_setup_command_failed")
    if completed.returncode:
        raise RuntimeError(closed_setup_command_reason(completed.stdout))
    if "agentmonitor.composition.billing_credential_operator" in arguments and not all(
        flag in completed.stdout
        for flag in (b"--account-id", b"--resource-id", b"--data-root")
    ):
        raise RuntimeError("m7_setup_operator_unavailable")


def execute_setup_activation(expected: str) -> LaneResult:
    """Initial 0720→0731 setup rollout only, never complete M7 deployment."""
    checks: list[CheckResult] = []
    stage = "controller_preflight"
    started = False
    try:
        verify_setup_controller(ROOT, expected)
        from tools.automation.implementations.auto_m6_local_activate import request
        from tools.automation.implementations.m6_cutover import (
            _FIXED_DATA,
            _FIXED_EXECUTABLE,
            _FIXED_UNIT,
            DatabaseRefV1,
            _candidate_override,
            _verify_active_source_schema,
            _verify_candidate_runtime,
            load_migration_catalog,
        )

        if load_migration_catalog().head != "v1_0731":
            raise RuntimeError("m7_setup_schema_selection_invalid")
        _verify_active_source_schema(
            DatabaseRefV1(_FIXED_DATA / "agentmonitor.db", _FIXED_DATA), "v1_0720"
        )
        checks.append(CheckResult(stage, "passed"))
        stage = "candidate_started"
        print("M7 SETUP OPERATION: initial setup activation only", flush=True)
        started = True
        _setup_process(
            [
                "tools/automation/implementations/auto_m6_cutover.py",
                "--expected-revision=" + expected,
            ],
            timeout=600,
        )
        checks.append(CheckResult(stage, "passed"))

        def installed_ready() -> None:
            verify_setup_controller(ROOT, expected)
            _verify_candidate_runtime(
                root=_FIXED_DATA,
                unit=_FIXED_UNIT,
                checkout=ROOT,
                origin="http://127.0.0.1:43110",
                executable=_FIXED_EXECUTABLE,
                expected_command=_candidate_override(ROOT)
                .split("ExecStart=\nExecStart=", 1)[1]
                .strip()
                .split(),
            )

        stage = "installed_revision_loopback"
        deadline = time.monotonic() + 20
        while True:
            try:
                installed_ready()
                break
            except (OSError, RuntimeError, ValueError):
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.2)
        checks.append(CheckResult(stage, "passed"))
        stage = "restart_finalized"
        verify_setup_controller(ROOT, expected)
        _setup_process(
            ["tools/automation/implementations/auto_m6_finalize_candidate.py"],
            timeout=90,
        )
        installed_ready()
        checks.append(CheckResult(stage, "passed"))
        stage = "operator_command"
        _setup_process(
            ["-m", "agentmonitor.composition.billing_credential_operator", "--help"],
            timeout=30,
        )
        checks.append(CheckResult(stage, "passed"))
        stage = "lan_readiness"
        status, body = request("http://192.168.1.18:43110", "/login")
        if status != 200 or b"agentmonitor-dashboard-root" not in body:
            raise RuntimeError("m7_setup_lan_unavailable")
        checks.append(CheckResult(stage, "passed"))
        stage = "installed_postcheck"
        installed_ready()
        checks.append(CheckResult(stage, "passed"))
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        known = {
            "m7_setup_cutover_journal_review",
            "m7_setup_finalize_journal_review",
            "m7_setup_revision_mismatch",
            "m7_setup_runtime_unavailable",
            "m7_setup_command_failed",
            "m7_setup_operator_unavailable",
            "m7_setup_lan_unavailable",
            "m7_setup_schema_selection_invalid",
            "m7_setup_controller_not_retained",
        }
        reason = (
            str(error)
            if str(error) in known
            else (
                "m7_setup_operation_requires_review"
                if started
                else "m7_setup_preflight_refused"
            )
        )
        checks.append(CheckResult(stage, "failed" if started else "blocked", reason))
    result = setup_activation_result(tuple(checks))
    for check in result.checks:
        reason = f" ({check.reason_code})" if check.reason_code else ""
        print(f"M7 CHECK {check.name}: {check.status.upper()}{reason}", flush=True)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", required=True, choices=tuple(REQUIRED_CHECKS))
    parser.add_argument("--check", choices=("setup_activation",))
    parser.add_argument("--expected-revision")
    args = parser.parse_args(argv)
    try:
        validate_selection(args.lane, args.check, args.expected_revision)
    except ValueError:
        parser.error(
            "setup_activation requires --lane deploy and --expected-revision=<40SHA>"
        )
    result = (
        execute_setup_activation(args.expected_revision)
        if args.check == "setup_activation"
        else execute_lane(args.lane)
    )
    if result.lane == "deploy/setup_activation":
        scope = (
            "setup operational slice; authenticated setup, collector continuity and "
            "backup/recovery proof remain separate; "
            "not full deployment or M7 acceptance"
        )
    elif result.lane in {"pure", "mutation"}:
        scope = (
            "pure policy verification only; "
            "no database, HTTP, browser or provider claim"
        )
    elif result.lane == "registry_metadata":
        scope = (
            "registry metadata and nonsecret binding lifecycle only; "
            "no secret entry, activation or provider access claim"
        )
    else:
        scope = f"{result.lane}; no milestone acceptance or publication claim"
    print(f"M7 RESULT: {result.status.upper()} — {scope}", flush=True)
    return {"passed": 0, "failed": 1, "blocked": 3, "not_run": 3}[result.status]


if __name__ == "__main__":
    raise SystemExit(main())

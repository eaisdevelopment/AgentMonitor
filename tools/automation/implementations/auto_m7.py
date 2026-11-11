"""Execute bounded M7 checks without treating a partial slice as milestone proof.

Pure calculations, critical mutations and an explicit registry metadata slice
execute real tests. Full registry setup and other named boundaries remain Not Run
until their real implementation lands.
No ticket flag, owner-entered result or historical receipt can make them pass.
"""

from __future__ import annotations

import argparse
import subprocess
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
    "backend/tests/contracts/test_budget_report_contract.py",
    "backend/tests/capacity/pure/test_budget_report_selection.py",
    "backend/tests/capacity/test_quantity_and_health.py",
)
REGISTRY_METADATA_TARGETS = (
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
                "lifecycle over real SQLite/HTTP; secret entry, credential verification "
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", required=True, choices=tuple(REQUIRED_CHECKS))
    args = parser.parse_args(argv)
    result = execute_lane(args.lane)
    if result.lane in {"pure", "mutation"}:
        scope = "pure policy verification only; no database, HTTP, browser or provider claim"
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

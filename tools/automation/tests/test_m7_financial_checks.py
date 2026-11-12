"""Real canonical guard checks cannot stand in for populated financial delivery."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tools.automation.implementations.auto_m7 import validate_selection

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    "check", ("collection_guards", "budget_http_guards", "queued_expiry_history")
)
def test_guard_selection_is_narrow_and_needs_no_deployment_revision(check: str) -> None:
    """Pure selection policy: guards belong only to the technical lane."""
    validate_selection("technical", check, None)
    for lane, revision in (("live", None), ("deploy", None), ("technical", "a" * 40)):
        with pytest.raises(ValueError, match="m7_selection_invalid"):
            validate_selection(lane, check, revision)


@pytest.mark.parametrize(
    ("check", "scope"),
    (
        (
            "collection_guards",
            "no successful provider collection or report commit claim",
        ),
        ("budget_http_guards", "no populated money, summary, history or browser claim"),
    ),
)
def test_selected_guard_command_executes_real_existing_suites(
    check: str, scope: str
) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.automation.implementations.auto_m7",
            "--lane",
            "technical",
            "--check",
            check,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert " passed in " in result.stdout
    assert f"M7 CHECK {check}: PASSED" in result.stdout
    assert "M7 RESULT: PASSED" in result.stdout
    assert scope in result.stdout
    assert "M7 CHECK collection: PASSED" not in result.stdout
    assert "M7 CHECK budget_http: PASSED" not in result.stdout


def test_full_technical_runs_guards_but_reports_missing_populated_boundaries() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.automation.implementations.auto_m7",
            "--lane",
            "technical",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 3, result.stdout + result.stderr
    for check in ("collection_guards", "budget_http_guards"):
        assert f"M7 CHECK {check}: PASSED" in result.stdout
    assert (
        "M7 CHECK collection: NOT_RUN (m7_genuine_report_collection_not_implemented)"
        in result.stdout
    )
    assert (
        "M7 CHECK budget_http: NOT_RUN (m7_populated_budget_http_not_implemented)"
        in result.stdout
    )
    assert "M7 RESULT: BLOCKED" in result.stdout

"""Real checkout refusal; no deployment, provider call or constructed service."""

import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tools.automation.implementations import auto_m7
from tools.automation.implementations.m7_exit_receipt import TimedCheck


def test_exit_refuses_wrong_real_checkout_before_observing_service() -> None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=auto_m7.ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    other = "0" * 40 if head != "0" * 40 else "1" * 40
    with pytest.raises(
        (ValueError, RuntimeError), match="source_not_clean|source_revision_mismatch"
    ):
        auto_m7.observe_exit_context(other)


def test_real_exit_command_without_revision_refuses_before_checks() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.automation.implementations.auto_m7",
            "--lane",
            "exit",
        ],
        cwd=auto_m7.ROOT,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        env={
            key: value
            for key, value in os.environ.items()
            if key != "AGENTMONITOR_M7_EXPECTED_REVISION"
        },
    )
    assert result.returncode == 3
    assert "M7 RESULT: BLOCKED" in result.stdout
    assert "M7 CHECK pure" not in result.stdout
    assert "M7 EXIT RECEIPT:" not in result.stdout


def test_canonical_exit_passes_explicit_nonsecret_revision_to_admission() -> None:
    result = subprocess.run(
        [sys.executable, "tools/automation/run.py", "AUTO-M7-EXIT"],
        cwd=auto_m7.ROOT,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        env=dict(
            os.environ,
            AGENTMONITOR_M7_EXPECTED_REVISION="0" * 40,
            PATH=str(Path(sys.executable).parent)
            + os.pathsep
            + os.environ.get("PATH", "/usr/bin:/bin"),
        ),
    )
    assert result.returncode == 3
    assert "m7_expected_installed_revision_required" not in result.stdout
    assert (
        "frontend_source_not_clean" in result.stdout
        or "m7_exit_source_revision_mismatch" in result.stdout
    )
    assert "M7 CHECK pure" not in result.stdout
    assert "M7 EXIT RECEIPT:" not in result.stdout


def test_real_schema_lane_records_its_actual_result_and_execution_times() -> None:
    observations: list[TimedCheck] = []
    started = datetime.now(UTC)
    result = auto_m7.execute_lane("persistence_schema", observations=observations)
    finished = datetime.now(UTC)
    assert result.status == "passed"
    assert len(observations) == 1
    observed = observations[0]
    assert (observed.lane, observed.name, observed.status) == (
        "persistence_schema",
        "persistence_schema",
        result.status,
    )
    assert started <= observed.started_at <= observed.finished_at <= finished

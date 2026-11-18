"""Explicit marker activation selection and real isolated schema rehearsal."""

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from tools.automation.implementations import auto_m7, m7_setup_activation

ROOT = Path(__file__).resolve().parents[3]


def test_model_activation_requires_exact_deploy_selection() -> None:
    auto_m7.validate_selection("deploy", "model_activation", "a" * 40)
    for selection in (
        ("exit", "model_activation", "a" * 40),
        ("deploy", "model_activation", None),
        ("deploy", "model_activation", "bad"),
    ):
        with pytest.raises(ValueError, match="m7_selection_invalid"):
            auto_m7.validate_selection(*selection)


def test_model_operation_does_not_accept_full_deployment() -> None:
    result = auto_m7.setup_activation_result(
        (auto_m7.CheckResult("installed_revision_loopback", "passed"),), model=True
    )
    assert result.lane == "deploy/model_activation"
    assert result.status == "blocked"
    assert {check.name for check in result.checks if check.status == "not_run"} == {
        "authenticated_financial",
        "collector_continuity",
        "backup_recovery",
    }
    assert auto_m7.evaluate_lane("deploy", result.checks).status != "passed"


def test_model_rehearsal_preserves_real_predecessor_backup(tmp_path: Path) -> None:
    # Keep the actual 0735 catalog/operator for this historical marker transition.
    checkout = tmp_path / "model-candidate"
    subprocess.run(
        [
            "/usr/bin/git",
            "clone",
            "--quiet",
            "--no-hardlinks",
            str(ROOT),
            str(checkout),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "/usr/bin/git",
            "checkout",
            "--quiet",
            "--detach",
            "e25765dd4636cd54f4427bbb05b2f03f394a8948",
        ],
        cwd=checkout,
        check=True,
        capture_output=True,
    )
    workspace = tmp_path / "rehearsal"
    result = m7_setup_activation._candidate_process(
        checkout,
        Path(sys.executable),
        ["-c", m7_setup_activation._REHEARSAL, str(workspace), "model"],
        timeout=180,
    )
    assert result.returncode == 0, "real model-marker rehearsal failed"
    facts = json.loads(result.stdout)
    assert facts["source_revision"] == "v1_0734"
    assert facts["target_revision"] == "v1_0735"
    assert facts["blockers"] == []
    schemas = []
    for location, revision in (
        (workspace / "agentmonitor.db", "v1_0735"),
        (workspace / "backup/agentmonitor.db", "v1_0734"),
    ):
        with sqlite3.connect(
            f"{location.as_uri()}?mode=ro&immutable=1", uri=True
        ) as connection:
            assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
            assert connection.execute(
                "SELECT version_num FROM alembic_version"
            ).fetchone() == (revision,)
            schemas.append(
                connection.execute(
                    "SELECT type,name,sql FROM sqlite_schema ORDER BY type,name"
                ).fetchall()
            )
            assert connection.execute(
                "SELECT count(*) FROM capacity_budget_report"
            ).fetchone() == (0,)
        assert location.stat().st_mode & 0o777 == 0o600
    assert schemas[0] == schemas[1]


def test_model_cli_rejects_unretained_controller_without_starting() -> None:
    result = m7_setup_activation._candidate_process(
        ROOT,
        Path(sys.executable),
        [
            "-m",
            "tools.automation.implementations.auto_m7",
            "--lane",
            "deploy",
            "--check",
            "model_activation",
            "--expected-revision=" + "a" * 40,
        ],
        timeout=15,
    )
    assert result.returncode == 3
    assert "controller_preflight" in result.stdout
    assert "M7 MODEL OPERATION" not in result.stdout

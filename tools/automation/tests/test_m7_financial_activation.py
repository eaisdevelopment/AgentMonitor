"""Financial activation admission and empty SQLite; no installed actions."""

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from tools.automation.implementations import auto_m7, m7_setup_activation

ROOT = Path(__file__).resolve().parents[3]


def test_financial_selection_requires_explicit_deploy_revision() -> None:
    auto_m7.validate_selection("deploy", "financial_activation", "a" * 40)
    for selection in (
        ("exit", "financial_activation", "a" * 40),
        ("deploy", "financial_activation", None),
        ("deploy", "financial_activation", "bad"),
    ):
        with pytest.raises(ValueError, match="m7_selection_invalid"):
            auto_m7.validate_selection(*selection)


def test_financial_rehearsal_uses_real_installed_predecessor(tmp_path: Path) -> None:
    workspace = tmp_path / "schema-rehearsal"
    result = m7_setup_activation._candidate_process(
        ROOT,
        Path(sys.executable),
        ["-c", m7_setup_activation._REHEARSAL, str(workspace), "financial"],
        timeout=180,
    )
    assert result.returncode == 0, "actual empty migration rehearsal must execute"
    facts = json.loads(result.stdout)
    assert facts["source_revision"] == "v1_0731"
    assert facts["target_revision"] == "v1_0733"
    assert facts["blockers"] == []
    for location, revision in (
        (workspace / "agentmonitor.db", "v1_0733"),
        (workspace / "backup/agentmonitor.db", "v1_0731"),
    ):
        with sqlite3.connect(f"{location.as_uri()}?mode=ro", uri=True) as connection:
            assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
            assert connection.execute(
                "SELECT version_num FROM alembic_version"
            ).fetchone() == (revision,)
            assert connection.execute(
                "SELECT count(*) FROM reg_account"
            ).fetchone() == (0,)
        assert location.stat().st_mode & 0o777 == 0o600
    with sqlite3.connect(
        f"{(workspace / 'agentmonitor.db').as_uri()}?mode=ro", uri=True
    ) as connection:
        for table in ("capacity_budget_report", "collection_budget_run"):
            assert connection.execute(f"SELECT count(*) FROM {table}").fetchone() == (
                0,
            )


def test_unknown_preparation_phase_refuses_before_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "invalid"
    result = m7_setup_activation._candidate_process(
        ROOT,
        Path(sys.executable),
        ["-c", m7_setup_activation._REHEARSAL, str(workspace), "other"],
        timeout=180,
    )
    assert result.returncode != 0
    assert not workspace.exists()


def test_financial_operational_slice_cannot_close_deploy() -> None:
    result = auto_m7.setup_activation_result(
        (auto_m7.CheckResult("installed_revision_loopback", "passed"),),
        financial=True,
    )
    assert result.lane == "deploy/financial_activation"
    assert result.status == "blocked"
    assert {check.name for check in result.checks if check.status == "not_run"} == {
        "authenticated_financial",
        "collector_continuity",
        "backup_recovery",
    }
    assert auto_m7.evaluate_lane("deploy", result.checks).status != "passed"


@pytest.fixture
def financial_checkout(tmp_path: Path) -> tuple[Path, str]:
    checkout = tmp_path / "selected"
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
    # Commit only the current actual operator sources into an isolated test clone.
    # No provider data, replacement collaborators or installed controls are added.
    for filename in (
        "auto_m7.py",
        "m7_setup_activation.py",
        "auto_m6_cutover.py",
        "m6_cutover.py",
        "m6_cutover_diagnostics.py",
    ):
        relative = Path("tools/automation/implementations") / filename
        (checkout / relative).write_bytes((ROOT / relative).read_bytes())
        subprocess.run(["/usr/bin/git", "add", str(relative)], cwd=checkout, check=True)
    subprocess.run(
        [
            "/usr/bin/git",
            "-c",
            "user.name=Controller test",
            "-c",
            "user.email=controller@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "--allow-empty",
            "-m",
            "Test current financial activation",
        ],
        cwd=checkout,
        check=True,
        capture_output=True,
    )
    revision = subprocess.check_output(
        ["/usr/bin/git", "rev-parse", "HEAD"],
        cwd=checkout,
        text=True,
    ).strip()
    return checkout, revision


def test_financial_cli_refuses_clean_unretained_controller(
    financial_checkout: tuple[Path, str],
) -> None:
    checkout, revision = financial_checkout
    result = m7_setup_activation._candidate_process(
        checkout,
        Path(sys.executable),
        [
            "-m",
            "tools.automation.implementations.auto_m7",
            "--lane",
            "deploy",
            "--check",
            "financial_activation",
            "--expected-revision=" + revision,
        ],
        timeout=15,
    )
    assert result.returncode == 3
    assert "controller_preflight" in result.stdout
    assert "m7_setup_controller_not_retained" in result.stdout
    assert "M7 FINANCIAL OPERATION" not in result.stdout


def test_financial_candidate_build_and_backup_rehearsal(
    tmp_path: Path,
    financial_checkout: tuple[Path, str],
) -> None:
    from tools.automation.implementations.m6_candidate_release import (
        verify_candidate_release,
    )

    checkout, revision = financial_checkout
    workspace = tmp_path / "preparation"
    modules = Path(
        "/home/dev/.local/share/agentmonitor/worktrees/dashboard-product-promotion"
        "/frontend/node_modules"
    )
    result = m7_setup_activation.prepare_setup_activation(
        candidate=checkout,
        expected_revision=revision,
        workspace=workspace,
        tool_modules=modules,
        python_executable=Path(sys.executable),
        phase="financial",
    )
    assert result.status == "prepared"
    assert result.blockers == ()
    assert result.source_revision == "v1_0731"
    assert result.target_revision == "v1_0733"
    assert result.revision == revision
    release = Path(result.release)
    assert verify_candidate_release(
        release,
        workspace / "releases",
        revision,
        result.build_digest,
    )
    assert (
        json.loads((workspace / "preparation.json").read_text())["revision"] == revision
    )
    assert (workspace / "preparation.json").stat().st_mode & 0o777 == 0o600
    assert not (release / "frontend/node_modules").exists()
    assert not (checkout / "frontend/node_modules").exists()
    assert not list(workspace.rglob("*.env"))
    assert (
        subprocess.check_output(
            ["/usr/bin/git", "status", "--porcelain"],
            cwd=checkout,
        )
        == b""
    )
    for location, expected in (
        (workspace / "schema-rehearsal/agentmonitor.db", "v1_0733"),
        (workspace / "schema-rehearsal/backup/agentmonitor.db", "v1_0731"),
    ):
        with sqlite3.connect(f"{location.as_uri()}?mode=ro", uri=True) as connection:
            assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
            assert connection.execute(
                "SELECT version_num FROM alembic_version"
            ).fetchone() == (expected,)
            assert connection.execute(
                "SELECT count(*) FROM reg_account"
            ).fetchone() == (0,)

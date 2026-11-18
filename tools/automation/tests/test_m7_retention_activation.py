"""Reviewed retention activation and real isolated pre-upgrade backup."""

import json
import sqlite3
import sys
from pathlib import Path

import pytest

from tools.automation.implementations import auto_m7, auto_migrate, m7_setup_activation
from tools.automation.implementations.m6_cutover import _retained_migration_source

ROOT = Path(__file__).resolve().parents[3]


def test_retention_activation_requires_exact_deploy_selection() -> None:
    auto_m7.validate_selection("deploy", "retention_activation", "a" * 40)
    for selection in (
        ("exit", "retention_activation", "a" * 40),
        ("deploy", "retention_activation", None),
        ("deploy", "retention_activation", "bad"),
    ):
        with pytest.raises(ValueError, match="m7_selection_invalid"):
            auto_m7.validate_selection(*selection)


def test_retention_operator_preserves_earlier_admissions() -> None:
    assert auto_migrate.TARGET == "v1_0736"
    assert "v1_0735" in auto_migrate.SOURCES
    assert _retained_migration_source("v1_0736") == "v1_0735"
    assert _retained_migration_source("v1_0735") == "v1_0734"
    assert _retained_migration_source("v1_0737") is None
    catalog, tail = auto_migrate._preflight_catalog("v1_0735")
    assert catalog.head == "v1_0736" and tail == ("v1_0736",)


def test_retention_operation_does_not_accept_full_deployment() -> None:
    result = auto_m7.setup_activation_result(
        (auto_m7.CheckResult("installed_revision_loopback", "passed"),), retention=True
    )
    assert result.lane == "deploy/retention_activation"
    assert result.status == "blocked"
    assert {check.name for check in result.checks if check.status == "not_run"} == {
        "authenticated_financial",
        "collector_continuity",
        "backup_recovery",
    }
    assert auto_m7.evaluate_lane("deploy", result.checks).status != "passed"


def test_retention_rehearsal_preserves_real_predecessor_backup(tmp_path: Path) -> None:
    workspace = tmp_path / "rehearsal"
    result = m7_setup_activation._candidate_process(
        ROOT,
        Path(sys.executable),
        ["-c", m7_setup_activation._REHEARSAL, str(workspace), "retention"],
        timeout=180,
    )
    assert result.returncode == 0, "real retention rehearsal refused"
    facts = json.loads(result.stdout)
    assert facts["source_revision"] == "v1_0735"
    assert facts["target_revision"] == "v1_0736"
    assert facts["blockers"] == []
    schemas = []
    for location, revision in (
        (workspace / "agentmonitor.db", "v1_0736"),
        (workspace / "backup/agentmonitor.db", "v1_0735"),
    ):
        with sqlite3.connect(
            f"{location.as_uri()}?mode=ro&immutable=1", uri=True
        ) as conn:
            assert conn.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
            assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
            assert conn.execute(
                "SELECT version_num FROM alembic_version"
            ).fetchone() == (revision,)
            schemas.append(
                set(conn.execute("SELECT type,name,sql FROM sqlite_schema").fetchall())
            )
            assert conn.execute(
                "SELECT count(*) FROM capacity_budget_report"
            ).fetchone() == (0,)
            if revision == "v1_0736":
                assert conn.execute(
                    "SELECT count(*) FROM capacity_budget_expired_report"
                ).fetchone() == (0,)
        assert location.stat().st_mode & 0o777 == 0o600
    assert schemas[1] < schemas[0]
    assert all(
        "capacity_budget_expired_report" in row[1] for row in schemas[0] - schemas[1]
    )


def test_retention_cli_rejects_unretained_controller_without_starting() -> None:
    result = m7_setup_activation._candidate_process(
        ROOT,
        Path(sys.executable),
        [
            "-m",
            "tools.automation.implementations.auto_m7",
            "--lane",
            "deploy",
            "--check",
            "retention_activation",
            "--expected-revision=" + "a" * 40,
        ],
        timeout=15,
    )
    assert result.returncode == 3
    assert "controller_preflight" in result.stdout
    assert "M7 RETENTION OPERATION" not in result.stdout

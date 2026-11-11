"""Real clean-checkout and isolated storage preparation; no installed service."""

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from tools.automation.implementations.m6_candidate_release import (
    verify_candidate_release,
)
from tools.automation.implementations.m6_frontend_build import FrontendBuildError
from tools.automation.implementations.m7_setup_activation import (
    SetupPreparationError,
    main,
    prepare_setup_activation,
)

MODULES = Path(
    "/home/dev/.local/share/agentmonitor/worktrees/dashboard-product-promotion"
    "/frontend/node_modules"
)


@pytest.fixture
def selected(tmp_path: Path) -> tuple[Path, str]:
    source = Path(__file__).resolve().parents[3]
    candidate = tmp_path / "selected"
    subprocess.run(
        [
            "/usr/bin/git",
            "clone",
            "--quiet",
            "--no-hardlinks",
            str(source),
            str(candidate),
        ],
        check=True,
        capture_output=True,
    )
    revision = subprocess.check_output(
        ["/usr/bin/git", "rev-parse", "HEAD"], cwd=candidate, text=True
    ).strip()
    return candidate, revision


def test_real_candidate_build_schema_backup_and_actual_policy(
    tmp_path: Path, selected: tuple[Path, str], capsys: pytest.CaptureFixture[str]
) -> None:
    candidate, revision = selected
    workspace = tmp_path / "preparation"
    exit_code = main(
        [
            "--candidate",
            str(candidate),
            "--expected-revision",
            revision,
            "--workspace",
            str(workspace),
            "--tool-modules",
            str(MODULES),
            "--python-executable",
            sys.executable,
        ]
    )
    result = json.loads(capsys.readouterr().out)
    policy = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            (
                "from tools.automation.implementations.auto_migrate import "
                "_preflight_catalog; _preflight_catalog('v1_0720')"
            ),
        ],
        cwd=candidate,
        env={
            "PATH": "/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(candidate / "backend/src") + os.pathsep + str(candidate),
        },
        capture_output=True,
        check=False,
    )
    assert ("migration_operator_policy_not_admitted" in result["blockers"]) == bool(
        policy.returncode
    )
    assert exit_code == (3 if result["blockers"] else 0)
    assert result["status"] == (
        "prepared_activation_blocked" if result["blockers"] else "prepared"
    )
    assert result["revision"] == revision
    assert result["source_revision"] == "v1_0720"
    assert result["target_revision"] != result["source_revision"]
    assert set(result["blockers"]) <= {
        "migration_operator_policy_not_admitted",
        "cutover_source_policy_not_admitted",
    }
    assert json.loads((workspace / "preparation.json").read_text()) == result
    assert (workspace / "preparation.json").stat().st_mode & 0o777 == 0o600
    release = Path(result["release"])
    assert verify_candidate_release(
        release, workspace / "releases", revision, result["build_digest"]
    )
    assert not (release / "frontend/node_modules").exists()
    assert not (candidate / "frontend/node_modules").exists()
    for location, expected in (
        (workspace / "schema-rehearsal/agentmonitor.db", result["target_revision"]),
        (workspace / "schema-rehearsal/backup/agentmonitor.db", "v1_0720"),
    ):
        with sqlite3.connect(f"{location.as_uri()}?mode=ro", uri=True) as connection:
            assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
            assert connection.execute(
                "SELECT version_num FROM alembic_version"
            ).fetchone() == (expected,)
            assert connection.execute(
                "SELECT count(*) FROM reg_account"
            ).fetchone() == (0,)
        assert location.stat().st_mode & 0o777 == 0o600
    assert not list(workspace.rglob("*.env"))
    assert (
        subprocess.check_output(
            ["/usr/bin/git", "status", "--porcelain"], cwd=candidate
        )
        == b""
    )


def test_dirty_selected_checkout_refused_before_workspace(
    tmp_path: Path, selected: tuple[Path, str]
) -> None:
    candidate, revision = selected
    (candidate / "AGENTS.md").rename(candidate / "AGENTS.moved")
    workspace = tmp_path / "preparation"
    with pytest.raises(FrontendBuildError, match="frontend_source_not_clean"):
        prepare_setup_activation(
            candidate=candidate,
            expected_revision=revision,
            workspace=workspace,
            tool_modules=MODULES,
            python_executable=Path(sys.executable),
        )
    assert not workspace.exists()


def test_existing_workspace_refused_without_reading_database(
    tmp_path: Path, selected: tuple[Path, str]
) -> None:
    candidate, revision = selected
    workspace = tmp_path / "preparation"
    workspace.mkdir(mode=0o700)
    with pytest.raises(SetupPreparationError, match="m7_setup_workspace_exists"):
        prepare_setup_activation(
            candidate=candidate,
            expected_revision=revision,
            workspace=workspace,
            tool_modules=MODULES,
            python_executable=Path(sys.executable),
        )
    assert list(workspace.iterdir()) == []


def test_real_wrong_revision_and_symlink_selection_refused(
    tmp_path: Path, selected: tuple[Path, str]
) -> None:
    candidate, revision = selected
    parent_revision = subprocess.check_output(
        ["/usr/bin/git", "rev-parse", "HEAD^"], cwd=candidate, text=True
    ).strip()
    workspace = tmp_path / "preparation"
    with pytest.raises(SetupPreparationError, match="m7_setup_revision_mismatch"):
        prepare_setup_activation(
            candidate=candidate,
            expected_revision=parent_revision,
            workspace=workspace,
            tool_modules=MODULES,
            python_executable=Path(sys.executable),
        )
    alias = tmp_path / "alias"
    alias.symlink_to(candidate, target_is_directory=True)
    with pytest.raises(SetupPreparationError, match="m7_setup_selection_invalid"):
        prepare_setup_activation(
            candidate=alias,
            expected_revision=revision,
            workspace=workspace,
            tool_modules=MODULES,
            python_executable=Path(sys.executable),
        )
    assert not workspace.exists()

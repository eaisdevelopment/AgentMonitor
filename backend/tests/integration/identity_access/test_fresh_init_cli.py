"""ST-IAM-001: installed fresh-only migration command over real SQLite."""

import os
import stat
import subprocess
import sys
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    InspectSchemaCompatibilityV1,
    application_schema_range,
)

MODULE = "agentmonitor.composition.iam_fresh_init"
SOURCE = Path(__file__).resolve().parents[3] / "src"


def invoke(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", MODULE, "--data-root", str(root)],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(SOURCE)},
        timeout=20,
        check=False,
    )


def test_fresh_init_cli_migrates_absent_file_once_and_refuses_repeat(
    tmp_path: Path,
) -> None:
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    first = invoke(tmp_path)
    assert first.returncode == 0
    assert first.stdout == "schema_initialized\n"
    assert first.stderr == ""
    assert stat.S_IMODE(ref._path.stat().st_mode) == 0o600
    assert os.stat(ref._path).st_uid == os.getuid()
    state = InspectSchemaCompatibilityV1(
        ref, application_schema_range(), "runtime_read_write"
    )
    assert state.state == "compatible"
    before = ref._path.read_bytes()
    repeat = invoke(tmp_path)
    assert repeat.returncode == 2
    assert repeat.stdout == "database_already_exists\n"
    assert repeat.stderr == ""
    assert ref._path.read_bytes() == before


def test_fresh_init_cli_refuses_invalid_root_without_creating_file(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "not-created"
    rejected = invoke(missing)
    assert rejected.returncode == 2
    assert rejected.stdout == "schema_initialization_refused\n"
    assert rejected.stderr == ""
    assert not missing.exists()

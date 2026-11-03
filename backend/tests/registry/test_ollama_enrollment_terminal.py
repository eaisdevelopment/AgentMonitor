"""The real operator rejects unattended use before opening its data root."""

import subprocess
import sys
from pathlib import Path

import pytest

from agentmonitor.composition.ollama_credential_operator import main


def test_unattended_enrollment_rejected_without_opening_database(
    tmp_path: Path,
) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "agentmonitor.composition.ollama_credential_operator",
            "--data-root",
            str(tmp_path),
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 2
    assert result.stdout.strip() == "Open this command in a local terminal."
    assert not (tmp_path / "agentmonitor.db").exists()


def test_operator_help_exposes_explicit_existing_env_import_mode(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as stopped:
        main(["--help"])

    assert stopped.value.code == 0
    output = capsys.readouterr().out
    assert "--from-env-variable VARIABLE" in output
    assert "--account-id ID" in output

"""The real operator rejects unattended use before opening its data root."""

import subprocess
import sys
from pathlib import Path


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

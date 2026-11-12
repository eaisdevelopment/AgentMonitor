"""Real operator process refusal/help boundaries; no credential values."""

import subprocess
import sys
from pathlib import Path


def test_billing_operator_help_has_account_resource_selectors() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "agentmonitor.composition.billing_credential_operator",
            "--help",
        ],
        env={"PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")},
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, "billing owner-local operator is missing"
    assert "--account-id" in result.stdout
    assert "--resource-id" in result.stdout
    assert "--data-root" in result.stdout
    assert (
        "--action" in result.stdout
        and "disconnect" in result.stdout
        and "cleanup" in result.stdout
    )
    assert "--api-key" not in result.stdout


def test_billing_operator_refuses_unattended_use_before_opening_database(
    tmp_path: Path,
) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "agentmonitor.composition.billing_credential_operator",
            "--data-root",
            str(tmp_path),
            "--account-id",
            "selected-account",
            "--resource-id",
            "selected-resource",
        ],
        env={"PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")},
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 2, "billing operator must refuse non-terminal use"
    assert result.stdout.strip() == "Open this command in a local terminal."
    assert not (tmp_path / "agentmonitor.db").exists()

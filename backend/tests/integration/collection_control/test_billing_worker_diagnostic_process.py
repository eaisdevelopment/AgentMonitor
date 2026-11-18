"""Real worker authority and real unsafe-database refusal; no provider or doubles."""

import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)

# Pytest's import path is process-local. Pin this checkout for independent
# workers without inheriting arbitrary environment or credential configuration.
_WORKER_ENV = {
    "PYTHONPATH": str(Path(__file__).resolve().parents[3] / "src"),
    "PYTHONDONTWRITEBYTECODE": "1",
}


def test_authorized_worker_sanitizes_real_database_permission_failure(
    tmp_path: Path,
) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    # Actual isolated filesystem precondition violation, not seeded telemetry.
    database = tmp_path / "agentmonitor.db"
    database.chmod(0o644)
    authority = uuid.uuid4().hex
    try:
        with subprocess.Popen(
            [
                sys.executable,
                "-m",
                "agentmonitor.composition.billing_worker",
                "--data-root",
                str(tmp_path),
                "--recovery-only",
                "--start-authority",
                authority,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=_WORKER_ENV,
        ) as process:
            output, diagnostic = process.communicate(
                "START " + authority + "\n", timeout=20
            )
            exit_code, pid = process.returncode, process.pid
    finally:
        database.chmod(0o600)
    assert exit_code == 4
    assert output == ""
    if (
        re.fullmatch(
            r"BILLING_WORKER_FAILURE phase=(initialize|collect) "
            r"type=(BudgetCollectionError|SqlitePolicyError|ValueError|"
            r"CollectionRepositoryErrorV1) "
            r"source=backend/src/agentmonitor/[a-z_/]+\.py:[1-9][0-9]*\n",
            diagnostic,
        )
        is None
    ):
        pytest.fail("sanitized_worker_failure_diagnostic_missing", pytrace=False)
    assert str(tmp_path) not in diagnostic
    assert authority not in diagnostic
    assert "database_permissions_unsafe" not in diagnostic
    # Observe the actual child PID's journal, not another test's matching line.
    deadline = time.monotonic() + 3
    while True:
        journal = subprocess.run(
            [
                "/usr/bin/journalctl",
                f"_PID={pid}",
                "--since",
                "-1 minute",
                "--no-pager",
                "-o",
                "cat",
                "--grep",
                "^BILLING_WORKER_FAILURE ",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if (
            journal.returncode == 0
            and diagnostic.rstrip("\n") in journal.stdout.splitlines()
        ):
            break
        if time.monotonic() >= deadline:
            pytest.fail("sanitized_worker_journal_diagnostic_missing", pytrace=False)
        time.sleep(0.05)


def test_revoked_authority_keeps_existing_exit_and_no_diagnostic(
    tmp_path: Path,
) -> None:
    authority = uuid.uuid4().hex
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "agentmonitor.composition.billing_worker",
            "--data-root",
            str(tmp_path),
            "--recovery-only",
            "--start-authority",
            authority,
        ],
        input="",
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
        env=_WORKER_ENV,
    )
    assert result.returncode == 5
    assert result.stdout == result.stderr == ""
    assert not (tmp_path / "agentmonitor.db").exists()

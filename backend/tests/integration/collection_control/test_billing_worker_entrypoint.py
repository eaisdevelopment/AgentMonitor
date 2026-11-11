"""Actual billing CLI against empty migrated storage, without credentials."""

import subprocess
import sys
import uuid
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)


def test_recovery_only_empty_database_never_creates_reports(tmp_path: Path) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    token = uuid.uuid4().hex
    source = Path(__file__).resolve().parents[3] / "src"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "agentmonitor.composition.billing_worker",
            "--data-root",
            str(tmp_path),
            "--recovery-only",
            "--start-authority",
            token,
        ],
        input="START " + token + "\n",
        text=True,
        capture_output=True,
        timeout=20,
        env={
            "PATH": "/usr/bin:/bin",
            "PYTHONPATH": str(source),
            "PYTHONDONTWRITEBYTECODE": "1",
        },
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            for table in (
                "collection_run",
                "collection_scheduler_instance",
                "capacity_budget_report",
                "capacity_commit_receipt",
            ):
                assert (
                    connection.exec_driver_sql(
                        f"SELECT COUNT(*) FROM {table}"
                    ).scalar_one()
                    == 0
                )
            assert not connection.exec_driver_sql("PRAGMA foreign_key_check").all()

"""Preserve the real verification receipt across the v1_0718 migration."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    InspectSchemaCompatibilityV1,
    application_schema_range,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import ActiveCredentialBindingRefV1

ROOT = Path(__file__).resolve().parents[4]
_LIVE_DATABASE = Path("/home/dev/.local/share/agentmonitor/agentmonitor.db")


def _private_real_copy(tmp_path: Path) -> DatabaseRefV1:
    os.chmod(tmp_path, 0o700)
    copied = tmp_path / "agentmonitor.db"
    source = sqlite3.connect(f"file:{_LIVE_DATABASE}?mode=ro", uri=True)
    target = sqlite3.connect(copied)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    os.chmod(copied, 0o600)
    return DatabaseRefV1(copied, tmp_path)


def _current_receipts(reference: DatabaseRefV1) -> list[tuple[object, ...]]:
    with open_sqlite_database(reference, "runtime_read_only") as database:
        with database.connect() as connection:
            return connection.exec_driver_sql(
                "SELECT verification_id,account_id,binding_id,binding_generation,"
                "access_target_id,run_id,admission_id,source_id,adapter_version,"
                "manifest_fingerprint,payload_digest,verified_at,record_version "
                "FROM reg_credential_binding_verification ORDER BY verification_id"
            ).fetchall()


def test_real_v1_0717_receipt_survives_verified_v1_0718_upgrade(
    tmp_path: Path,
) -> None:
    """M6-A03/A04/A07/A09: preserve real current lineage, add empty history."""
    assert _LIVE_DATABASE.is_file()
    reference = _private_real_copy(tmp_path)
    with open_sqlite_database(reference, "runtime_read_only") as database:
        with database.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT version_num FROM alembic_version"
                ).scalar_one()
                == "v1_0717"
            )
    before = _current_receipts(reference)
    assert before

    environment = {
        "AGENTMONITOR_MIGRATE_DATA_ROOT": str(tmp_path),
        "AGENTMONITOR_MIGRATE_EXPECTED_HEAD": "v1_0717",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    result = subprocess.run(
        [sys.executable, "tools/automation/implementations/auto_migrate.py"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    view = InspectSchemaCompatibilityV1(
        reference, application_schema_range(), "runtime_read_write"
    )
    assert view.state == "compatible"
    assert view.current_revision == "v1_0718"
    if _current_receipts(reference) != before:
        pytest.fail("current_verification_receipt_changed")

    with open_sqlite_database(reference, "runtime_read_only") as database:
        with database.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM "
                    "reg_credential_binding_verification_history"
                ).scalar_one()
                == 0
            )
            assert (
                connection.exec_driver_sql("PRAGMA foreign_key_check").first() is None
            )
            assert (
                connection.exec_driver_sql("PRAGMA integrity_check").scalar_one()
                == "ok"
            )

    row = before[0]
    repository = SqliteCloudCredentialRegistryV1(reference)
    binding = ActiveCredentialBindingRefV1(
        account_id=OpaqueIdV1(str(row[1])),
        binding_id=OpaqueIdV1(str(row[2])),
        generation=int(row[3]),
    )
    current = repository.read_current_verification(binding)
    exact = repository.read_verification_by_run(
        OpaqueIdV1(str(row[5])), OpaqueIdV1(str(row[6]))
    )
    if current is None or exact != current:
        pytest.fail("exact_verification_receipt_lookup_changed")

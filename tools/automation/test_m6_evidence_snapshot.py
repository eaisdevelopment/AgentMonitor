"""Read-only real-state checks for the M6 completion snapshot."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from tools.automation.implementations.m6_real_snapshot import (
    M6EvidenceSnapshotV1,
    read_m6_evidence_snapshot_v1,
)

REAL_DATA_ROOT = Path("/home/dev/.local/share/agentmonitor")


def test_snapshot_contract_exposes_only_sanitized_aggregates() -> None:
    snapshot = M6EvidenceSnapshotV1.not_run(
        schema_state="upgrade_required",
        reason_code="m6_snapshot_schema_upgrade_required",
    )

    assert snapshot.as_json() == {
        "schema_version": "1.0.0",
        "record_type": "agentmonitor.m6_real_snapshot.v1",
        "status": "not_run",
        "reason_code": "m6_snapshot_schema_upgrade_required",
        "schema_state": "upgrade_required",
        "counts": {
            "active_ollama_accounts": 0,
            "registered_local_installations": 0,
            "observed_local_installations": 0,
            "active_cloud_targets": 0,
            "owner_confirmed_cloud_targets": 0,
            "owner_confirmed_required_scopes": 0,
            "verified_cloud_targets": 0,
            "current_balance_targets": 0,
            "history_targets": 0,
            "configured_alert_targets": 0,
            "alerted_targets": 0,
            "process_observation_count": 0,
            "natural_recovery_targets": 0,
            "cross_provider_continuity_targets": 0,
        },
        "digests": {
            "current_balance_lineage_sha256": hashlib.sha256(b"").hexdigest(),
            "current_history_lineage_sha256": hashlib.sha256(b"").hexdigest(),
        },
    }


def test_real_installed_database_is_inspected_without_mutation() -> None:
    before = (REAL_DATA_ROOT / "agentmonitor.db").stat()

    snapshot = read_m6_evidence_snapshot_v1(REAL_DATA_ROOT)

    after = (REAL_DATA_ROOT / "agentmonitor.db").stat()
    assert (after.st_dev, after.st_ino, after.st_size) == (
        before.st_dev,
        before.st_ino,
        before.st_size,
    )
    assert snapshot.status in {"passed", "blocked", "not_run"}
    assert snapshot.reason_code.startswith("m6_snapshot_")
    assert set(snapshot.as_json()) == {
        "schema_version",
        "record_type",
        "status",
        "reason_code",
        "schema_state",
        "counts",
        "digests",
    }
    assert set(snapshot.as_json()["counts"]) == {
        "active_ollama_accounts",
        "registered_local_installations",
        "observed_local_installations",
        "active_cloud_targets",
        "owner_confirmed_cloud_targets",
        "owner_confirmed_required_scopes",
        "verified_cloud_targets",
        "current_balance_targets",
        "history_targets",
        "configured_alert_targets",
        "alerted_targets",
        "process_observation_count",
        "natural_recovery_targets",
        "cross_provider_continuity_targets",
    }
    assert set(snapshot.as_json()["digests"]) == {
        "current_balance_lineage_sha256",
        "current_history_lineage_sha256",
    }
    assert all(
        isinstance(value, str) and len(value) == 64
        for value in snapshot.as_json()["digests"].values()
    )
    assert snapshot.natural_recovery_targets == 0
    assert snapshot.cross_provider_continuity_targets == 0


def test_real_snapshot_cli_emits_one_bounded_json_document() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.automation.implementations.m6_real_snapshot",
            "--data-root",
            str(REAL_DATA_ROOT),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )

    lines = result.stdout.splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["record_type"] == "agentmonitor.m6_real_snapshot.v1"
    assert payload["status"] in {"passed", "blocked", "not_run"}
    assert result.returncode == (0 if payload["status"] == "passed" else 3)

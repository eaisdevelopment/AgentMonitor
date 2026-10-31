"""Read-only proof that the real Claude identity claim has durable M06 evidence."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest


def _real_database_path() -> Path:
    value = os.environ.get("AGENTMONITOR_TEST_DATA_ROOT")
    if value is None:
        pytest.skip("NOT RUN: AGENTMONITOR_TEST_DATA_ROOT is not selected")
    root = Path(value)
    if not root.is_absolute():
        pytest.fail("AGENTMONITOR_TEST_DATA_ROOT must be absolute")
    database = root / "agentmonitor.db"
    if not database.is_file():
        pytest.fail("selected real AgentMonitor database is unavailable")
    return database


def _real_account_id() -> str:
    value = os.environ.get("AGENTMONITOR_TEST_ACCOUNT_ID")
    if value is None:
        pytest.skip("NOT RUN: AGENTMONITOR_TEST_ACCOUNT_ID is not selected")
    if not value or len(value) > 128:
        pytest.fail("AGENTMONITOR_TEST_ACCOUNT_ID is invalid")
    return value


def test_real_active_claude_identity_claim_resolves_to_committed_runtime_evidence() -> (
    None
):
    """M02-LIVE-011: current binding resolves to one exact durable M06 receipt."""

    database = _real_database_path()
    account_id = _real_account_id()
    connection = sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            "SELECT c.account_id, c.evidence_reference, "
            "d.account_id AS decision_account_id, d.evidence_set_digest, "
            "o.observation_id, o.source_id, o.source_version, o.parser_version, "
            "s.account_id AS session_account_id, s.correlation_state, "
            "r.payload_digest, r.mechanism_version, r.observation_ids_json "
            "FROM reg_provider_identity_claim AS c "
            "JOIN reg_identity_decision AS d ON d.claim_id=c.claim_id "
            "AND d.invalidated_at IS NULL "
            "LEFT JOIN runtime_session_observation AS o "
            "ON o.observation_id=c.evidence_reference "
            "LEFT JOIN runtime_session AS s ON s.session_id=o.session_id "
            "LEFT JOIN runtime_ingest_receipt AS r "
            "ON r.collection_run_id=o.collection_run_id "
            "AND r.source_id=o.source_id AND r.parser_version=o.parser_version "
            "WHERE c.provider_key='claude' "
            "AND c.identity_scheme='claude.otel.account.sha256' "
            "AND c.identity_scope='provider_account' "
            "AND c.account_id=? "
            "AND c.invalidated_at IS NULL",
            (account_id,),
        ).fetchall()
    finally:
        connection.close()

    assert len(rows) == 1, "expected exactly one active Claude identity claim"
    row = rows[0]
    assert row["observation_id"] is not None, (
        "active Claude identity evidence does not resolve to an M06 observation"
    )
    assert row["payload_digest"] is not None, (
        "active Claude identity evidence does not resolve to an M06 receipt"
    )
    assert row["evidence_reference"] == row["observation_id"]
    assert row["evidence_set_digest"] == row["payload_digest"]
    assert row["evidence_reference"] in json.loads(row["observation_ids_json"])
    assert row["source_id"] == "claude.otel.metrics.http-json.v1"
    assert row["source_version"] == "1.0.0"
    assert row["mechanism_version"] == row["source_version"]
    assert row["parser_version"] == "1.0.0"
    assert row["account_id"] == row["decision_account_id"]
    assert row["account_id"] == row["session_account_id"]
    assert row["correlation_state"] == "automatic_matched"

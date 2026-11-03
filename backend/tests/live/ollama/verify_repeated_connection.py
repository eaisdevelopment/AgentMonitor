"""Explicit live check: one genuine re-verification preserves the prior receipt.

Run only with an already authenticated dashboard browser and exactly one active
Ollama monitoring target. The normal service owns dispatch and rate admission.
No key, provider body or browser credential enters the test process or output.
"""

import subprocess
import time
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)

ROOT = Path(__file__).resolve().parents[4]
DATA = Path("/home/dev/.local/share/agentmonitor")


def test_actual_second_verification_preserves_previous_receipt() -> None:
    reference = DatabaseRefV1(DATA / "agentmonitor.db", DATA)
    registry = SqliteRegistryRepositoryV1(reference)
    cloud = SqliteCloudCredentialRegistryV1(reference)
    graphs = [
        cloud.read_monitoring_target(account.account_id)
        for account in registry.list_accounts("ollama", page_size=100)
        if account.lifecycle == "active" and account.is_effective_monitoring_enabled
    ]
    active = [graph for graph in graphs if graph and graph.lifecycle == "active"]
    if len(active) != 1:
        pytest.fail("exactly_one_active_ollama_target_required")
    graph = active[0]
    before = cloud.read_current_verification(graph.binding)
    if before is None:
        pytest.fail("existing_real_verification_required")
    request = subprocess.run(
        [
            "/usr/bin/node",
            "frontend/tests/browser/m6/request_reverification.mjs",
            graph.account_id.value,
        ],
        cwd=ROOT,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if request.returncode or request.stdout != b"connection_verification_enqueued\n":
        pytest.fail("real_connection_verification_enqueue_failed")
    deadline = time.monotonic() + 240
    while time.monotonic() < deadline:
        current = cloud.read_current_verification(graph.binding)
        if current is not None and current.verification_id != before.verification_id:
            if (
                current.verified_at <= before.verified_at
                or current.access_target_id != before.access_target_id
                or current.binding != before.binding
                or current.source_id != before.source_id
                or current.manifest_fingerprint != before.manifest_fingerprint
            ):
                pytest.fail("real_verification_supersession_lineage_invalid")
            if (
                cloud.read_verification_by_run(before.run_id, before.admission_id)
                != before
            ):
                pytest.fail("prior_verification_receipt_not_preserved")
            if (
                cloud.read_verification_by_run(current.run_id, current.admission_id)
                != current
            ):
                pytest.fail("new_verification_receipt_not_readable")
            if cloud.read_monitoring_target(graph.account_id) != graph:
                pytest.fail("reverification_changed_monitoring_target")
            return
        time.sleep(5)
    pytest.fail("real_reverification_not_completed_in_observation_interval")

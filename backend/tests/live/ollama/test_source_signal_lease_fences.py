"""Real private SQLite admission keeps independent lease sequences separate."""

from __future__ import annotations

import os
import sqlite3
import time
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.collection_control.sqlite import (
    ollama_cloud_admission,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.probe_descriptor import (
    ollama_cloud_probe_fingerprint,
    ollama_cloud_scheduled_policy,
)
from agentmonitor.composition.ollama_verification_run import build_scheduled_cloud_run
from agentmonitor.contracts.collection_control_v1 import (
    OllamaCloudLatestSourceSignalQueryV1,
    OllamaCloudRequestAcquireV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1

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


def _wait_for_actual_due_time(reference: DatabaseRefV1) -> None:
    with open_sqlite_database(reference, "runtime_read_only") as database:
        with database.connect() as connection:
            gate = (
                connection.exec_driver_sql(
                    "SELECT active_admission_id,next_allowed_at FROM "
                    "collection_ollama_cloud_gate"
                )
                .mappings()
                .one()
            )
            assert gate["active_admission_id"] is None
            due = connection.exec_driver_sql(
                "SELECT MIN(MAX(s.next_due_at,"
                "COALESCE(s.not_before_at,s.next_due_at))) "
                "FROM collection_schedule s JOIN collection_cloud_schedule_lane lane "
                "ON lane.schedule_id=s.schedule_id LEFT JOIN collection_lease l "
                "ON l.schedule_id=s.schedule_id WHERE s.provider_key='ollama' "
                "AND s.state='enabled' AND l.schedule_id IS NULL"
            ).scalar_one()
    assert due is not None
    deadline = max(
        datetime.fromisoformat(str(due)),
        datetime.fromisoformat(str(gate["next_allowed_at"])),
    )
    assert (deadline - datetime.now(UTC)).total_seconds() <= 330
    while (remaining := (deadline - datetime.now(UTC)).total_seconds()) > 0:
        time.sleep(min(remaining, 1))


def test_actual_cloud_and_collection_fences_are_independent(tmp_path: Path) -> None:
    """M6-A07/A09: exclude only the current reserved run using both real fences."""
    assert _LIVE_DATABASE.is_file()
    reference = _private_real_copy(tmp_path)
    registry = SqliteRegistryRepositoryV1(reference)
    cloud = SqliteCloudCredentialRegistryV1(reference)
    admissions = ollama_cloud_admission.SqliteOllamaCloudAdmissionRepositoryV1(
        reference
    )
    worker_id = OpaqueIdV1("ollama-fence-check-" + uuid4().hex)
    targets = []
    for account in registry.list_accounts(provider_key="ollama", page_size=100):
        graph = cloud.read_monitoring_target(account.account_id)
        if graph is None or not account.is_effective_monitoring_enabled:
            continue
        run = build_scheduled_cloud_run(
            graph,
            worker_id,
            account.registry_revision,
            ollama_cloud_probe_fingerprint(),
            datetime.now(UTC),
        )
        admissions.register_schedule(run)
        targets.append((account, graph))
    assert targets
    _wait_for_actual_due_time(reference)
    now = datetime.now(UTC)
    decision = admissions.acquire(
        OllamaCloudRequestAcquireV1(
            admission_id=OpaqueIdV1("ollama-fence-attempt-" + uuid4().hex),
            scheduler_instance_id=worker_id,
            requested_at=now,
            lease_expires_at=now + timedelta(seconds=60),
            jitter_seconds=0,
        )
    )
    lease = decision.lease
    assert lease is not None
    account, graph = next(
        item for item in targets if item[0].account_id == lease.account_id
    )
    policy = ollama_cloud_scheduled_policy()
    query = OllamaCloudLatestSourceSignalQueryV1(
        account_id=account.account_id,
        binding_generation=graph.binding.generation,
        access_target_id=graph.access_target_id,
        capability_id=policy.capability_id,
        source_id=policy.source_id,
        adapter_version=policy.adapter_version,
        source_fingerprint=policy.source_fingerprint,
        payload_schema=policy.payload_schema,
        queried_at=datetime.now(UTC),
    )
    prior = admissions.read_latest_source_signal(query)
    assert prior.run_id is not None
    run = build_scheduled_cloud_run(
        graph,
        worker_id,
        account.registry_revision,
        ollama_cloud_probe_fingerprint(),
        datetime.now(UTC),
    )
    runs = ollama_cloud_admission.SqliteOllamaCloudRunRepositoryV1(reference, lease)
    admitted = runs.admit_run(run)
    assert admitted.fencing_token != lease.fencing_token
    runs.mark_running(
        run.run_id, datetime.now(UTC), fencing_token=admitted.fencing_token
    )

    observed = admissions.read_latest_source_signal(
        replace(
            query,
            queried_at=datetime.now(UTC),
            exclude_active_lease=lease,
        )
    )

    assert observed.run_id == prior.run_id
    assert observed.admission_id == prior.admission_id
    assert observed.signal == prior.signal
    # A forged command is rejected by the independent global admission fence.
    with pytest.raises(
        ollama_cloud_admission.OllamaCloudAdmissionRepositoryErrorV1,
        match="ollama_cloud_fencing_conflict",
    ):
        admissions.read_latest_source_signal(
            replace(
                query,
                queried_at=datetime.now(UTC),
                exclude_active_lease=replace(
                    lease, fencing_token=lease.fencing_token + 1
                ),
            )
        )

"""Exercise current-policy admission after a real registry revision advances."""

from __future__ import annotations

import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.composition.ollama_installation_reconciliation import (
    reconcile_ollama_installation_v1,
)
from agentmonitor.composition.ollama_verification_run import (
    build_scheduled_cloud_run,
    cloud_schedule_target_digest,
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


def test_real_current_policy_admits_after_unrelated_registry_revision(
    tmp_path: Path,
) -> None:
    """M6-A07/A09: registry freshness is a run fence, not policy identity."""
    assert _LIVE_DATABASE.is_file()
    reference = _private_real_copy(tmp_path)
    registry = SqliteRegistryRepositoryV1(reference)
    cloud = SqliteCloudCredentialRegistryV1(reference)
    accounts = registry.list_accounts(provider_key="ollama", page_size=100)
    candidates = []
    for account in accounts:
        graph = cloud.read_monitoring_target(account.account_id)
        if graph is None:
            continue
        digest = cloud_schedule_target_digest(graph)
        schedule_id = "ollama-cloud-" + digest[:40]
        with open_sqlite_database(reference, "runtime_read_only") as database:
            with database.connect() as connection:
                prior = (
                    connection.exec_driver_sql(
                        "SELECT registry_revision,source_id,manifest_fingerprint,"
                        "collection_policy_version,target_generation FROM "
                        "collection_run WHERE schedule_id=? ORDER BY "
                        "target_generation DESC,attempt_ordinal DESC LIMIT 1",
                        (schedule_id,),
                    )
                    .mappings()
                    .one_or_none()
                )
                instance = connection.exec_driver_sql(
                    "SELECT instance_id FROM collection_scheduler_instance "
                    "ORDER BY heartbeat_at DESC,instance_id DESC LIMIT 1"
                ).scalar_one_or_none()
                active = connection.exec_driver_sql(
                    "SELECT 1 FROM collection_lease WHERE schedule_id=? LIMIT 1",
                    (schedule_id,),
                ).first()
        if (
            prior is not None
            and instance is not None
            and active is None
        ):
            candidates.append((account, graph, prior, str(instance)))
    assert candidates
    account, graph, prior, instance = candidates[0]
    reconcile_ollama_installation_v1(reference)
    current = registry.get_account(account.account_id)
    assert current is not None
    assert current.registry_revision > account.registry_revision
    run = build_scheduled_cloud_run(
        graph,
        OpaqueIdV1(instance),
        current.registry_revision,
        str(prior["manifest_fingerprint"]),
        datetime.now(UTC),
    )
    assert run.source_id == prior["source_id"]
    assert run.collection_policy_version == prior["collection_policy_version"]
    assert run.target_generation == int(prior["target_generation"])
    assert run.registry_revision != int(prior["registry_revision"])

    admitted = SqliteCollectionRepositoryV1(reference).admit_run(run)

    assert admitted.run_id == run.run_id
    assert admitted.state == "queued"

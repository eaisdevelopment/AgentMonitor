"""Actual empty SQLite manual usage queue boundaries without provider records."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.collection_control.sqlite import (
    ollama_cloud_admission as cloud_admission,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.budget import (
    BudgetCollectionError,
)
from agentmonitor.composition.ollama_usage_fence import cloud_usage_fence
from agentmonitor.composition.ollama_usage_run import (
    POLICY_VERSION,
    usage_budget_limit,
    usage_manifest_fingerprint,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


@pytest.mark.parametrize("range_key", ["7d", "30d"])
def test_empty_usage_claim_does_not_reserve_global_gate(
    tmp_path: Path, range_key: str
) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    gate = cloud_admission.SqliteOllamaCloudAdmissionRepositoryV1(reference)
    assert (
        gate.claim_next_usage_run(
            scheduler_instance_id=OpaqueIdV1("empty-usage-worker"),
            as_of=datetime.now(UTC),
            resolve_budget_limit=usage_budget_limit,
            manifest_fingerprint=usage_manifest_fingerprint(),
            collection_policy_version=POLICY_VERSION,
            operation_family="collect.ollama.usage." + range_key,
            cloud_admission_fence=cloud_usage_fence,
            jitter_seconds=0,
        )
        is None
    )
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            for table in (
                "collection_run",
                "collection_lease",
                "collection_scheduler_instance",
                "collection_ollama_cloud_gate",
                "collection_ollama_cloud_admission",
                "collection_cloud_attempt_journal",
            ):
                assert (
                    connection.exec_driver_sql(
                        f"SELECT count(*) FROM {table}"
                    ).scalar_one()
                    == 0
                )


def test_empty_usage_status_read_creates_no_gate(tmp_path: Path) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    gate = cloud_admission.SqliteOllamaCloudAdmissionRepositoryV1(reference)
    assert gate.read_usage_gate_status(datetime.now(UTC)) == ("ready", None)
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM collection_ollama_cloud_gate"
                ).scalar_one()
                == 0
            )


@pytest.mark.parametrize("jitter", [-1, 11, True])
def test_usage_claim_invalid_jitter_rejected_before_storage(
    tmp_path: Path, jitter: int
) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    gate = cloud_admission.SqliteOllamaCloudAdmissionRepositoryV1(reference)
    with pytest.raises(
        cloud_admission.OllamaCloudAdmissionRepositoryErrorV1,
        match="ollama_cloud_admission_query_invalid",
    ):
        gate.claim_next_usage_run(
            scheduler_instance_id=OpaqueIdV1("invalid-usage-worker"),
            as_of=datetime.now(UTC),
            resolve_budget_limit=usage_budget_limit,
            manifest_fingerprint=usage_manifest_fingerprint(),
            collection_policy_version=POLICY_VERSION,
            operation_family="collect.ollama.usage.7d",
            cloud_admission_fence=cloud_usage_fence,
            jitter_seconds=jitter,
        )
    assert not (tmp_path / "agentmonitor.db").exists()


def test_usage_claim_requires_real_authority_fence_before_storage(
    tmp_path: Path,
) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    gate = cloud_admission.SqliteOllamaCloudAdmissionRepositoryV1(reference)
    with pytest.raises(BudgetCollectionError, match="budget_admission_fence_required"):
        gate.claim_next_usage_run(
            scheduler_instance_id=OpaqueIdV1("invalid-usage-worker"),
            as_of=datetime.now(UTC),
            resolve_budget_limit=usage_budget_limit,
            manifest_fingerprint=usage_manifest_fingerprint(),
            collection_policy_version=POLICY_VERSION,
            operation_family="collect.ollama.usage.7d",
            cloud_admission_fence=None,
            jitter_seconds=0,
        )
    assert not (tmp_path / "agentmonitor.db").exists()

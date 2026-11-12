"""Real SQLite dispatch metadata reads; no provider observations are seeded."""

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
from agentmonitor.adapters.persistence.collection_control.sqlite.budget import (
    BudgetCollectionError,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.composition.ollama_usage_fence import cloud_usage_fence
from agentmonitor.composition.ollama_usage_run import (
    POLICY_VERSION,
    usage_budget_limit,
    usage_manifest_fingerprint,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def test_empty_dispatch_snapshot_is_consistent_and_read_only(tmp_path: Path) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    repository = SqliteCollectionRepositoryV1(reference)
    result = repository.read_budget_dispatch_snapshot(
        provider_key="ollama",
        capability_id="api.usage",
        source_id="ollama.cloud.usage.v1",
        manifest_fingerprint=usage_manifest_fingerprint(),
        collection_policy_version=POLICY_VERSION,
        operation_families=("collect.ollama.usage.7d", "collect.ollama.usage.30d"),
        budget_scope_digests=("a" * 64,),
        schedule_ids=(OpaqueIdV1("absent-schedule"),),
        as_of=datetime.now(UTC),
    )
    assert result.states == ()
    assert result.schedules == ()
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            for table in ("collection_run", "collection_schedule", "collection_lease"):
                assert (
                    connection.exec_driver_sql(
                        f"SELECT count(*) FROM {table}"
                    ).scalar_one()
                    == 0
                )


@pytest.mark.parametrize("digests", [("invalid",), ("a" * 64,) * 4097])
def test_snapshot_rejects_invalid_bounds_before_storage(
    tmp_path: Path, digests: tuple[str, ...]
) -> None:
    repository = SqliteCollectionRepositoryV1(
        DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    )
    with pytest.raises(BudgetCollectionError, match="budget_dispatch_query_invalid"):
        repository.read_budget_dispatch_snapshot(
            provider_key="ollama",
            capability_id="api.usage",
            source_id="ollama.cloud.usage.v1",
            manifest_fingerprint=usage_manifest_fingerprint(),
            collection_policy_version=POLICY_VERSION,
            operation_families=("collect.ollama.usage.7d",),
            budget_scope_digests=digests,
            schedule_ids=(),
            as_of=datetime.now(UTC),
        )
    assert not (tmp_path / "agentmonitor.db").exists()


def test_exact_absent_run_claim_does_not_select_other_work(tmp_path: Path) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    repository = SqliteCollectionRepositoryV1(
        reference, cloud_admission_fence=cloud_usage_fence
    )
    assert (
        repository.claim_next_budget_run(
            scheduler_instance_id=OpaqueIdV1("empty-worker"),
            as_of=datetime.now(UTC),
            resolve_budget_limit=usage_budget_limit,
            provider_key="ollama",
            capability_id="api.usage",
            source_id="ollama.cloud.usage.v1",
            manifest_fingerprint=usage_manifest_fingerprint(),
            collection_policy_version=POLICY_VERSION,
            operation_family="collect.ollama.usage.7d",
            expected_run_id=OpaqueIdV1("absent-run"),
        )
        is None
    )

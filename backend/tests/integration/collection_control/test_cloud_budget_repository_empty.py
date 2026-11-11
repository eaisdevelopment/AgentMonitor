"""Real empty SQLite cloud queries and recovery; no provider records are seeded."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.budget import (
    BudgetCollectionError,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.contracts.collection_control_v1 import CloudBudgetReportContextV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.collection_control.application.budget_executor import (
    ExecuteBudgetCollectionRunV1,
)


def test_empty_store_has_no_captured_cloud_authority(tmp_path: Path) -> None:
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    repository = SqliteCollectionRepositoryV1(ref, cloud_admission_fence=None)
    with pytest.raises(BudgetCollectionError, match="budget_run_not_found"):
        repository.get_budget_target(OpaqueIdV1("absent-run"))


@pytest.mark.parametrize("scope", ["self", "team"])
@pytest.mark.parametrize("days", [7, 30])
def test_empty_latest_cloud_context_and_recovery_create_no_rows(
    tmp_path: Path, scope: str, days: int
) -> None:
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    repository = SqliteCollectionRepositoryV1(ref)
    now = datetime.now(UTC)
    end = now.replace(hour=0, minute=0, second=0, microsecond=0)
    context = CloudBudgetReportContextV1(
        scope=scope,  # type: ignore[arg-type]
        range_key="7d" if days == 7 else "30d",
        interval_start=end - timedelta(days=days),
        interval_end=end,
    )
    assert (
        repository.get_latest_budget_run(
            OpaqueIdV1("absent-account"),
            OpaqueIdV1("absent-resource"),
            1,
            now,
            report_context=context,
        )
        is None
    )
    executor = ExecuteBudgetCollectionRunV1(
        repository, SqliteBudgetReportRepositoryV1(ref)
    )
    arguments = dict(
        provider_key="ollama",
        capability_id="api.usage",
        source_id="ollama.cloud.usage.v1",
        as_of=now,
        owner_stale_before=now - timedelta(seconds=120),
        recovery_instance_id=OpaqueIdV1("absent-recovery-owner"),
        recovery_lease_expires_at=now + timedelta(seconds=30),
        maximum_runs=16,
    )
    assert executor.recover_pending_commits(**arguments) == ()  # type: ignore[arg-type]
    assert executor.recover_expired_runs(**arguments) == ()  # type: ignore[arg-type]
    with open_sqlite_database(ref, "runtime_read_only") as handle:
        with handle.connect() as connection:
            for table in (
                "collection_run",
                "collection_budget_run",
                "collection_lease",
                "collection_budget_reservation",
                "collection_scheduler_instance",
                "capacity_commit_receipt",
            ):
                assert (
                    connection.exec_driver_sql(
                        f"SELECT count(*) FROM {table}"
                    ).scalar_one()
                    == 0
                )
            assert not connection.exec_driver_sql("PRAGMA foreign_key_check").all()

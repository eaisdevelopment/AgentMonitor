"""Real empty M04 store denies authority; no fabricated active target is admitted."""

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
    require_budget_run_lease,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def test_empty_store_has_no_captured_billing_authority(tmp_path: Path) -> None:
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    repository = SqliteCollectionRepositoryV1(ref)
    with pytest.raises(BudgetCollectionError, match="budget_run_not_found"):
        repository.get_billing_target(OpaqueIdV1("absent-run"))
    with open_sqlite_database(ref, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            with pytest.raises(
                BudgetCollectionError, match="budget_run_fencing_conflict"
            ):
                require_budget_run_lease(
                    connection,
                    OpaqueIdV1("absent-run"),
                    scheduler_instance_id=OpaqueIdV1("absent-scheduler"),
                    fencing_token=1,
                    as_of=datetime.now(UTC),
                )
            assert (
                connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM collection_run"
                ).scalar_one()
                == 0
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM collection_budget_run"
                ).scalar_one()
                == 0
            )
            assert not connection.exec_driver_sql("PRAGMA foreign_key_check").all()


def test_finalization_requires_a_typed_receipt_before_database_open(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agentmonitor.db"
    repository = SqliteCollectionRepositoryV1(DatabaseRefV1(path, tmp_path))
    with pytest.raises(BudgetCollectionError, match="budget_receipt_required"):
        repository.finalize_budget_committed(
            None,  # type: ignore[arg-type]
            terminal_state="succeeded",
            completed_at=datetime.now(UTC),
            fencing_token=1,
            scheduler_instance_id=OpaqueIdV1("absent-scheduler"),
        )
    assert not path.exists()


def test_empty_recovery_uses_real_m04_m05_ports_without_source_or_receipts(
    tmp_path: Path,
) -> None:
    from datetime import timedelta

    from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
        SqliteBudgetReportRepositoryV1,
    )
    from agentmonitor.modules.collection_control.application.budget_executor import (
        ExecuteBudgetCollectionRunV1,
    )

    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    executor = ExecuteBudgetCollectionRunV1(
        SqliteCollectionRepositoryV1(ref), SqliteBudgetReportRepositoryV1(ref)
    )
    now = datetime.now(UTC)
    assert (
        executor.recover_pending_commits(
            provider_key="claude",
            capability_id="api.billing",
            source_id="anthropic.api.cost.v1",
            as_of=now,
            owner_stale_before=now,
            recovery_instance_id=OpaqueIdV1("empty-recovery-owner"),
            recovery_lease_expires_at=now + timedelta(seconds=30),
            maximum_runs=16,
        )
        == ()
    )
    with open_sqlite_database(ref, "runtime_read_only") as handle:
        with handle.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM collection_scheduler_instance"
                ).scalar_one()
                == 0
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM capacity_commit_receipt"
                ).scalar_one()
                == 0
            )

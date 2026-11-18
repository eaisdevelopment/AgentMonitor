"""M04 retention checks over genuine copied receipts and real SQLite integrity."""

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
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.budget import (
    BudgetCollectionError,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.contracts.collection_control_v1 import (
    BudgetCollectionReceiptV1,
    BudgetCollectionRunViewV1,
)
from sqlalchemy.engine import Connection

from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)


@pytest.fixture(scope="module")
def retained(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[DatabaseRefV1, tuple[BudgetCollectionReceiptV1, ...]]:
    reference = _private_real_copy(tmp_path_factory.mktemp("m04-budget-retention"))
    from backend.tests.persistence.sqlite.migrations.test_m05_model_remainder import (
        migrate_revision,
    )

    migrate_revision(reference, "v1_0736", "migration_existing")
    runs = SqliteCollectionRepositoryV1(reference)
    reports = SqliteBudgetReportRepositoryV1(reference)
    receipts: list[BudgetCollectionReceiptV1] = []
    cursor = None
    now = datetime.now(UTC)
    for _ in range(20):
        page = runs.list_runs(None, None, now, 500, cursor)
        for run in page:
            if (
                not isinstance(run, BudgetCollectionRunViewV1)
                or run.state not in {"succeeded", "partial"}
                or run.report_id is None
            ):
                continue
            status = reports.get_commit_status(run.run_id, run.capability_id)
            if status.receipt is not None and status.receipt.fact_ids:
                receipts.append(status.receipt)
                if len(receipts) == 2:
                    return reference, tuple(receipts)
        if len(page) < 500:
            break
        cursor = page[-1].run_id.value
    pytest.fail("genuine_finalized_budget_receipts_required", pytrace=False)


def _guard(
    connection: Connection, receipts: tuple[BudgetCollectionReceiptV1, ...]
) -> None:
    from agentmonitor.adapters.persistence.collection_control.sqlite.budget_retention_guard import (  # noqa: E501
        ensure_budget_retention_safe_in_transaction,
    )

    ensure_budget_retention_safe_in_transaction(connection, receipts)


def test_genuine_terminal_receipts_are_safe_without_mutation(
    retained: tuple[DatabaseRefV1, tuple[BudgetCollectionReceiptV1, ...]],
) -> None:
    reference, receipts = retained
    repository = SqliteBudgetReportRepositoryV1(reference)
    before = tuple(
        repository.get_commit_status(receipt.run_id, receipt.capability_id)
        for receipt in receipts
    )
    with open_sqlite_database(reference, "runtime_read_write") as database:
        with database.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            changes = connection.exec_driver_sql("SELECT total_changes()").scalar_one()
            _guard(connection, receipts)
            assert connection.in_transaction()
            assert (
                connection.exec_driver_sql("SELECT total_changes()").scalar_one()
                == changes
            )
            connection.rollback()
    after = tuple(
        repository.get_commit_status(receipt.run_id, receipt.capability_id)
        for receipt in receipts
    )
    if before != after:
        pytest.fail("budget_retention_guard_changed_receipts", pytrace=False)


def test_guard_requires_real_transaction_and_bounded_distinct_receipts(
    retained: tuple[DatabaseRefV1, tuple[BudgetCollectionReceiptV1, ...]],
) -> None:
    reference, receipts = retained
    with open_sqlite_database(reference, "runtime_read_write") as database:
        with database.connect() as connection:
            connection.rollback()
            with pytest.raises(
                BudgetCollectionError, match="^budget_retention_transaction_required$"
            ):
                _guard(connection, receipts)
            # SQLAlchemy autobegin alone does not hold a SQLite transaction.
            connection.exec_driver_sql("SELECT 1")
            with pytest.raises(
                BudgetCollectionError, match="^budget_retention_transaction_required$"
            ):
                _guard(connection, receipts)
            connection.rollback()
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            for invalid in ((), (receipts[0], receipts[0]), receipts * 101):
                with pytest.raises(
                    BudgetCollectionError, match="^budget_retention_request_invalid$"
                ):
                    _guard(connection, invalid)
            connection.rollback()


def test_genuine_receipts_refused_by_real_empty_database(
    retained: tuple[DatabaseRefV1, tuple[BudgetCollectionReceiptV1, ...]],
    tmp_path: Path,
) -> None:
    _, receipts = retained
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    with open_sqlite_database(reference, "runtime_read_write") as database:
        with database.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            with pytest.raises(
                BudgetCollectionError, match="^budget_retention_run_unsafe$"
            ):
                _guard(connection, receipts)
            assert (
                connection.exec_driver_sql("SELECT total_changes()").scalar_one() == 0
            )
            connection.rollback()


@pytest.mark.parametrize("remove", ["budget_link", "fact_link"])
def test_genuine_link_removal_is_refused_and_rollback_restores_safety(
    retained: tuple[DatabaseRefV1, tuple[BudgetCollectionReceiptV1, ...]],
    remove: str,
) -> None:
    reference, receipts = retained
    receipt = receipts[0]
    with open_sqlite_database(reference, "runtime_read_write") as database:
        with database.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            if remove == "budget_link":
                removed = connection.exec_driver_sql(
                    "DELETE FROM collection_budget_run WHERE run_id=?",
                    (receipt.run_id.value,),
                )
                code = "budget_retention_run_unsafe"
            else:
                removed = connection.exec_driver_sql(
                    "DELETE FROM collection_run_observation_ref "
                    "WHERE run_id=? AND observation_id=?",
                    (receipt.run_id.value, receipt.fact_ids[0].value),
                )
                code = "budget_retention_references_unsafe"
            assert removed.rowcount == 1
            changes = connection.exec_driver_sql("SELECT total_changes()").scalar_one()
            with pytest.raises(BudgetCollectionError, match=f"^{code}$"):
                _guard(connection, receipts)
            assert (
                connection.exec_driver_sql("SELECT total_changes()").scalar_one()
                == changes
            )
            connection.rollback()
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            _guard(connection, receipts)
            connection.rollback()

"""Real empty SQLite boundary; no financial reports or substitute fence are seeded."""

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
    BudgetRepositoryError,
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.contracts.capacity_v1 import (
    BudgetPeriodV1,
    BudgetReportHistoryQueryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def test_empty_database_queries_do_not_invent_reports_or_receipts(
    tmp_path: Path,
) -> None:
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    repo = SqliteBudgetReportRepositoryV1(ref)
    account = OpaqueIdV1("absent-account")
    assert repo.get_report(account, OpaqueIdV1("absent-report")) is None
    assert (
        repo.get_commit_status(OpaqueIdV1("absent-run"), "api.billing").state
        == "not_committed"
    )
    query = BudgetReportHistoryQueryV1(
        account,
        OpaqueIdV1("absent-resource"),
        BudgetPeriodV1(
            datetime(2026, 11, 1, tzinfo=UTC), datetime(2026, 11, 8, tzinfo=UTC)
        ),
    )
    page = repo.list_reports(query)
    assert page.items == ()
    assert page.has_more is False
    assert page.next_key is None
    assert page.availability.state == "available"
    with open_sqlite_database(ref, "runtime_read_only") as handle:
        with handle.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM capacity_budget_report"
                ).scalar_one()
                == 0
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM capacity_commit_receipt"
                ).scalar_one()
                == 0
            )


def test_missing_fence_refuses_before_creating_database(tmp_path: Path) -> None:
    path = tmp_path / "agentmonitor.db"
    repo = SqliteBudgetReportRepositoryV1(DatabaseRefV1(path, tmp_path))
    with pytest.raises(
        BudgetRepositoryError, match="budget_transaction_fence_required"
    ):
        repo.commit(None)  # type: ignore[arg-type]  # No report or I/O can reach admission.
    assert not path.exists()


def test_invalid_cursor_is_rejected_before_database_open(tmp_path: Path) -> None:
    path = tmp_path / "agentmonitor.db"
    repo = SqliteBudgetReportRepositoryV1(DatabaseRefV1(path, tmp_path))
    query = BudgetReportHistoryQueryV1(
        OpaqueIdV1("absent-account"),
        OpaqueIdV1("absent-resource"),
        BudgetPeriodV1(
            datetime(2026, 11, 1, tzinfo=UTC), datetime(2026, 11, 8, tzinfo=UTC)
        ),
        after_key="not-a-cursor",
    )
    with pytest.raises(BudgetRepositoryError, match="budget_history_cursor_invalid"):
        repo.list_reports(query)
    assert not path.exists()

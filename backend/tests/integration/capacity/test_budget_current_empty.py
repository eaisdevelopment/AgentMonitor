"""Real empty current-query boundary; no constructed financial report is persisted."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

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
from agentmonitor.contracts.capacity_v1 import (
    BudgetCurrentQueryV1,
    BudgetCurrentReportsPortV1,
    BudgetPeriodV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def test_empty_current_query_is_unavailable_and_creates_no_reports(
    tmp_path: Path,
) -> None:
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    repository: BudgetCurrentReportsPortV1 = SqliteBudgetReportRepositoryV1(ref)
    now = datetime.now(UTC)
    query = BudgetCurrentQueryV1(
        OpaqueIdV1("absent-account"),
        OpaqueIdV1("absent-resource"),
        1,
        BudgetPeriodV1(now - timedelta(days=7), now),
        now,
    )
    result = repository.get_current_reports(query)
    assert result.items == ()
    assert result.availability.state == "unavailable"
    assert result.availability.reason_code == "budget_current_reports_absent"
    assert result.availability.as_of == now
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
            assert not connection.exec_driver_sql("PRAGMA foreign_key_check").all()


def test_missing_database_is_query_unavailable_without_creating_storage(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agentmonitor.db"
    repository = SqliteBudgetReportRepositoryV1(DatabaseRefV1(path, tmp_path))
    now = datetime.now(UTC)
    query = BudgetCurrentQueryV1(
        OpaqueIdV1("absent-account"),
        OpaqueIdV1("absent-resource"),
        1,
        BudgetPeriodV1(now - timedelta(days=7), now),
        now,
    )
    result = repository.get_current_reports(query)
    assert result.items == ()
    assert result.availability.state == "unavailable"
    assert result.availability.reason_code == "budget_current_query_unavailable"
    assert not path.exists()

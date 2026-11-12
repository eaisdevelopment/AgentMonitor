"""Real migrated empty SQLite; no fabricated provider authority or telemetry."""

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
from agentmonitor.adapters.persistence.collection_control.sqlite.budget import (
    BudgetCollectionError,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.contracts.collection_control_v1 import BillingBudgetReportContextV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1


@pytest.mark.parametrize("days", [7, 30])
@pytest.mark.parametrize("grouping", [(), ("project",)])
def test_empty_billing_context_lookup_is_read_only(
    tmp_path: Path,
    days: int,
    grouping: tuple[str, ...],
) -> None:
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    runs = SqliteCollectionRepositoryV1(ref)
    now = datetime.now(UTC)
    end = now.replace(hour=0, minute=0, second=0, microsecond=0)
    context = BillingBudgetReportContextV1(
        "7d" if days == 7 else "30d",
        end - timedelta(days=days),
        end,
        "cost",
        grouping,
    )
    for selection in (None, context):
        assert (
            runs.get_latest_budget_run(
                OpaqueIdV1("absent-account"),
                OpaqueIdV1("absent-resource"),
                2,
                now,
                report_context=selection,
            )
            is None
        )
    with pytest.raises(BudgetCollectionError, match="budget_run_not_found"):
        runs.get_billing_target(OpaqueIdV1("absent-run"))
    with open_sqlite_database(ref, "runtime_read_only") as handle:
        with handle.connect() as connection:
            for table in (
                "collection_run",
                "collection_budget_run",
                "collection_lease",
                "collection_budget_reservation",
                "collection_request",
            ):
                assert (
                    connection.exec_driver_sql(
                        f"SELECT count(*) FROM {table}"
                    ).scalar_one()
                    == 0
                )
            assert (
                connection.exec_driver_sql("PRAGMA integrity_check").scalar_one()
                == "ok"
            )

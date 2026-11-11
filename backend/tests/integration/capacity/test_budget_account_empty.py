"""Actual account query with empty migrated storage, no financial fixtures."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
    SqliteBillingConnectionRepositoryV1,
)
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def test_absent_account_does_not_become_an_empty_financial_account(
    tmp_path: Path,
) -> None:
    from agentmonitor.modules.capacity.application.budget_queries import (
        GetAccountBudgetCurrentV1,
    )

    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    query = GetAccountBudgetCurrentV1(
        SqliteBillingConnectionRepositoryV1(ref),
        SqliteBudgetReportRepositoryV1(ref),
        SqliteCollectionRepositoryV1(ref),
    )
    now = datetime.now(UTC)
    assert (
        query(
            OpaqueIdV1("not-enrolled"),
            period=BudgetPeriodV1(now - timedelta(days=7), now),
            as_of=now,
        )
        is None
    )

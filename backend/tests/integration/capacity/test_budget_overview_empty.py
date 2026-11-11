"""Actual migrated empty SQLite Overview query, without financial fixtures."""

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
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.contracts.budget_query_v1 import BudgetOverviewQueryV1
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1
from agentmonitor.modules.capacity.application.budget_queries import (
    GetAccountBudgetCurrentV1,
)
from agentmonitor.modules.registry.application.accounts import (
    ListAccountResourcesV1,
    ListAccountsV1,
)


def test_empty_real_overview_has_no_rows_totals_or_subscription_ids(
    tmp_path: Path,
) -> None:
    from agentmonitor.modules.capacity.application.budget_overview import (
        ListBudgetOverviewV1,
    )

    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    registry = SqliteRegistryRepositoryV1(reference)
    overview = ListBudgetOverviewV1(
        ListAccountsV1(registry),
        GetAccountBudgetCurrentV1(
            SqliteBillingConnectionRepositoryV1(reference),
            SqliteBudgetReportRepositoryV1(reference),
            SqliteCollectionRepositoryV1(reference),
        ),
        ListAccountResourcesV1(registry),
    )
    now = datetime.now(UTC)
    end = now.replace(hour=0, minute=0, second=0, microsecond=0)
    result = overview(
        BudgetOverviewQueryV1(BudgetPeriodV1(end - timedelta(days=7), end), now)
    )
    assert result.page.availability.state == "available"
    assert result.page.items == () and result.summaries == ()
    assert result.subscription_account_ids == () and result.inventory_count == 0
    assert result.page.next_key is None

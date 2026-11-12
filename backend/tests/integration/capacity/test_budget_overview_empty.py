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


def test_real_primary_group_resolves_pool_outside_account_group(tmp_path: Path) -> None:
    """Owner metadata only: no report fixtures and no invented zero spending."""
    from agentmonitor.adapters.persistence.registry.sqlite.financial_pools import (
        SqliteFinancialPoolRepositoryV1,
    )
    from agentmonitor.modules.capacity.application.budget_overview import (
        ListBudgetOverviewV1,
    )

    from backend.tests.integration.registry.test_financial_pools import (
        _assign,
        _organization,
        _source,
    )

    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    primary = _organization(reference)
    first, first_resource = _source(reference)
    second, second_resource = _source(reference)
    pools = SqliteFinancialPoolRepositoryV1(reference)
    created = pools.assign(
        _assign(pools, first, first_resource, org=primary.organization_id)
    )
    assert created.pool is not None
    pools.assign(
        _assign(
            pools, second, second_resource, action="join", pool_id=created.pool.pool_id
        )
    )
    registry = SqliteRegistryRepositoryV1(reference)
    overview = ListBudgetOverviewV1(
        ListAccountsV1(registry),
        GetAccountBudgetCurrentV1(
            SqliteBillingConnectionRepositoryV1(reference),
            SqliteBudgetReportRepositoryV1(reference),
            SqliteCollectionRepositoryV1(reference),
        ),
        ListAccountResourcesV1(registry),
        financial_pools=pools,
    )
    now = datetime.now(UTC)
    end = now.replace(hour=0, minute=0, second=0, microsecond=0)
    result = overview(
        BudgetOverviewQueryV1(
            BudgetPeriodV1(end - timedelta(days=7), end),
            now,
            organization_ids=(primary.organization_id,),
        )
    )
    assert result.page.availability.state == "available"
    assert len(result.page.items) == 1
    row = result.page.items[0]
    assert row.pool_id == created.pool.pool_id
    assert row.primary_organization_id == primary.organization_id
    assert len(row.access_paths) == 2
    assert {path.account.account_id for path in row.access_paths} == {
        first.account_id,
        second.account_id,
    }
    assert row.contexts == () and result.summaries == ()
    assert row.counted_in_selection is True
    assert result.inventory_count == 2
    # The same shared row is visible from its secondary, ungrouped access paths.
    from dataclasses import replace

    secondary = overview(
        replace(
            BudgetOverviewQueryV1(BudgetPeriodV1(end - timedelta(days=7), end), now),
            organization_ids=(),
            include_ungrouped=True,
        )
    )
    assert secondary.page.availability.state == "available"
    assert len(secondary.page.items) == 1
    assert secondary.page.items[0].counted_in_selection is False
    assert secondary.summaries == () and secondary.exclusions == ()

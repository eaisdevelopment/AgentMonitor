"""Measure actual Overview reads on a private copy of genuine registry/history."""

import cProfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
    SqliteBillingConnectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.financial_pools import (
    SqliteFinancialPoolRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.contracts.budget_query_v1 import BudgetOverviewQueryV1
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1
from agentmonitor.modules.capacity.application.budget_overview import (
    ListBudgetOverviewV1,
)
from agentmonitor.modules.capacity.application.budget_queries import (
    GetAccountBudgetCurrentV1,
)
from agentmonitor.modules.capacity.domain.budget_overview import project_budget_rows
from agentmonitor.modules.registry.application.accounts import (
    ListAccountResourcesV1,
    ListAccountsV1,
)
from agentmonitor.modules.registry.application.organizations import GetOrganizationV1

from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)


def test_subscription_only_inventory_does_not_open_financial_current_queries(
    tmp_path: Path,
) -> None:
    reference = _private_real_copy(tmp_path)
    registry = SqliteRegistryRepositoryV1(reference)
    accounts = ListAccountsV1(registry)
    resources = ListAccountResourcesV1(registry)
    current = GetAccountBudgetCurrentV1(
        SqliteBillingConnectionRepositoryV1(reference),
        SqliteBudgetReportRepositoryV1(reference),
        SqliteCollectionRepositoryV1(reference),
    )
    overview = ListBudgetOverviewV1(
        accounts,
        current,
        resources,
        SqliteFinancialPoolRepositoryV1(reference),
        GetOrganizationV1(registry),
    )
    now = datetime.now(UTC)
    end = now.replace(hour=0, minute=0, second=0, microsecond=0)
    query = BudgetOverviewQueryV1(BudgetPeriodV1(end - timedelta(days=30), end), now)
    inventory = accounts.page(None, as_of=now, limit=200)
    assert not inventory.has_more, "genuine_inventory_exceeds_comparison_bound"
    active = tuple(a for a in inventory.items if a.lifecycle != "archived")
    subscriptions = []
    for account in active:
        registered = resources(account.account_id)
        if (
            account.provider_key in {"claude", "codex"}
            and account.initial_connection_purpose is None
            and len(registered) < 100
            and any(r.lifecycle == "active" for r in registered)
            and all(r.kind == "subscription_pool" for r in registered)
        ):
            detail = current(account.account_id, period=query.period, as_of=now)
            if project_budget_rows(account, registered, detail, query) != ():
                raise AssertionError("subscription_has_financial_rows")
            if project_budget_rows(account, registered, None, query) != ():
                raise AssertionError("subscription_omission_changes_financial_rows")
            subscriptions.append(account.account_id)
    assert subscriptions, "genuine_subscription_inventory_required"
    profile = cProfile.Profile()
    with profile:
        result = overview(query)
    assert result.page.availability.state == "available"
    assert result.inventory_count == len(active)
    assert set(subscriptions).issubset(result.subscription_account_ids)
    calls = sum(
        item.callcount
        for item in profile.getstats()
        if item.code == GetAccountBudgetCurrentV1.__call__.__code__
    )
    expected_calls = len(active) - len(subscriptions)
    assert calls == expected_calls, (
        "subscription_only_financial_queries_are_unnecessary"
    )


def test_account_read_publishes_actual_subscription_resource_presence(
    tmp_path: Path,
) -> None:
    reference = _private_real_copy(tmp_path)
    registry = SqliteRegistryRepositoryV1(reference)
    accounts = registry.list_accounts(page_size=200)
    assert accounts, "genuine_registry_required"
    positives = 0
    for account in accounts:
        resources = registry.list_account_resources(account.account_id)
        assert len(resources) < 100, "resource_comparison_requires_complete_list"
        expected = any(
            r.kind == "subscription_pool" and r.lifecycle == "active" for r in resources
        )
        assert getattr(account, "has_active_subscription_resource", None) is expected
        selected = registry.get_account(account.account_id)
        assert selected is not None
        assert getattr(selected, "has_active_subscription_resource", None) is expected
        positives += expected
    assert positives > 0, "genuine_subscription_resource_required"

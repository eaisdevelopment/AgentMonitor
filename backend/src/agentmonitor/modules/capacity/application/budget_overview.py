"""Full-inventory financial Overview through published query ports only."""

from dataclasses import replace

from agentmonitor.contracts.budget_query_v1 import (
    AccountBudgetCurrentPortV1,
    AccountBudgetCurrentV1,
    BudgetAccountInventoryPortV1,
    BudgetOverviewQueryV1,
    BudgetOverviewResultV1,
    BudgetOverviewRowV1,
)
from agentmonitor.contracts.common_v1 import QueryAvailabilityV1, QueryPageV1
from agentmonitor.contracts.registry_billing_v1 import FinancialPoolReadPortV1
from agentmonitor.contracts.registry_v1 import AccountViewV1, ListAccountResourcesV1
from agentmonitor.modules.capacity.domain.budget_overview import (
    BudgetOverviewError,
    account_matches,
    append_inventory_page,
    has_subscription,
    overview_result,
    project_budget_rows,
)
from agentmonitor.modules.capacity.domain.budget_pool_overview import (
    resolve_overview_pools,
)


class ListBudgetOverviewV1:
    def __init__(
        self,
        accounts: BudgetAccountInventoryPortV1,
        current: AccountBudgetCurrentPortV1,
        resources: ListAccountResourcesV1,
        financial_pools: FinancialPoolReadPortV1 | None = None,
    ) -> None:
        self._accounts = accounts
        self._current = current
        self._resources = resources
        self._financial_pools = financial_pools

    def _inventory(self, query: BudgetOverviewQueryV1) -> tuple[AccountViewV1, ...]:
        inventory: tuple[AccountViewV1, ...] = ()
        cursor = None
        seen = set()
        while True:
            page = self._accounts.page(
                query.provider_key, as_of=query.as_of, limit=200, after_key=cursor
            )
            inventory = append_inventory_page(inventory, page, query.as_of)
            if not page.has_more:
                return inventory
            if page.next_key in seen:
                raise BudgetOverviewError("budget_overview_inventory_invalid")
            seen.add(page.next_key)
            cursor = page.next_key

    def __call__(self, query: BudgetOverviewQueryV1) -> BudgetOverviewResultV1:
        try:
            inventory = self._inventory(query)
            revision = inventory[0].registry_revision if inventory else 0
            selected = tuple(a for a in inventory if account_matches(a, query))
            full_query = replace(query, organization_ids=None, include_ungrouped=False)
            authorized = tuple(a for a in inventory if account_matches(a, full_query))
            currents: list[AccountBudgetCurrentV1] = []
            rows: list[BudgetOverviewRowV1] = []
            subscriptions = []
            snapshots = {}
            for account in authorized:
                resources = self._resources(account.account_id)
                if any(r.registry_revision != revision for r in resources):
                    raise BudgetOverviewError("budget_overview_registry_changed")
                snapshots[account.account_id] = resources
                current = self._current(
                    account.account_id, period=query.period, as_of=query.as_of
                )
                if account_matches(account, query) and has_subscription(
                    account,
                    resources,
                    has_cloud_resources=current is not None
                    and bool(
                        current.cloud_resources
                        or current.funds is not None
                        and current.funds.components
                    ),
                ):
                    subscriptions.append(account.account_id)
                # Billing connection revisions describe their last mutation;
                # inventory/resources/funds carry the global read revision.
                if (
                    current is not None
                    and current.funds is not None
                    and current.funds.components
                    and current.funds.registry_revision != revision
                ):
                    raise BudgetOverviewError("budget_overview_registry_changed")
                if current is not None:
                    currents.append(current)
                rows.extend(
                    project_budget_rows(account, resources, current, full_query)
                )
            resource_ids = tuple(
                sorted(
                    {
                        r.connection.resource_id
                        for current in currents
                        for r in current.resources
                    }
                    | {
                        r.target.resource_id
                        for current in currents
                        for r in current.cloud_resources
                    },
                    key=lambda value: value.value,
                )
            )
            pool_snapshot = None
            projection = None
            if self._financial_pools is not None and resource_ids:
                pool_snapshot = self._financial_pools(
                    resource_ids,
                    expected_registry_revision=revision,
                    as_of=query.as_of,
                )
                if (
                    pool_snapshot.availability.state != "available"
                    or pool_snapshot.registry_revision != revision
                    or pool_snapshot.as_of != query.as_of
                    or pool_snapshot.resource_ids != resource_ids
                ):
                    raise BudgetOverviewError("budget_overview_registry_changed")
                projection = resolve_overview_pools(
                    tuple(rows),
                    tuple(currents),
                    pool_snapshot,
                    query,
                )
            if self._inventory(query) != inventory:
                raise BudgetOverviewError("budget_overview_registry_changed")
            if any(
                self._resources(account_id) != resources
                for account_id, resources in snapshots.items()
            ):
                raise BudgetOverviewError("budget_overview_registry_changed")
            if pool_snapshot is not None and self._financial_pools is not None:
                if (
                    self._financial_pools(
                        resource_ids,
                        expected_registry_revision=revision,
                        as_of=query.as_of,
                    )
                    != pool_snapshot
                ):
                    raise BudgetOverviewError("budget_overview_registry_changed")
            return overview_result(
                projection.rows
                if projection is not None
                else tuple(row for row in rows if account_matches(row.account, query)),
                query,
                registry_revision=revision,
                inventory_count=len(
                    {account.account_id for account in selected}
                    | {
                        path.account.account_id
                        for row in (projection.rows if projection else ())
                        for path in row.access_paths
                    }
                ),
                summaries=projection.summaries if projection is not None else (),
                exclusions=projection.exclusions if projection is not None else None,
                summary_reason=projection.summary_reason
                if projection is not None
                else None,
                subscription_account_ids=tuple(
                    sorted(subscriptions, key=lambda i: i.value)
                ),
            )
        except ValueError as error:
            reason = (
                str(error)
                if isinstance(error, BudgetOverviewError)
                else "budget_overview_query_unavailable"
            )
            return BudgetOverviewResultV1(
                query.period,
                query.as_of,
                QueryPageV1(
                    (),
                    query.limit,
                    False,
                    None,
                    QueryAvailabilityV1("unavailable", reason, query.as_of),
                ),
                (),
                (),
                reason,
                0,
                0,
                (),
            )

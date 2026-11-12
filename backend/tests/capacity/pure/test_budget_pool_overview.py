"""Pure M7 pool attribution; constructed DTOs never cross an I/O boundary."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from agentmonitor.contracts.budget_query_v1 import (
    AccountBudgetCurrentV1,
    BudgetCloudResourceCurrentV1,
    BudgetOverviewQueryV1,
    BudgetOverviewRowV1,
    BudgetResourceCurrentV1,
)
from agentmonitor.contracts.capacity_v1 import BudgetReportSelectionV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1, QueryAvailabilityV1
from agentmonitor.contracts.registry_billing_v1 import (
    BillingConnectionViewV1,
    FinancialPoolMembershipV1,
    FinancialPoolSnapshotV1,
    FinancialPoolViewV1,
    FinancialResourceScopeV1,
)
from agentmonitor.modules.capacity.domain.budget_overview import project_budget_rows

from backend.tests.capacity.pure.test_budget_aggregation import PERIOD, _input
from backend.tests.capacity.pure.test_budget_overview import _account, _resource

if TYPE_CHECKING:
    from agentmonitor.modules.capacity.domain.budget_pool_overview import (
        BudgetPoolOverview,
    )

NOW = PERIOD.end + timedelta(days=2)
PRIMARY, SECONDARY = OpaqueIdV1("primary"), OpaqueIdV1("secondary")
QUERY = BudgetOverviewQueryV1(PERIOD, NOW)
AVAILABLE = QueryAvailabilityV1("available", "pure_read", NOW)


def _entry(
    name: str,
    org: OpaqueIdV1,
    amount: str | None = "8",
    *,
    hour: int = 1,
    currency: str = "USD",
) -> tuple[BudgetOverviewRowV1, AccountBudgetCurrentV1]:
    item = _input(name, amount, pool="shared", hour=hour, currency=currency)
    report = item.selection.current
    assert report is not None and report.report.subject.account_id is not None
    account = replace(
        _account(),
        account_id=report.report.subject.account_id,
        friendly_name=name,
        organization_id=org,
        created_at=NOW,
        updated_at=NOW,
    )
    connection = BillingConnectionViewV1(
        account.account_id,
        item.resource_id,
        "claude",
        "scope-shared",
        "provider_verified",
        1,
        "enabled",
        "active",
        1,
        1,
        NOW,
        NOW,
    )
    current = AccountBudgetCurrentV1(
        account.account_id,
        PERIOD,
        NOW,
        AVAILABLE,
        (
            BudgetResourceCurrentV1(
                connection, (item.selection,), AVAILABLE, (), None, AVAILABLE
            ),
        ),
    )
    resource = replace(_resource(resource_id=name), account_id=account.account_id)
    row = project_budget_rows(account, (resource,), current, QUERY)[0]
    return row, current


def _changed(
    entry: tuple[BudgetOverviewRowV1, AccountBudgetCurrentV1],
    selection: BudgetReportSelectionV1,
) -> tuple[BudgetOverviewRowV1, AccountBudgetCurrentV1]:
    row, current = entry
    current = replace(
        current, resources=(replace(current.resources[0], reports=(selection,)),)
    )
    assert row.resource_id is not None
    resource = replace(
        _resource(resource_id=row.resource_id.value), account_id=row.account.account_id
    )
    return project_budget_rows(row.account, (resource,), current, QUERY)[0], current


def _snapshot(
    *entries: tuple[BudgetOverviewRowV1, AccountBudgetCurrentV1],
) -> FinancialPoolSnapshotV1:
    pool = FinancialPoolViewV1(
        OpaqueIdV1("shared"),
        "claude",
        PRIMARY,
        1,
        1,
        NOW,
        NOW,
        "Shared pool",
        "billing",
    )
    members = []
    ids = []
    for row, current in entries:
        assert row.resource_id is not None
        ids.append(row.resource_id)
        connection = current.resources[0].connection
        selected = next(
            (s.current or s.latest_attempt for s in current.resources[0].reports), None
        )
        unresolved = connection.scope_evidence == "unresolved"
        members.append(
            FinancialPoolMembershipV1(
                OpaqueIdV1("association-" + row.resource_id.value),
                FinancialResourceScopeV1(
                    row.account.account_id,
                    row.resource_id,
                    "claude",
                    "billing",
                    connection.scope_generation,
                    connection.scope_id,
                    connection.scope_evidence,
                    selected.report.binding_id if unresolved and selected else None,
                    selected.report.binding_generation
                    if unresolved and selected
                    else None,
                ),
                pool.pool_id,
                "owner_asserted",
                NOW,
                None,
                1,
                1,
            )
        )
    return FinancialPoolSnapshotV1(
        tuple(ids), (pool,), tuple(members), 1, NOW, AVAILABLE
    )


def _resolve(
    entries: tuple[tuple[BudgetOverviewRowV1, AccountBudgetCurrentV1], ...],
    *,
    query: BudgetOverviewQueryV1 = QUERY,
    snapshot: FinancialPoolSnapshotV1 | None = None,
) -> "BudgetPoolOverview":
    from agentmonitor.modules.capacity.domain.budget_pool_overview import (
        resolve_overview_pools,
    )

    return resolve_overview_pools(
        tuple(e[0] for e in entries),
        tuple(e[1] for e in entries),
        snapshot if snapshot is not None else _snapshot(*entries),
        query,
    )


@pytest.mark.parametrize(
    "organizations,counted",
    [((PRIMARY,), True), ((SECONDARY,), False), ((PRIMARY, SECONDARY), True)],
)
def test_primary_attribution_uses_all_access_paths_before_filtering(
    organizations: tuple[OpaqueIdV1, ...], counted: bool
) -> None:
    entries = (_entry("first", PRIMARY, "8"), _entry("second", SECONDARY, "6", hour=2))
    result = _resolve(entries, query=replace(QUERY, organization_ids=organizations))
    assert len(result.rows) == 1
    row = result.rows[0]
    assert row.pool_id == OpaqueIdV1("shared")
    assert row.primary_organization_id == PRIMARY
    assert row.counted_in_selection is counted
    assert len(row.access_paths) == 2
    assert len(row.contexts) == 1
    context = row.contexts[0]
    assert context.report_id == entries[1][0].contexts[0].report_id
    assert context.report_account_id == entries[1][0].account.account_id
    assert context.report_resource_id == entries[1][0].resource_id
    assert context.collected_at == entries[1][0].contexts[0].collected_at
    assert context.spend is not None and context.spend.amount.as_decimal() == Decimal(
        "6"
    )
    assert result.exclusions == ()
    if counted:
        assert {s.scope_kind for s in result.summaries} == {"global", "organization"}
        assert all(
            s.total.amount.as_decimal() == Decimal("6") for s in result.summaries
        )
        assert all(s.included_pool_count == 1 for s in result.summaries)
    else:
        assert result.summaries == ()


def test_missing_primary_report_uses_secondary_and_keeps_failed_path_visible() -> None:
    first = _changed(_entry("first", PRIMARY), BudgetReportSelectionV1(None, None))
    first = (
        replace(
            first[0],
            state_code="collection_failed",
            state_rank=1,
            collection_error="source_unavailable",
        ),
        first[1],
    )
    second = _entry("second", SECONDARY, "6")
    result = _resolve(
        (first, second), query=replace(QUERY, organization_ids=(PRIMARY,))
    )
    assert len(result.rows) == 1 and result.rows[0].state_code == "collection_failed"
    assert any(
        p.collection_error == "source_unavailable" for p in result.rows[0].access_paths
    )
    assert result.rows[0].contexts[0].report_account_id == second[0].account.account_id
    assert result.summaries and all(
        s.total.amount.as_decimal() == Decimal("6") for s in result.summaries
    )


def test_unassociated_resources_remain_separate_and_do_not_become_totals() -> None:
    entries = (_entry("first", PRIMARY), _entry("second", SECONDARY))
    snapshot = replace(_snapshot(*entries), pools=(), memberships=())
    result = _resolve(entries, snapshot=snapshot)
    assert len(result.rows) == 2 and result.summaries == ()
    assert all(row.pool_id is None for row in result.rows)
    assert result.exclusions[0].reason_code == "unresolved_overlap"
    assert result.exclusions[0].count == 2


def test_changed_scope_epoch_cannot_reuse_pool_association() -> None:
    entries = (_entry("first", PRIMARY),)
    snapshot = _snapshot(*entries)
    member = snapshot.memberships[0]
    snapshot = replace(
        snapshot,
        memberships=(replace(member, scope=replace(member.scope, scope_generation=2)),),
    )
    result = _resolve(entries, snapshot=snapshot)
    assert result.rows[0].pool_id is None and result.summaries == ()


def test_conflicting_upstream_target_preserves_evidence_but_has_no_pool_total() -> None:
    first, second = _entry("first", PRIMARY), _entry("second", SECONDARY)
    report = second[1].resources[0].reports[0].current
    assert report is not None
    report = replace(
        report,
        report=replace(
            report.report,
            subject=replace(
                report.report.subject,
                provider_target=replace(
                    report.report.subject.provider_target,
                    target_id=OpaqueIdV1("amat_" + "b" * 32),
                ),
            ),
        ),
    )
    second = _changed(second, BudgetReportSelectionV1(report, report))
    result = _resolve((first, second))
    assert len(result.rows) == 1 and result.summaries == ()
    assert any(e.reason_code == "incompatible_pool_reports" for e in result.exclusions)
    assert len(result.rows[0].contexts) == 2
    assert all(c.spend is None for c in result.rows[0].contexts)


@pytest.mark.parametrize("case", ["missing", "partial", "counts"])
def test_unavailable_pool_coverage_is_not_zero(case: str) -> None:
    entry = _entry("first", PRIMARY)
    report = entry[1].resources[0].reports[0].current
    assert report is not None
    if case == "missing":
        selection = BudgetReportSelectionV1(None, None)
    elif case == "partial":
        partial = replace(
            report,
            report=replace(
                report.report,
                completeness="partial",
                omission_codes=("missing_page",),
                empty_means_zero=False,
            ),
        )
        selection = BudgetReportSelectionV1(None, partial)
    else:
        counts = replace(
            report,
            report=replace(
                report.report, currency=None, cost_buckets=(), empty_means_zero=False
            ),
        )
        selection = BudgetReportSelectionV1(counts, counts)
    result = _resolve((_changed(entry, selection),))
    assert result.summaries == () and result.summary_reason is not None
    assert len(result.rows) == 1
    assert all(c.spend is None for c in result.rows[0].contexts)


def test_totals_ignore_row_page_limit() -> None:
    entries = (_entry("first", PRIMARY, "0.1"), _entry("second", PRIMARY, "0.2"))
    snapshot = _snapshot(*entries)
    other = replace(
        snapshot.pools[0], pool_id=OpaqueIdV1("other"), display_name="Other pool"
    )
    snapshot = replace(
        snapshot,
        pools=(*snapshot.pools, other),
        memberships=(
            snapshot.memberships[0],
            replace(snapshot.memberships[1], pool_id=other.pool_id),
        ),
    )
    full = _resolve(entries, snapshot=snapshot)
    bounded = _resolve(entries, snapshot=snapshot, query=replace(QUERY, limit=1))
    assert len(bounded.rows) == 2
    assert bounded.summaries == full.summaries
    assert all(s.total.amount.as_decimal() == Decimal("0.3") for s in bounded.summaries)


def _unresolved(
    entry: tuple[BudgetOverviewRowV1, AccountBudgetCurrentV1],
) -> tuple[BudgetOverviewRowV1, AccountBudgetCurrentV1]:
    row, current = entry
    resource = current.resources[0]
    view = resource.reports[0].current
    assert view is not None
    current = replace(
        current,
        resources=(
            replace(
                resource,
                connection=replace(
                    resource.connection, scope_id=None, scope_evidence="unresolved"
                ),
            ),
        ),
    )
    view = replace(
        view, report=replace(view.report, scope_id=None, scope_evidence="unresolved")
    )
    return _changed((row, current), BudgetReportSelectionV1(view, view))


def test_unresolved_association_before_first_report_keeps_metadata_without_money() -> (
    None
):
    entry = _unresolved(_entry("first", PRIMARY))
    snapshot = _snapshot(entry)
    entry = _changed(entry, BudgetReportSelectionV1(None, None))
    result = _resolve((entry,), snapshot=snapshot)
    assert result.rows[0].pool_id == snapshot.pools[0].pool_id
    assert len(result.rows[0].access_paths) == 1
    assert result.rows[0].contexts == () and result.summaries == ()
    assert result.exclusions[0].reason_code == "missing_report"


@pytest.mark.parametrize("changed", ["id", "generation", "evidence"])
def test_unresolved_pool_requires_exact_report_lineage(changed: str) -> None:
    entry = _unresolved(_entry("first", PRIMARY))
    snapshot = _snapshot(entry)
    member = snapshot.memberships[0]
    scope = member.scope
    if changed == "id":
        scope = replace(scope, binding_id=OpaqueIdV1("different-binding"))
    elif changed == "generation":
        scope = replace(scope, binding_generation=2)
    else:
        scope = replace(
            scope,
            provider_scope_id="different-financial-scope",
            scope_evidence="owner_asserted",
            binding_id=None,
            binding_generation=None,
        )
    snapshot = replace(snapshot, memberships=(replace(member, scope=scope),))
    result = _resolve((entry,), snapshot=snapshot)
    assert result.rows[0].pool_id is None and result.summaries == ()
    assert result.exclusions[0].reason_code == "unresolved_overlap"


def test_verified_scope_allows_rotated_credential_without_changing_money_identity() -> (
    None
):
    first = _entry("first", PRIMARY)
    second = _entry("second", SECONDARY, "6", hour=2)
    view = second[1].resources[0].reports[0].current
    assert view is not None
    view = replace(
        view,
        report=replace(
            view.report, binding_id=OpaqueIdV1("rotated-binding"), binding_generation=9
        ),
    )
    second = _changed(second, BudgetReportSelectionV1(view, view))
    result = _resolve((first, second))
    assert len(result.rows) == 1
    assert all(s.total.amount.as_decimal() == Decimal("6") for s in result.summaries)


def test_conflicting_source_ids_cannot_be_counted_as_same_pool() -> None:
    first, second = _entry("first", PRIMARY), _entry("second", SECONDARY)
    view = second[1].resources[0].reports[0].current
    assert view is not None
    view = replace(view, report=replace(view.report, source_id="different-source"))
    second = _changed(second, BudgetReportSelectionV1(view, view))
    result = _resolve((first, second))
    assert result.summaries == ()
    assert all(c.spend is None for c in result.rows[0].contexts)
    assert result.exclusions[0].reason_code == "incompatible_pool_reports"


def test_later_overflow_is_included_in_every_summary_coverage_count() -> None:
    entries = (
        _entry("a-eur", PRIMARY, "1", currency="EUR"),
        _entry("b-usd", PRIMARY, "9" * 78),
        _entry("c-usd", PRIMARY, "9" * 78),
    )
    original = _snapshot(*entries)
    pools = tuple(
        replace(original.pools[0], pool_id=OpaqueIdV1(str(i))) for i in range(3)
    )
    snapshot = replace(
        original,
        pools=pools,
        memberships=tuple(
            replace(member, pool_id=pool.pool_id)
            for member, pool in zip(original.memberships, pools, strict=True)
        ),
    )
    result = _resolve(entries, snapshot=snapshot)
    assert result.summaries and all(s.currency == "EUR" for s in result.summaries)
    assert all(s.excluded_resource_count == 2 for s in result.summaries)
    assert result.exclusions[0].reason_code == "cost_total_unavailable"
    assert result.exclusions[0].count == 2


def test_pool_chooses_one_whole_funds_source_with_its_lineage() -> None:
    from backend.tests.capacity.pure.test_budget_overview import _funds_current

    account, resource, current = _funds_current()
    fund = project_budget_rows(
        account,
        (resource,),
        current,
        BudgetOverviewQueryV1(current.period, current.as_of),
    )[0].funds[0]
    first, second = _entry("first", PRIMARY), _entry("second", SECONDARY)
    earlier = replace(
        fund,
        component_id=OpaqueIdV1("first-included"),
        collected_at=NOW - timedelta(hours=1),
    )
    newer = replace(fund, component_id=OpaqueIdV1("second-included"), collected_at=NOW)
    first = (
        replace(
            first[0],
            funds=(
                earlier,
                replace(
                    earlier,
                    component_id=OpaqueIdV1("first-purchased"),
                    kind="purchased_credits",
                ),
            ),
        ),
        first[1],
    )
    second = (
        replace(
            second[0],
            funds=(
                newer,
                replace(
                    newer,
                    component_id=OpaqueIdV1("second-purchased"),
                    kind="purchased_credits",
                ),
            ),
        ),
        second[1],
    )
    result = _resolve((first, second))
    funds = result.rows[0].funds
    assert tuple(f.component_id.value for f in funds) == (
        "second-included",
        "second-purchased",
    )
    assert all(
        f.source_account_id == second[0].account.account_id
        and f.source_resource_id == second[0].resource_id
        for f in funds
    )
    assert all(f.remaining == fund.remaining and f.limit == fund.limit for f in funds)


@pytest.mark.parametrize(
    "source_category,associated",
    [("self_requests_and_cost", True), ("team_requests_and_cost", False)],
)
def test_cloud_membership_is_self_only_and_counts_do_not_become_money(
    source_category: str, associated: bool
) -> None:
    from backend.tests.contracts.test_cloud_budget_run_contract import _graph

    graph = _graph()
    account = replace(
        _account(),
        account_id=graph.account_id,
        provider_key="ollama",
        organization_id=PRIMARY,
    )
    view = _input("cloud", "1").selection.current
    assert view is not None
    view = replace(
        view,
        report=replace(
            view.report,
            subject=replace(
                view.report.subject,
                account_id=graph.account_id,
                resource_id=graph.resource_id,
                provider_key="ollama",
            ),
            binding_id=graph.binding.binding_id,
            binding_generation=graph.binding.generation,
            scope_id=None,
            scope_evidence="unresolved",
            source_id="ollama.cloud.usage.v1",
            source_category=source_category,
            currency=None,
            cost_buckets=(),
            empty_means_zero=False,
        ),
    )
    selection = BudgetReportSelectionV1(view, view)
    current = AccountBudgetCurrentV1(
        account.account_id,
        PERIOD,
        NOW,
        AVAILABLE,
        (),
        cloud_resources=(
            BudgetCloudResourceCurrentV1(
                graph, (selection,), AVAILABLE, (), None, AVAILABLE
            ),
        ),
    )
    row = project_budget_rows(account, (), current, QUERY)[0]
    pool = FinancialPoolViewV1(
        OpaqueIdV1("cloud-pool"),
        "ollama",
        PRIMARY,
        1,
        1,
        NOW,
        NOW,
        "Cloud pool",
        "self",
    )
    scope = FinancialResourceScopeV1(
        account.account_id,
        graph.resource_id,
        "ollama",
        "self",
        1,
        None,
        "unresolved",
        graph.binding.binding_id,
        graph.binding.generation,
    )
    membership = FinancialPoolMembershipV1(
        OpaqueIdV1("cloud-association"),
        scope,
        pool.pool_id,
        "owner_asserted",
        NOW - timedelta(days=1),
        None,
        1,
        1,
    )
    snapshot = FinancialPoolSnapshotV1(
        (graph.resource_id,), (pool,), (membership,), 1, NOW, AVAILABLE
    )
    result = _resolve(((row, current),), snapshot=snapshot)
    assert result.rows[0].pool_id == (pool.pool_id if associated else None)
    assert result.summaries == ()
    assert all(context.spend is None for context in result.rows[0].contexts)
    assert result.exclusions[0].reason_code == (
        "currency_unavailable" if associated else "unresolved_overlap"
    )


@pytest.mark.parametrize("boundary", ["currency", "basis", "category"])
def test_context_boundaries_remain_separate_within_one_pool(boundary: str) -> None:
    first, second = (
        _entry("first", PRIMARY, "2"),
        _entry(
            "second",
            SECONDARY,
            "3",
            currency="EUR" if boundary == "currency" else "USD",
        ),
    )
    view = second[1].resources[0].reports[0].current
    assert view is not None
    if boundary == "basis":
        view = replace(view, report=replace(view.report, cost_basis="net_of_credits"))
    elif boundary == "category":
        view = replace(view, report=replace(view.report, source_category="other_costs"))
    second = _changed(second, BudgetReportSelectionV1(view, view))
    result = _resolve((first, second))
    assert len(result.rows) == 1 and len(result.rows[0].contexts) == 2
    totals = [summary for summary in result.summaries if summary.scope_kind == "global"]
    assert len(totals) == 2
    assert {s.total.amount.as_decimal() for s in totals} == {Decimal("2"), Decimal("3")}
    assert result.exclusions == ()

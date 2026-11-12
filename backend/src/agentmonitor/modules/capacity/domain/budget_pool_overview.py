"""Apply explicit pool attribution to complete Overview inventory, without I/O."""

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass, replace

from agentmonitor.contracts.budget_query_v1 import (
    AccountBudgetCurrentV1,
    BudgetCloudResourceCurrentV1,
    BudgetOverviewAccessPathV1,
    BudgetOverviewContextV1,
    BudgetOverviewExclusionV1,
    BudgetOverviewQueryV1,
    BudgetOverviewRowV1,
    BudgetOverviewSummaryV1,
    BudgetResourceCurrentV1,
)
from agentmonitor.contracts.capacity_v1 import (
    BudgetReportSelectionV1,
    BudgetReportViewV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import (
    FinancialPoolMembershipV1,
    FinancialPoolSnapshotV1,
    FinancialPoolViewV1,
)
from agentmonitor.modules.capacity.domain.budget_account_spend import reported_spend
from agentmonitor.modules.capacity.domain.budget_aggregation import (
    BudgetSpendInput,
    aggregate_budget_spend,
)
from agentmonitor.modules.capacity.domain.budget_money import BudgetMoneyError
from agentmonitor.modules.capacity.domain.budget_overview import (
    BudgetOverviewError,
    account_matches,
)

type Resource = BudgetResourceCurrentV1 | BudgetCloudResourceCurrentV1
type GroupKey = tuple[str | None, str, str]


@dataclass(frozen=True, slots=True)
class BudgetPoolOverview:
    rows: tuple[BudgetOverviewRowV1, ...]
    summaries: tuple[BudgetOverviewSummaryV1, ...]
    exclusions: tuple[BudgetOverviewExclusionV1, ...]
    summary_reason: str | None


@dataclass(frozen=True, slots=True)
class _Member:
    row: BudgetOverviewRowV1
    resource: Resource
    membership: FinancialPoolMembershipV1


def _group_selected(
    organization: OpaqueIdV1 | None, query: BudgetOverviewQueryV1
) -> bool:
    return (
        query.organization_ids is None
        or organization is None
        and query.include_ungrouped
        or organization in query.organization_ids
    )


def _report_matches(
    view: BudgetReportViewV1,
    member: FinancialPoolMembershipV1,
    query: BudgetOverviewQueryV1,
) -> bool:
    report, scope = view.report, member.scope
    return (
        report.subject.account_id == scope.account_id
        and report.subject.resource_id == scope.resource_id
        and report.subject.provider_key == scope.provider_key
        and report.scope_generation == scope.scope_generation
        and report.requested_period == query.period
        and view.stored_at <= query.as_of
        and (
            scope.selector == "billing"
            or scope.selector == "self"
            and report.source_category == "self_requests_and_cost"
        )
        and (
            report.scope_evidence == scope.scope_evidence == "unresolved"
            and report.binding_id == scope.binding_id
            and report.binding_generation == scope.binding_generation
            or report.scope_evidence != "unresolved"
            and scope.scope_evidence != "unresolved"
            and report.scope_id is not None
            and report.scope_id.value == scope.provider_scope_id
        )
    )


def _member_matches(
    row: BudgetOverviewRowV1,
    resource: Resource,
    member: FinancialPoolMembershipV1,
    query: BudgetOverviewQueryV1,
) -> bool:
    scope = member.scope
    if (
        scope.account_id != row.account.account_id
        or scope.resource_id != row.resource_id
        or scope.provider_key != row.account.provider_key
    ):
        return False
    views = tuple(
        view
        for selection in resource.reports
        for view in (selection.current, selection.latest_attempt)
        if view is not None
    )
    if any(not _report_matches(view, member, query) for view in views):
        return False
    if isinstance(resource, BudgetCloudResourceCurrentV1):
        graph = resource.target
        return (
            scope.selector == "self"
            and scope.scope_generation == 1
            and graph.lifecycle == "active"
            and scope.scope_evidence == "unresolved"
            and scope.binding_id == graph.binding.binding_id
            and scope.binding_generation == graph.binding.generation
        )
    connection = resource.connection
    return (
        scope.selector == "billing"
        and scope.scope_generation == connection.scope_generation
        and scope.provider_scope_id == connection.scope_id
        and (scope.scope_evidence == "unresolved")
        == (connection.scope_evidence == "unresolved")
        # The atomic registry snapshot fences membership against active binding.
        # Before a first report it still supplies metadata, never money; any
        # report above must independently match its exact credential lineage.
    )


def _context(
    selection: BudgetReportSelectionV1, reason: str | None = None
) -> BudgetOverviewContextV1:
    view = selection.current or selection.latest_attempt
    assert view is not None
    report = view.report
    spend = reported_spend(selection)
    assert spend is not None
    return BudgetOverviewContextV1(
        view.report_id,
        report.scope_generation,
        report.scope_id.value if report.scope_id else None,
        report.scope_evidence,
        report.source_id,
        report.source_category,
        report.cost_basis,
        report.currency,
        spend.total if reason is None else None,
        reason or spend.reason_code,
        report.source_data_through,
        report.collected_at,
        report.completeness,
        report_account_id=report.subject.account_id,
        report_resource_id=report.subject.resource_id,
    )


def _pool_readings(
    pool: FinancialPoolViewV1, members: tuple[_Member, ...]
) -> tuple[tuple[BudgetOverviewContextV1, ...], tuple[BudgetSpendInput, ...], set[str]]:
    groups: dict[GroupKey, list[BudgetSpendInput]] = defaultdict(list)
    for member in members:
        for selection in member.resource.reports:
            view = selection.current or selection.latest_attempt
            if view is None or view.report.grouping:
                continue
            report = view.report
            groups[(report.currency, report.cost_basis, report.source_category)].append(
                BudgetSpendInput(
                    member.membership.scope.resource_id,
                    pool.pool_id,
                    member.membership.association_evidence,
                    selection,
                )
            )
    contexts: list[BudgetOverviewContextV1] = []
    contributions: list[BudgetSpendInput] = []
    reasons: set[str] = set()
    if not groups:
        reasons.add("missing_report")
    for key in sorted(groups, key=lambda key: (key[0] or "", key[1], key[2])):
        candidates = groups[key]
        if len({item.resource_id for item in candidates}) != len(candidates):
            reason = "incompatible_pool_reports"
            aggregation = None
        else:
            try:
                aggregation = aggregate_budget_spend(tuple(candidates))
                reason = None
            except BudgetMoneyError:
                aggregation = None
                reason = "cost_total_unavailable"
        if aggregation is not None and aggregation.groups:
            # There is one pool and one currency/basis/category in this call.
            contribution = aggregation.groups[0].contributions[0]
            chosen = next(
                item
                for item in candidates
                if item.selection.current == contribution.report
            )
            contributions.append(chosen)
            contexts.append(_context(chosen.selection))
            # Other access paths do not make a complete canonical pool partial;
            # their collection failures remain visible on access_paths.
        else:
            reasons.update(
                {reason}
                if reason is not None
                else {item.reason for item in aggregation.coverage}
                if aggregation is not None
                else {"missing_report"}
            )
            invalid = reason or (
                "incompatible_pool_reports"
                if aggregation is not None
                and any(
                    item.reason == "incompatible_pool_reports"
                    for item in aggregation.coverage
                )
                else None
            )
            contexts.extend(_context(item.selection, invalid) for item in candidates)
    unique = {context.report_id: context for context in contexts}
    return (
        tuple(unique[key] for key in sorted(unique, key=lambda i: i.value)),
        tuple(contributions),
        reasons,
    )


def _pool_row(
    pool: FinancialPoolViewV1,
    members: tuple[_Member, ...],
    contexts: tuple[BudgetOverviewContextV1, ...],
    counted: bool,
) -> BudgetOverviewRowV1:
    ordered = sorted(
        members,
        key=lambda m: (
            m.row.account.account_id.value,
            m.membership.scope.resource_id.value,
        ),
    )
    representative = next(
        (
            m.row
            for m in ordered
            if m.row.account.organization_id == pool.primary_organization_id
        ),
        ordered[0].row,
    )
    worst = min((m.row for m in ordered), key=lambda row: (row.state_rank, row.row_id))
    funds_source = max(
        (m.row for m in ordered if m.row.funds),
        key=lambda row: (max(f.collected_at for f in row.funds), row.row_id),
        default=None,
    )
    funds = (
        ()
        if funds_source is None
        else tuple(
            replace(
                f,
                source_account_id=funds_source.account.account_id,
                source_resource_id=funds_source.resource_id,
            )
            for f in funds_source.funds
        )
    )
    return replace(
        representative,
        row_id=hashlib.sha256(
            ("financial-pool\0" + pool.pool_id.value).encode()
        ).hexdigest(),
        contexts=contexts,
        funds=funds,
        funds_reason_code=(
            funds_source.funds_reason_code
            if funds_source
            else representative.funds_reason_code
        ),
        state_code=worst.state_code,
        state_rank=worst.state_rank,
        collection_state=worst.collection_state,
        collection_error=worst.collection_error,
        monitoring_enabled=any(m.row.monitoring_enabled for m in ordered),
        pool_id=pool.pool_id,
        pool_name=pool.display_name,
        pool_selector=pool.selector,
        primary_organization_id=pool.primary_organization_id,
        association_evidence=(
            "owner_asserted"
            if any(
                m.membership.association_evidence == "owner_asserted" for m in ordered
            )
            else "provider_verified"
        ),
        counted_in_selection=counted,
        access_paths=tuple(
            BudgetOverviewAccessPathV1(
                m.row.account,
                m.membership.scope.resource_id,
                m.row.state_code,
                m.row.monitoring_enabled,
                m.row.collection_error,
            )
            for m in ordered
        ),
    )


def resolve_overview_pools(
    rows: tuple[BudgetOverviewRowV1, ...],
    currents: tuple[AccountBudgetCurrentV1, ...],
    snapshot: FinancialPoolSnapshotV1,
    query: BudgetOverviewQueryV1,
) -> BudgetPoolOverview:
    """Resolve whole selected pools before row pagination or organization filtering."""
    if (
        snapshot.as_of != query.as_of
        or any(
            current.as_of != query.as_of or current.period != query.period
            for current in currents
        )
        or len({current.account_id for current in currents}) != len(currents)
    ):
        raise BudgetOverviewError("budget_pool_snapshot_invalid")
    resources: dict[tuple[OpaqueIdV1, OpaqueIdV1], Resource] = {}
    for current in currents:
        if current.availability.state != "available":
            continue
        for billing in current.resources:
            resources[(current.account_id, billing.connection.resource_id)] = billing
        for cloud in current.cloud_resources:
            resources[(current.account_id, cloud.target.resource_id)] = cloud
    pools = {pool.pool_id: pool for pool in snapshot.pools}
    grouped: dict[OpaqueIdV1, list[_Member]] = defaultdict(list)
    remaining = []
    base_query = replace(query, organization_ids=None)
    for row in rows:
        if not account_matches(row.account, base_query):
            continue
        resource = (
            resources.get((row.account.account_id, row.resource_id))
            if row.resource_id
            else None
        )
        matches = tuple(
            member
            for member in snapshot.memberships
            if resource is not None and _member_matches(row, resource, member, query)
        )
        if len(matches) > 1:
            raise BudgetOverviewError("budget_pool_membership_ambiguous")
        if matches and resource is not None:
            grouped[matches[0].pool_id].append(_Member(row, resource, matches[0]))
        elif account_matches(row.account, query):
            remaining.append(replace(row, counted_in_selection=False))
    result_rows = list(remaining)
    excluded: dict[tuple[str, str], tuple[OpaqueIdV1 | None, set[str]]] = {}
    for row in remaining:
        if row.resource_id is not None:
            reason = (
                "unresolved_overlap"
                if snapshot.availability.state == "available"
                else "pool_metadata_unavailable"
            )
            excluded[("resource", row.row_id)] = (row.account.organization_id, {reason})
    chosen: list[BudgetSpendInput] = []
    for pool_id in sorted(grouped, key=lambda i: i.value):
        pool, members = pools[pool_id], tuple(grouped[pool_id])
        counted = _group_selected(pool.primary_organization_id, query)
        if not counted and not any(
            account_matches(m.row.account, query) for m in members
        ):
            continue
        contexts, contributions, reasons = _pool_readings(pool, members)
        result_rows.append(_pool_row(pool, members, contexts, counted))
        if counted:
            chosen.extend(contributions)
            if reasons:
                excluded[("pool", pool_id.value)] = (
                    pool.primary_organization_id,
                    reasons,
                )
    summaries: list[BudgetOverviewSummaryV1] = []
    groups: dict[GroupKey, list[BudgetSpendInput]] = defaultdict(list)
    for item in chosen:
        assert item.selection.current is not None
        report = item.selection.current.report
        groups[(report.currency, report.cost_basis, report.source_category)].append(
            item
        )
    for key in sorted(groups, key=lambda key: (key[0] or "", key[1], key[2])):
        candidates = groups[key]
        organizations = {
            pools[item.canonical_pool_id].primary_organization_id
            for item in candidates
            if item.canonical_pool_id is not None
        }
        for kind, organization in [
            ("global", None),
            *(
                ("organization", org)
                for org in sorted(organizations, key=lambda i: i.value if i else "")
            ),
        ]:
            inputs = tuple(
                item
                for item in candidates
                if kind == "global"
                or item.canonical_pool_id is not None
                and pools[item.canonical_pool_id].primary_organization_id
                == organization
            )
            try:
                aggregation = aggregate_budget_spend(inputs)
            except BudgetMoneyError:
                for item in inputs:
                    assert item.canonical_pool_id is not None
                    excluded[("pool", item.canonical_pool_id.value)] = (
                        pools[item.canonical_pool_id].primary_organization_id,
                        {"cost_total_unavailable"},
                    )
                continue
            for group in aggregation.groups:
                summaries.append(
                    BudgetOverviewSummaryV1(
                        "global" if kind == "global" else "organization",
                        organization,
                        group.currency,
                        group.cost_basis,
                        group.source_category,
                        group.total,
                        len(group.contributions),
                        0,  # Final coverage is attached after every group is checked.
                    )
                )
    summaries = [
        replace(
            summary,
            excluded_resource_count=sum(
                summary.scope_kind == "global" or org == summary.organization_id
                for org, _ in excluded.values()
            ),
        )
        for summary in summaries
    ]
    counts = Counter(reason for _, reasons in excluded.values() for reason in reasons)
    exclusions = tuple(
        BudgetOverviewExclusionV1(reason, counts[reason]) for reason in sorted(counts)
    )
    summary_reason = (
        (
            "partial_coverage"
            if summaries
            else next(iter(counts))
            if len(counts) == 1
            else "no_eligible_reports"
        )
        if counts
        else None
    )
    return BudgetPoolOverview(
        tuple(result_rows), tuple(summaries), exclusions, summary_reason
    )

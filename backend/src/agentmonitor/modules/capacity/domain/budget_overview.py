"""Pure compact financial Overview projection and snapshot pagination."""

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict
from datetime import datetime
from typing import Literal

from agentmonitor.contracts.budget_query_v1 import (
    AccountBudgetCurrentV1,
    BudgetCloudResourceCurrentV1,
    BudgetFundComponentV1,
    BudgetOverviewContextV1,
    BudgetOverviewExclusionV1,
    BudgetOverviewFundV1,
    BudgetOverviewQueryV1,
    BudgetOverviewResultV1,
    BudgetOverviewRowV1,
    BudgetOverviewSummaryV1,
    BudgetResourceCurrentV1,
)
from agentmonitor.contracts.common_v1 import (
    OpaqueIdV1,
    QueryAvailabilityV1,
    QueryPageV1,
)
from agentmonitor.contracts.registry_v1 import AccountResourceViewV1, AccountViewV1
from agentmonitor.modules.capacity.domain.budget_account_spend import reported_spend
from agentmonitor.modules.capacity.domain.budget_money import remaining_percentage

MAX_ACCOUNTS = 2000
_API_KINDS = {"api_organization", "api_project", "workspace", "prepaid_credit_pool"}


class BudgetOverviewError(ValueError):
    """Closed query failures contain no financial or identity values."""


def account_matches(account: AccountViewV1, query: BudgetOverviewQueryV1) -> bool:
    return (
        account.lifecycle != "archived"
        and (query.provider_key is None or account.provider_key == query.provider_key)
        and (
            query.organization_ids is None
            or account.organization_id is None
            and query.include_ungrouped
            or account.organization_id in query.organization_ids
        )
    )


def has_subscription(
    account: AccountViewV1,
    resources: tuple[AccountResourceViewV1, ...],
    *,
    has_cloud_resources: bool = False,
) -> bool:
    if resources:
        return any(
            r.kind == "subscription_pool" and r.lifecycle == "active" for r in resources
        )
    return not has_cloud_resources and account.initial_connection_purpose != "api"


def requires_financial_query(
    account: AccountViewV1,
    resources: tuple[AccountResourceViewV1, ...],
) -> bool:
    """Only proven subscription-only accounts can omit financial reads.

    Billing enrollment adds its resource atomically. Ollama cloud authority is
    separate from this resource list, so cloud accounts always need the query.
    Retained non-subscription resources and ambiguous/pending metadata also do.
    """
    return not (
        account.provider_key in {"claude", "codex"}
        and account.initial_connection_purpose is None
        # ListAccountResourcesV1 returns at most 100 rows without a next-page
        # marker. A full list cannot establish absence of a billing resource.
        and len(resources) < 100
        and any(
            r.kind == "subscription_pool" and r.lifecycle == "active" for r in resources
        )
        and all(r.kind == "subscription_pool" for r in resources)
    )


def append_inventory_page(
    previous: tuple[AccountViewV1, ...],
    page: QueryPageV1[AccountViewV1],
    as_of: datetime,
) -> tuple[AccountViewV1, ...]:
    if page.availability.state != "available" or page.availability.as_of != as_of:
        raise BudgetOverviewError("budget_overview_inventory_unavailable")
    combined = previous + page.items
    if len(combined) > MAX_ACCOUNTS or len(combined) == MAX_ACCOUNTS and page.has_more:
        raise BudgetOverviewError("budget_overview_inventory_overflow")
    if (
        len({a.account_id for a in combined}) != len(combined)
        or page.has_more
        and not page.items
    ):
        raise BudgetOverviewError("budget_overview_inventory_invalid")
    if len({a.registry_revision for a in combined}) > 1:
        raise BudgetOverviewError("budget_overview_registry_changed")
    return combined


def _hash(value: object) -> str:
    def encode(item: object) -> str:
        if isinstance(item, datetime):
            return item.isoformat()
        raise TypeError("budget_overview_hash_invalid")

    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=encode,
        ).encode("ascii")
    ).hexdigest()


def _fund(component: BudgetFundComponentV1) -> BudgetOverviewFundV1:
    ratio = remaining_percentage(
        component.remaining.value, component.limit.value, compatible=True
    )
    return BudgetOverviewFundV1(
        component.component_id,
        component.kind,
        component.remaining,
        component.limit,
        ratio.percentage_text if ratio else None,
        ratio.is_low_remaining if ratio else None,
        "remaining_percentage_calculated" if ratio else "percentage_inputs_unavailable",
        component.is_constraining,
        component.collected_at,
        component.observed_at,
        component.freshness,
        component.observation_id,
        percentage_method=ratio.method_id if ratio else None,
        percentage_decimal_places=ratio.decimal_places if ratio else None,
        percentage_rounding=ratio.rounding if ratio else None,
        source_account_id=component.subject.account_id,
        source_resource_id=component.subject.resource_id,
    )


def _contexts(
    resource: BudgetResourceCurrentV1 | BudgetCloudResourceCurrentV1 | None,
    account: AccountViewV1,
    resource_id: OpaqueIdV1,
    query: BudgetOverviewQueryV1,
) -> tuple[BudgetOverviewContextV1, ...]:
    if resource is None:
        return ()
    result = []
    for selection in resource.reports:
        selected = selection.current or selection.latest_attempt
        if selected is None:
            continue
        report = selected.report
        if (
            report.subject.account_id != account.account_id
            or report.subject.resource_id != resource_id
            or report.subject.provider_key != account.provider_key
            or report.requested_period != query.period
            or selected.stored_at > query.as_of
        ):
            raise BudgetOverviewError("budget_overview_report_context_invalid")
        # Grouped reports are breakdowns, not another total-cost context.
        if report.grouping:
            continue
        spend = reported_spend(selection)
        assert spend is not None
        result.append(
            BudgetOverviewContextV1(
                selected.report_id,
                report.scope_generation,
                report.scope_id.value if report.scope_id else None,
                report.scope_evidence,
                report.source_id,
                report.source_category,
                report.cost_basis,
                report.currency,
                spend.total,
                spend.reason_code,
                report.source_data_through,
                report.collected_at,
                report.completeness,
                report_account_id=report.subject.account_id,
                report_resource_id=report.subject.resource_id,
            )
        )
    if len({c.report_id for c in result}) != len(result):
        raise BudgetOverviewError("budget_overview_report_context_invalid")
    return tuple(
        sorted(
            result,
            key=lambda c: (
                c.source_id,
                c.source_category,
                c.cost_basis,
                c.currency or "",
                c.report_id.value,
            ),
        )
    )


def _state(
    *,
    owner_action: str | None,
    query_unavailable: bool,
    resource: BudgetResourceCurrentV1 | BudgetCloudResourceCurrentV1 | None,
    contexts: tuple[BudgetOverviewContextV1, ...],
    funds: tuple[BudgetOverviewFundV1, ...],
    funds_incomplete: bool,
    as_of: datetime,
) -> tuple[str, int, str | None, str | None]:
    run = resource.latest_collection if resource is not None else None
    run_visible = (
        run is not None
        and run.requested_at <= as_of
        and (run.completed_at is None or run.completed_at <= as_of)
    )
    collection_state = run.state if run is not None and run_visible else None
    collection_error = run.error_code if run is not None and run_visible else None
    if owner_action is not None or collection_state == "blocked":
        return (
            owner_action or "owner_action_required",
            0,
            collection_state,
            collection_error,
        )
    if collection_state in {"failed", "timed_out", "cancelled", "unsupported"}:
        return "collection_failed", 1, collection_state, collection_error
    if (
        query_unavailable
        or resource is not None
        and (
            resource.collection_availability.state != "available"
            or resource.report_availability.state == "unavailable"
        )
    ):
        return "budget_query_unavailable", 2, collection_state, collection_error
    if run is not None and not run_visible:
        return "collection_history_unavailable", 2, None, None
    if (
        any(
            c.completeness != "complete"
            or c.spend_reason in {"report_incomplete", "report_coverage_incomplete"}
            for c in contexts
        )
        or collection_state == "partial"
        or funds_incomplete
    ):
        return "incomplete", 2, collection_state, collection_error
    if any(f.freshness in {"stale", "conflicted", "no_observation"} for f in funds):
        return "stale", 2, collection_state, collection_error
    if any(f.freshness != "fresh" for f in funds) or any(
        c.source_data_through is None for c in contexts
    ):
        return "freshness_unknown", 2, collection_state, collection_error
    if not contexts and not funds:
        return "no_report", 2, collection_state, collection_error
    if any(f.is_constraining is True and f.is_low is True for f in funds):
        return "low", 3, collection_state, collection_error
    return "current", 4, collection_state, collection_error


def project_budget_rows(
    account: AccountViewV1,
    resources: tuple[AccountResourceViewV1, ...],
    current: AccountBudgetCurrentV1 | None,
    query: BudgetOverviewQueryV1,
) -> tuple[BudgetOverviewRowV1, ...]:
    if not account_matches(account, query):
        return ()
    if current is not None and (
        current.account_id != account.account_id
        or current.as_of != query.as_of
        or current.period != query.period
    ):
        raise BudgetOverviewError("budget_overview_account_context_invalid")
    if any(r.account_id != account.account_id for r in resources) or len(
        {r.resource_id for r in resources}
    ) != len(resources):
        raise BudgetOverviewError("budget_overview_resource_context_invalid")
    active = {r.resource_id: r for r in resources if r.lifecycle == "active"}
    billing = (
        {}
        if current is None
        else {r.connection.resource_id: r for r in current.resources}
    )
    cloud = (
        {}
        if current is None
        else {r.target.resource_id: r for r in current.cloud_resources}
    )
    components = (
        () if current is None or current.funds is None else current.funds.components
    )
    if any(f.subject.provider_key != account.provider_key for f in components):
        raise BudgetOverviewError("budget_overview_funds_context_invalid")
    identities = set(billing) | set(cloud) | {f.subject.resource_id for f in components}
    # Cloud graph resources have their own published registry authority and need
    # not also be registered as local profile/account resources.
    cloud_authority = {i for i, r in cloud.items() if r.target.lifecycle == "active"}
    if not identities.issubset(set(active) | cloud_authority):
        raise BudgetOverviewError("budget_overview_registry_changed")
    identities |= {r.resource_id for r in active.values() if r.kind in _API_KINDS}
    result = []
    for identity in sorted(identities, key=lambda i: i.value):
        resource: BudgetResourceCurrentV1 | BudgetCloudResourceCurrentV1 | None = (
            billing.get(identity) or cloud.get(identity)
        )
        resource_kind: Literal["billing", "cloud", "unconfigured"] = (
            "billing"
            if identity in billing
            else "cloud"
            if identity in cloud
            or any(f.subject.resource_id == identity for f in components)
            else "unconfigured"
        )
        monitoring = (
            resource.connection.monitoring_preference == "enabled"
            if isinstance(resource, BudgetResourceCurrentV1)
            else account.is_effective_monitoring_enabled
        )
        owner_action = (
            "setup_required"
            if resource_kind == "unconfigured"
            else "connection_required"
            if isinstance(resource, BudgetResourceCurrentV1)
            and resource.connection.lifecycle != "active"
            else "monitoring_disabled"
            if not monitoring
            else None
        )
        funds = tuple(
            _fund(f)
            for f in sorted(components, key=lambda f: f.component_id.value)
            if f.subject.resource_id == identity
        )
        contexts = _contexts(resource, account, identity, query)
        code, rank, collection_state, collection_error = _state(
            owner_action=owner_action,
            query_unavailable=current is None
            or current.availability.state != "available",
            resource=resource,
            contexts=contexts,
            funds=funds,
            funds_incomplete=any(
                f.completeness != "complete" or f.remaining.value is None
                for f in components
                if f.subject.resource_id == identity
            ),
            as_of=query.as_of,
        )
        funds_reason = (
            None
            if funds
            else current.funds.availability.reason_code
            if current is not None
            and current.funds is not None
            and current.funds.availability.state != "available"
            else "funds_source_unavailable"
        )
        result.append(
            BudgetOverviewRowV1(
                _hash((account.account_id.value, identity.value)),
                account,
                identity,
                resource_kind,
                monitoring,
                code,
                rank,
                contexts,
                funds,
                collection_state,
                collection_error,
                funds_reason_code=funds_reason,
            )
        )
    if not result and not resources and account.initial_connection_purpose == "api":
        result.append(
            BudgetOverviewRowV1(
                _hash((account.account_id.value, None)),
                account,
                None,
                "unconfigured",
                False,
                "setup_required",
                0,
                (),
                (),
                None,
                None,
                funds_reason_code="funds_source_unavailable",
            )
        )
    return tuple(result)


def overview_result(
    rows: tuple[BudgetOverviewRowV1, ...],
    query: BudgetOverviewQueryV1,
    *,
    registry_revision: int,
    inventory_count: int,
    subscription_account_ids: tuple[OpaqueIdV1, ...],
    summaries: tuple[BudgetOverviewSummaryV1, ...] = (),
    exclusions: tuple[BudgetOverviewExclusionV1, ...] | None = None,
    summary_reason: str | None = None,
    organization_labels: Mapping[OpaqueIdV1, str | None] | None = None,
) -> BudgetOverviewResultV1:
    labels = organization_labels or {}

    def group_name(row: BudgetOverviewRowV1) -> str:
        identity = (
            row.primary_organization_id if row.pool_id else row.account.organization_id
        )
        return (
            "Ungrouped"
            if identity is None
            else labels.get(identity) or "Organization unavailable"
        ).casefold()

    def account_name(row: BudgetOverviewRowV1) -> str:
        return (row.pool_name or row.account.friendly_name).casefold()

    # A direction change reverses the chosen field, never its deterministic ties.
    stable = sorted(
        rows,
        key=lambda row: (
            group_name(row),
            account_name(row),
            row.account.account_id.value,
            row.resource_id.value if row.resource_id else "",
            row.row_id,
        ),
    )
    ordered = tuple(
        sorted(
            stable,
            key=lambda row: (
                row.state_rank
                if query.sort_by == "state"
                else group_name(row)
                if query.sort_by == "organization"
                else account_name(row)
            ),
            reverse=query.sort_direction == "descending",
        )
    )
    if len({r.row_id for r in ordered}) != len(ordered):
        raise BudgetOverviewError("budget_overview_rows_invalid")
    selection = asdict(query)
    selection.pop("after_key")
    snapshot = _hash(
        (
            selection,
            registry_revision,
            tuple(sorted((key.value, value) for key, value in labels.items())),
            inventory_count,
            tuple(i.value for i in subscription_account_ids),
            tuple(asdict(row) for row in ordered),
            tuple(asdict(summary) for summary in summaries),
            None if exclusions is None else tuple(asdict(e) for e in exclusions),
            summary_reason,
        )
    )
    cursors = tuple(_hash((snapshot, row.row_id)) for row in ordered)
    start = 0
    if query.after_key is not None:
        if len(query.after_key) != 64 or any(
            c not in "0123456789abcdef" for c in query.after_key
        ):
            raise BudgetOverviewError("budget_overview_cursor_invalid")
        if query.after_key not in cursors:
            raise BudgetOverviewError("budget_overview_cursor_expired")
        start = cursors.index(query.after_key) + 1
    items = ordered[start : start + query.limit]
    more = start + len(items) < len(ordered)
    excluded = sum(row.resource_id is not None for row in ordered)
    return BudgetOverviewResultV1(
        query.period,
        query.as_of,
        QueryPageV1(
            items,
            query.limit,
            more,
            cursors[start + len(items) - 1] if more else None,
            QueryAvailabilityV1("available", "budget_overview_read", query.as_of),
        ),
        summaries,
        exclusions
        if exclusions is not None
        else (
            (BudgetOverviewExclusionV1("unresolved_overlap", excluded),)
            if excluded
            else ()
        ),
        summary_reason
        if exclusions is not None
        else ("unresolved_overlap" if excluded else None),
        inventory_count,
        registry_revision,
        subscription_account_ids,
    )

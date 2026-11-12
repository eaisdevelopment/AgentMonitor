"""Read-only financial Overview; M05 owns selection, state and arithmetic."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from agentmonitor.api.problem import ProblemError
from agentmonitor.api.v1.dependencies import authorize_request, observation_ports
from agentmonitor.api.v1.routers._observation import (
    ERROR_RESPONSES,
    availability,
    decode_cursor,
    page_meta,
    policy,
    reject_unknown_query,
    require_opaque_selector,
)
from agentmonitor.api.v1.routers.budgets import (
    _money,
    _money_field,
    _period,
    cost_bucket_wire,
    report_summary_wire,
    report_wire,
    reported_spend_wire,
    usage_bucket_wire,
)
from agentmonitor.api.v1.schemas.budget_overview import (
    BudgetOverviewAccessPathWireV1,
    BudgetOverviewContextWireV1,
    BudgetOverviewExclusionWireV1,
    BudgetOverviewFundWireV1,
    BudgetOverviewRowWireV1,
    BudgetOverviewSummaryWireV1,
    BudgetOverviewWireV1,
    BudgetSelectedReportWireV1,
)
from agentmonitor.api.v1.schemas.budgets import (
    BudgetHistoryRowWireV1,
    BudgetHistoryWireV1,
    BudgetReportedSpendWireV1,
    BudgetReportListWireV1,
)
from agentmonitor.api.v1.schemas.registry import AccountViewV1
from agentmonitor.api.v1.serialization import technical_wire
from agentmonitor.contracts.budget_query_v1 import (
    BudgetHistoryQueryV1,
    BudgetOverviewQueryV1,
    BudgetOverviewRowV1,
)
from agentmonitor.contracts.capacity_v1 import (
    BudgetPeriodV1,
    BudgetReportHistoryQueryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.capacity.application.queries import CapacityQueryUnavailableV1
from fastapi import APIRouter, Query, Request

router = APIRouter(tags=["budgets"])
OPERATION = "capacity_list_budget_overview_v1"


def overview_row_wire(row: BudgetOverviewRowV1) -> BudgetOverviewRowWireV1:
    return BudgetOverviewRowWireV1(
        row_id=row.row_id,
        account=AccountViewV1.model_validate(technical_wire(row.account)),
        resource_id=None if row.resource_id is None else row.resource_id.value,
        resource_kind=row.resource_kind,
        monitoring_enabled=row.monitoring_enabled,
        state_code=row.state_code,
        state_rank=row.state_rank,
        contexts=[
            BudgetOverviewContextWireV1(
                report_id=c.report_id.value,
                scope_generation=c.scope_generation,
                scope_id=c.scope_id,
                scope_evidence=c.scope_evidence,
                source_id=c.source_id,
                source_category=c.source_category,
                cost_basis=c.cost_basis,
                currency=c.currency,
                spend=None if c.spend is None else _money(c.spend),
                spend_reason=c.spend_reason,
                source_data_through=c.source_data_through,
                collected_at=c.collected_at,
                completeness=c.completeness,
                report_account_id=c.report_account_id.value
                if c.report_account_id
                else None,
                report_resource_id=c.report_resource_id.value
                if c.report_resource_id
                else None,
            )
            for c in row.contexts
        ],
        funds=[
            BudgetOverviewFundWireV1(
                component_id=f.component_id.value,
                kind=f.kind,
                remaining=_money_field(f.remaining),
                limit=_money_field(f.limit),
                percentage_text=f.percentage_text,
                is_low=f.is_low,
                percentage_reason=f.percentage_reason,
                is_constraining=f.is_constraining,
                collected_at=f.collected_at,
                observed_at=f.observed_at,
                freshness=f.freshness,
                observation_id=f.observation_id.value,
                percentage_method=f.percentage_method,
                percentage_decimal_places=f.percentage_decimal_places,
                percentage_rounding=f.percentage_rounding,
                source_account_id=f.source_account_id.value
                if f.source_account_id
                else None,
                source_resource_id=f.source_resource_id.value
                if f.source_resource_id
                else None,
            )
            for f in row.funds
        ],
        collection_state=row.collection_state,
        collection_error=row.collection_error,
        funds_reason_code=row.funds_reason_code,
        pool_id=row.pool_id.value if row.pool_id else None,
        pool_name=row.pool_name,
        pool_selector=row.pool_selector,
        primary_organization_id=row.primary_organization_id.value
        if row.primary_organization_id
        else None,
        association_evidence=row.association_evidence,
        counted_in_selection=row.counted_in_selection,
        access_paths=tuple(
            BudgetOverviewAccessPathWireV1(
                account=AccountViewV1.model_validate(technical_wire(path.account)),
                resource_id=path.resource_id.value,
                state_code=path.state_code,
                monitoring_enabled=path.monitoring_enabled,
                collection_error=path.collection_error,
            )
            for path in row.access_paths
        ),
    )


@router.get(
    "/budgets",
    operation_id=OPERATION,
    response_model=BudgetOverviewWireV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:telemetry", "BudgetOverviewPortV1"),
)
def list_budget_overview(
    request: Request,
    period_start: Annotated[datetime, Query()],
    period_end: Annotated[datetime, Query()],
    as_of: Annotated[datetime, Query()],
    organization_ids: Annotated[
        str | None,
        Query(
            max_length=26000, description="Comma-separated IDs; absent all, empty none."
        ),
    ] = None,
    include_ungrouped: bool = False,
    provider_key: Annotated[str | None, Query(max_length=64)] = None,
    sort_by: Literal["account", "organization", "state"] = "state",
    sort_direction: Literal["ascending", "descending"] = "ascending",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: Annotated[str | None, Query(max_length=4096)] = None,
) -> BudgetOverviewWireV1:
    caller = authorize_request(request, "read:telemetry")
    reject_unknown_query(
        request,
        frozenset(
            {
                "period_start",
                "period_end",
                "as_of",
                "organization_ids",
                "include_ungrouped",
                "provider_key",
                "sort_by",
                "sort_direction",
                "limit",
                "cursor",
            }
        ),
    )
    if any(
        v.utcoffset() != UTC.utcoffset(v) for v in (period_start, period_end, as_of)
    ):
        raise ProblemError(400, "invalid_filter")
    groups = None
    if organization_ids is not None:
        raw = [] if organization_ids == "" else organization_ids.split(",")
        if len(raw) > 100:
            raise ProblemError(400, "invalid_filter")
        groups = tuple(OpaqueIdV1(require_opaque_selector(v)) for v in raw)
    filters = {
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "as_of": as_of.isoformat(),
        "organization_ids": organization_ids,
        "include_ungrouped": str(include_ungrouped),
        "provider_key": provider_key,
        "sort_by": sort_by,
        "sort_direction": sort_direction,
    }
    after_key = decode_cursor(
        request, caller, cursor, operation_id=OPERATION, limit=limit, filters=filters
    )
    try:
        query = BudgetOverviewQueryV1(
            period=BudgetPeriodV1(period_start, period_end),
            as_of=as_of,
            organization_ids=groups,
            include_ungrouped=include_ungrouped,
            provider_key=provider_key,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=limit,
            after_key=after_key,
        )
    except (TypeError, ValueError):
        raise ProblemError(400, "invalid_filter") from None
    port = observation_ports(request).list_budget_overview
    if port is None:
        raise ProblemError(503, "observation_data_unavailable")
    try:
        result = port(query)
    except CapacityQueryUnavailableV1:
        raise ProblemError(503, "observation_repository_unavailable") from None
    return BudgetOverviewWireV1(
        period=_period(result.period),
        as_of=result.as_of,
        items=[overview_row_wire(row) for row in result.page.items],
        page=page_meta(
            request,
            caller,
            operation_id=OPERATION,
            limit=limit,
            has_more=result.page.has_more,
            next_key=result.page.next_key,
            filters=filters,
        ),
        availability=availability(result.page.availability),
        summaries=[
            BudgetOverviewSummaryWireV1(
                scope_kind=s.scope_kind,
                organization_id=None
                if s.organization_id is None
                else s.organization_id.value,
                currency=s.currency,
                cost_basis=s.cost_basis,
                source_category=s.source_category,
                total=_money(s.total),
                included_pool_count=s.included_pool_count,
                excluded_resource_count=s.excluded_resource_count,
            )
            for s in result.summaries
        ],
        exclusions=[
            BudgetOverviewExclusionWireV1(reason_code=e.reason_code, count=e.count)
            for e in result.exclusions
        ],
        summary_reason=result.summary_reason,
        inventory_count=result.inventory_count,
        registry_revision=result.registry_revision,
        subscription_account_ids=[v.value for v in result.subscription_account_ids],
    )


@router.get(
    "/budgets/{budget_id}",
    operation_id="capacity_get_budget_v1",
    response_model=BudgetSelectedReportWireV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:telemetry", "BudgetSelectedReportPortV1"),
)
def get_selected_budget_report(
    budget_id: str,
    request: Request,
    account_id: str,
    report_id: str,
    period_start: Annotated[datetime, Query()],
    period_end: Annotated[datetime, Query()],
    as_of: Annotated[datetime, Query()],
) -> BudgetSelectedReportWireV1:
    authorize_request(request, "read:telemetry")
    reject_unknown_query(
        request,
        frozenset({"account_id", "report_id", "period_start", "period_end", "as_of"}),
    )
    for value in (budget_id, account_id, report_id):
        require_opaque_selector(value)
    try:
        query = BudgetOverviewQueryV1(BudgetPeriodV1(period_start, period_end), as_of)
    except (TypeError, ValueError):
        raise ProblemError(400, "invalid_filter") from None
    port = observation_ports(request).get_selected_budget_report
    if port is None:
        raise ProblemError(503, "observation_data_unavailable")
    try:
        selected = port(
            OpaqueIdV1(account_id),
            OpaqueIdV1(budget_id),
            OpaqueIdV1(report_id),
            period=query.period,
            as_of=query.as_of,
        )
    except (CapacityQueryUnavailableV1, ValueError):
        raise ProblemError(503, "observation_repository_unavailable") from None
    if selected is None:
        raise ProblemError(404, "budget_report_not_found")
    return BudgetSelectedReportWireV1(
        report=report_wire(selected.report),
        reported_spend=BudgetReportedSpendWireV1(
            report_id=selected.reported_spend.report_id.value,
            total=None
            if selected.reported_spend.total is None
            else _money(selected.reported_spend.total),
            reason_code=selected.reported_spend.reason_code,
        ),
        as_of=selected.as_of,
    )


@router.get(
    "/budgets/{budget_id}/history",
    operation_id="capacity_list_budget_history_v1",
    response_model=BudgetHistoryWireV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:telemetry", "BudgetHistoryPortV1"),
)
def list_budget_history(
    budget_id: str,
    request: Request,
    account_id: str,
    report_id: str,
    period_start: Annotated[datetime, Query()],
    period_end: Annotated[datetime, Query()],
    as_of: Annotated[datetime, Query()],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: Annotated[str | None, Query(max_length=4096)] = None,
) -> BudgetHistoryWireV1:
    caller = authorize_request(request, "read:telemetry")
    reject_unknown_query(
        request,
        frozenset(
            {
                "account_id",
                "report_id",
                "period_start",
                "period_end",
                "as_of",
                "limit",
                "cursor",
            }
        ),
    )
    for value in (budget_id, account_id, report_id):
        require_opaque_selector(value)
    if any(
        v.utcoffset() != UTC.utcoffset(v) for v in (period_start, period_end, as_of)
    ):
        raise ProblemError(400, "invalid_filter")
    operation = "capacity_list_budget_history_v1"
    filters: dict[str, str | None] = {
        "budget_id": budget_id,
        "account_id": account_id,
        "report_id": report_id,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "as_of": as_of.isoformat(),
    }
    after_key = decode_cursor(
        request, caller, cursor, operation_id=operation, limit=limit, filters=filters
    )
    try:
        query = BudgetHistoryQueryV1(
            OpaqueIdV1(account_id),
            OpaqueIdV1(budget_id),
            OpaqueIdV1(report_id),
            BudgetPeriodV1(period_start, period_end),
            as_of,
            limit,
            after_key,
        )
    except (TypeError, ValueError):
        raise ProblemError(400, "invalid_filter") from None
    port = observation_ports(request).list_budget_history
    if port is None:
        raise ProblemError(503, "observation_data_unavailable")
    try:
        result = port(query)
    except CapacityQueryUnavailableV1:
        raise ProblemError(503, "observation_repository_unavailable") from None
    except ValueError as error:
        if str(error) == "budget_history_cursor_invalid":
            raise ProblemError(400, "invalid_cursor") from None
        raise ProblemError(503, "observation_repository_unavailable") from None
    if result is None:
        raise ProblemError(404, "budget_report_not_found")
    return BudgetHistoryWireV1(
        report=report_summary_wire(result.report),
        reported_spend=reported_spend_wire(result.reported_spend),
        as_of=result.as_of,
        items=[
            BudgetHistoryRowWireV1(
                kind=row.kind,
                cost=None if row.cost is None else cost_bucket_wire(row.cost),
                usage=None if row.usage is None else usage_bucket_wire(row.usage),
            )
            for row in result.page.items
        ],
        page=page_meta(
            request,
            caller,
            operation_id=operation,
            limit=limit,
            has_more=result.page.has_more,
            next_key=result.page.next_key,
            filters=filters,
        ),
        availability=availability(result.page.availability),
    )


@router.get(
    "/budgets/{budget_id}/reports",
    operation_id="capacity_list_budget_reports_v1",
    response_model=BudgetReportListWireV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:telemetry", "BudgetReportHistoryPortV1"),
)
def list_budget_reports(
    budget_id: str,
    request: Request,
    account_id: str,
    period_start: Annotated[datetime, Query()],
    period_end: Annotated[datetime, Query()],
    as_of: Annotated[datetime, Query()],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: Annotated[str | None, Query(max_length=4096)] = None,
) -> BudgetReportListWireV1:
    caller = authorize_request(request, "read:telemetry")
    reject_unknown_query(
        request,
        frozenset(
            {"account_id", "period_start", "period_end", "as_of", "limit", "cursor"}
        ),
    )
    for value in (budget_id, account_id):
        require_opaque_selector(value)
    if any(
        v.utcoffset() != UTC.utcoffset(v) for v in (period_start, period_end, as_of)
    ):
        raise ProblemError(400, "invalid_filter")
    operation = "capacity_list_budget_reports_v1"
    filters: dict[str, str | None] = {
        "budget_id": budget_id,
        "account_id": account_id,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "as_of": as_of.isoformat(),
    }
    after_key = decode_cursor(
        request, caller, cursor, operation_id=operation, limit=limit, filters=filters
    )
    try:
        query = BudgetReportHistoryQueryV1(
            OpaqueIdV1(account_id),
            OpaqueIdV1(budget_id),
            BudgetPeriodV1(period_start, period_end),
            limit,
            after_key,
            as_of,
        )
    except (TypeError, ValueError):
        raise ProblemError(400, "invalid_filter") from None
    port = observation_ports(request).list_budget_reports
    if port is None:
        raise ProblemError(503, "observation_data_unavailable")
    try:
        result = port(query)
    except CapacityQueryUnavailableV1:
        raise ProblemError(503, "observation_repository_unavailable") from None
    except ValueError as error:
        if str(error) == "budget_history_cursor_invalid":
            raise ProblemError(400, "invalid_cursor") from None
        raise ProblemError(503, "observation_repository_unavailable") from None
    if result is None:
        raise ProblemError(404, "registry_subject_not_found")
    return BudgetReportListWireV1(
        account_id=account_id,
        resource_id=budget_id,
        period=_period(query.period),
        as_of=as_of,
        items=[report_summary_wire(item) for item in result.items],
        page=page_meta(
            request,
            caller,
            operation_id=operation,
            limit=limit,
            has_more=result.has_more,
            next_key=result.next_key,
            filters=filters,
        ),
        availability=availability(result.availability),
    )

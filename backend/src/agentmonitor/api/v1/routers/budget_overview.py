"""Read-only financial Overview; M05 owns selection, state and arithmetic."""

from datetime import UTC, datetime
from typing import Annotated

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
    report_wire,
)
from agentmonitor.api.v1.schemas.budget_overview import (
    BudgetOverviewContextWireV1,
    BudgetOverviewExclusionWireV1,
    BudgetOverviewFundWireV1,
    BudgetOverviewRowWireV1,
    BudgetOverviewSummaryWireV1,
    BudgetOverviewWireV1,
    BudgetSelectedReportWireV1,
)
from agentmonitor.api.v1.schemas.budgets import BudgetReportedSpendWireV1
from agentmonitor.api.v1.schemas.registry import AccountViewV1
from agentmonitor.api.v1.serialization import technical_wire
from agentmonitor.contracts.budget_query_v1 import (
    BudgetOverviewQueryV1,
    BudgetOverviewRowV1,
)
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1
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
            )
            for f in row.funds
        ],
        collection_state=row.collection_state,
        collection_error=row.collection_error,
        funds_reason_code=row.funds_reason_code,
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

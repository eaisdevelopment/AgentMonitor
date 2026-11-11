"""P01 account financial read; application ports own selection and arithmetic."""

from datetime import UTC, datetime
from typing import Annotated

from agentmonitor.api.problem import ProblemError
from agentmonitor.api.v1.dependencies import authorize_request, observation_ports
from agentmonitor.api.v1.routers._observation import (
    ERROR_RESPONSES,
    availability,
    policy,
    reject_unknown_query,
    require_opaque_selector,
)
from agentmonitor.api.v1.schemas.budgets import (
    AccountBudgetCurrentWireV1,
    AccountBudgetFundsWireV1,
    BudgetCloudResourceCurrentWireV1,
    BudgetCollectionStateWireV1,
    BudgetCostBucketWireV1,
    BudgetDimensionWireV1,
    BudgetFundComponentWireV1,
    BudgetPeriodWireV1,
    BudgetReportedSpendWireV1,
    BudgetReportSelectionWireV1,
    BudgetReportWireV1,
    BudgetResourceCurrentWireV1,
    BudgetUsageBucketWireV1,
    ExactMoneyFieldWireV1,
    ExactMoneyWireV1,
)
from agentmonitor.api.v1.schemas.capacity import (
    CapacityObservationProvenanceWireV1,
    CapacitySubjectWireV2,
    ExactQuantityWireV1,
)
from agentmonitor.api.v1.schemas.registry import BillingConnectionViewV1
from agentmonitor.api.v1.serialization import technical_wire
from agentmonitor.contracts.budget_query_v1 import (
    AccountBudgetCurrentV1,
    AccountBudgetFundsV1,
)
from agentmonitor.contracts.capacity_v1 import (
    BudgetPeriodV1,
    BudgetReportViewV1,
    ExactMoneyFieldV1,
)
from agentmonitor.contracts.common_quantity_v1 import ExactMoneyV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.capacity.application.queries import CapacityQueryUnavailableV1
from fastapi import APIRouter, Query, Request

router = APIRouter(tags=["budgets"])


def _period(item: BudgetPeriodV1) -> BudgetPeriodWireV1:
    return BudgetPeriodWireV1(start=item.start, end=item.end)


def _money(item: ExactMoneyV1) -> ExactMoneyWireV1:
    return ExactMoneyWireV1(
        coefficient=item.amount.coefficient,
        scale=item.amount.scale,
        currency=item.currency,
    )


def report_wire(item: BudgetReportViewV1) -> BudgetReportWireV1:
    """Pure allowlisted mapping; no custody fields or recalculated amounts."""
    report = item.report
    return BudgetReportWireV1(
        report_id=item.report_id.value,
        account_id=report.subject.account_id.value,
        resource_id=report.subject.resource_id.value,
        provider_key=report.subject.provider_key,
        scope_generation=report.scope_generation,
        scope_id=None if report.scope_id is None else report.scope_id.value,
        scope_evidence=report.scope_evidence,
        source_id=report.source_id,
        source_category=report.source_category,
        cost_basis=report.cost_basis,
        grouping=list(report.grouping),
        requested_period=_period(report.requested_period),
        covered_period=None
        if report.covered_period is None
        else _period(report.covered_period),
        source_data_through=report.source_data_through,
        collected_at=report.collected_at,
        stored_at=item.stored_at,
        completeness=report.completeness,
        omission_codes=list(report.omission_codes),
        currency=report.currency,
        empty_means_zero=report.empty_means_zero,
        cost_buckets=[
            BudgetCostBucketWireV1(
                bucket_key=row.bucket_key,
                period=_period(row.period),
                amount=_money(row.amount),
                kind=row.kind,
                dimensions=[
                    BudgetDimensionWireV1(kind=d.kind, value=d.value)
                    for d in row.dimensions
                ],
            )
            for row in report.cost_buckets
        ],
        usage_buckets=[
            BudgetUsageBucketWireV1(
                bucket_key=row.bucket_key,
                period=_period(row.period),
                quantity=ExactQuantityWireV1(
                    coefficient=row.quantity.amount.coefficient,
                    scale=row.quantity.amount.scale,
                    unit=row.quantity.unit,
                ),
                dimensions=[
                    BudgetDimensionWireV1(kind=d.kind, value=d.value)
                    for d in row.dimensions
                ],
            )
            for row in report.usage_buckets
        ],
    )


def _money_field(item: ExactMoneyFieldV1) -> ExactMoneyFieldWireV1:
    return ExactMoneyFieldWireV1(
        availability=item.availability.state,
        value=None if item.value is None else _money(item.value),
        precision=item.precision,
        confidence=item.confidence,
        value_kind=item.value_kind,
        reason_code=item.reason_code,
    )


def funds_wire(item: AccountBudgetFundsV1) -> AccountBudgetFundsWireV1:
    return AccountBudgetFundsWireV1(
        account_id=item.account_id.value,
        as_of=item.as_of,
        availability=availability(item.availability),
        registry_revision=item.registry_revision,
        components=[
            BudgetFundComponentWireV1(
                subject=CapacitySubjectWireV2(
                    provider_key=c.subject.provider_key,
                    provider_target_kind="cloud_service",
                    provider_target_id=c.subject.provider_target.target_id.value,
                    account_id=c.subject.account_id.value,
                    resource_id=c.subject.resource_id.value,
                ),
                component_id=c.component_id.value,
                kind=c.kind,
                remaining=_money_field(c.remaining),
                limit=_money_field(c.limit),
                period=None if c.period is None else _period(c.period),
                renewal_at=c.renewal_at,
                expires_at=c.expires_at,
                is_constraining=c.is_constraining,
                scope_evidence=c.scope_evidence,
                observation_id=c.observation_id.value,
                collection_run_id=c.collection_run_id.value,
                observed_at=c.observed_at,
                collected_at=c.collected_at,
                stored_at=c.stored_at,
                freshness=c.freshness,
                completeness=c.completeness,
                provenance=CapacityObservationProvenanceWireV1.model_validate(
                    technical_wire(c.provenance)
                ),
            )
            for c in item.components
        ],
    )


def account_wire(item: AccountBudgetCurrentV1) -> AccountBudgetCurrentWireV1:
    resources = []
    for resource in item.resources:
        run = resource.latest_collection
        resources.append(
            BudgetResourceCurrentWireV1(
                connection=BillingConnectionViewV1.model_validate(
                    technical_wire(resource.connection)
                ),
                reports=[
                    BudgetReportSelectionWireV1(
                        current=None
                        if row.current is None
                        else report_wire(row.current),
                        latest_attempt=None
                        if row.latest_attempt is None
                        else report_wire(row.latest_attempt),
                    )
                    for row in resource.reports
                ],
                report_availability=availability(resource.report_availability),
                reported_spend=[
                    BudgetReportedSpendWireV1(
                        report_id=row.report_id.value,
                        total=None if row.total is None else _money(row.total),
                        reason_code=row.reason_code,
                    )
                    for row in resource.reported_spend
                ],
                latest_collection=None
                if run is None
                else BudgetCollectionStateWireV1(
                    run_id=run.run_id.value,
                    state=run.state,
                    source_id=run.source_id,
                    requested_at=run.requested_at,
                    started_at=run.started_at,
                    completed_at=run.completed_at,
                    outcome_code=run.outcome_code,
                    error_code=run.error_code,
                    report_id=None if run.report_id is None else run.report_id.value,
                ),
                collection_availability=availability(resource.collection_availability),
            )
        )
    cloud_resources = []
    for cloud in item.cloud_resources:
        run = cloud.latest_collection
        cloud_resources.append(
            BudgetCloudResourceCurrentWireV1(
                account_id=cloud.target.account_id.value,
                resource_id=cloud.target.resource_id.value,
                lifecycle=cloud.target.lifecycle,
                reports=[
                    BudgetReportSelectionWireV1(
                        current=None
                        if row.current is None
                        else report_wire(row.current),
                        latest_attempt=None
                        if row.latest_attempt is None
                        else report_wire(row.latest_attempt),
                    )
                    for row in cloud.reports
                ],
                report_availability=availability(cloud.report_availability),
                reported_spend=[
                    BudgetReportedSpendWireV1(
                        report_id=row.report_id.value,
                        total=None if row.total is None else _money(row.total),
                        reason_code=row.reason_code,
                    )
                    for row in cloud.reported_spend
                ],
                latest_collection=None
                if run is None
                else BudgetCollectionStateWireV1(
                    run_id=run.run_id.value,
                    state=run.state,
                    source_id=run.source_id,
                    requested_at=run.requested_at,
                    started_at=run.started_at,
                    completed_at=run.completed_at,
                    outcome_code=run.outcome_code,
                    error_code=run.error_code,
                    report_id=None if run.report_id is None else run.report_id.value,
                ),
                collection_availability=availability(cloud.collection_availability),
            )
        )
    return AccountBudgetCurrentWireV1(
        account_id=item.account_id.value,
        period=_period(item.period),
        as_of=item.as_of,
        availability=availability(item.availability),
        resources=resources,
        funds=None if item.funds is None else funds_wire(item.funds),
        cloud_resources=cloud_resources,
    )


@router.get(
    "/accounts/{account_id}/api-capacity",
    operation_id="capacity_get_account_api_budget_v1",
    response_model=AccountBudgetCurrentWireV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:telemetry", "AccountBudgetCurrentPortV1"),
)
def get_account_budget(
    account_id: str,
    request: Request,
    period_start: Annotated[
        datetime, Query(description="Inclusive UTC reporting start.")
    ],
    period_end: Annotated[datetime, Query(description="Exclusive UTC reporting end.")],
    as_of: Annotated[
        datetime, Query(description="Pinned UTC read instant; no provider collection.")
    ],
) -> AccountBudgetCurrentWireV1:
    authorize_request(request, "read:telemetry")
    reject_unknown_query(request, frozenset({"period_start", "period_end", "as_of"}))
    require_opaque_selector(account_id)
    if (
        any(
            value.utcoffset() != UTC.utcoffset(value)
            for value in (period_start, period_end, as_of)
        )
        or not period_start < period_end <= as_of
    ):
        raise ProblemError(400, "invalid_filter")
    port = observation_ports(request).get_account_budget_current
    if port is None:
        raise ProblemError(503, "observation_data_unavailable")
    try:
        item = port(
            OpaqueIdV1(account_id),
            period=BudgetPeriodV1(period_start, period_end),
            as_of=as_of,
        )
    except CapacityQueryUnavailableV1:
        raise ProblemError(503, "observation_repository_unavailable") from None
    if item is None:
        raise ProblemError(404, "registry_subject_not_found")
    return account_wire(item)

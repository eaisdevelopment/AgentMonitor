"""Read the first cloud budget journey in its exact self-report context."""

from datetime import datetime, timedelta

from agentmonitor.contracts.budget_query_v1 import (
    BudgetCloudResourceCurrentV1,
    BudgetCollectionStatePortV1,
)
from agentmonitor.contracts.capacity_v1 import (
    BudgetCurrentQueryV1,
    BudgetCurrentReportsPortV1,
    BudgetPeriodV1,
    BudgetReportSelectionV1,
)
from agentmonitor.contracts.collection_control_v1 import CloudBudgetReportContextV1
from agentmonitor.contracts.common_v1 import QueryAvailabilityV1
from agentmonitor.contracts.registry_v1 import CloudMonitoringTargetV1
from agentmonitor.modules.capacity.domain.budget_account_spend import reported_spend


def visible_cloud_reports(
    selections: tuple[BudgetReportSelectionV1, ...],
) -> tuple[BudgetReportSelectionV1, ...]:
    return tuple(
        selection
        for selection in selections
        if (view := selection.latest_attempt or selection.current) is not None
        and view.report.source_category
        in {"self_requests_and_cost", "team_requests_and_cost"}
    )


def default_cloud_spend_reports(
    selections: tuple[BudgetReportSelectionV1, ...],
) -> tuple[BudgetReportSelectionV1, ...]:
    return tuple(
        selection
        for selection in selections
        if (view := selection.latest_attempt or selection.current) is not None
        and view.report.source_category == "self_requests_and_cost"
        and not view.report.grouping
    )


def cloud_budget_current(
    target: CloudMonitoringTargetV1,
    reports: BudgetCurrentReportsPortV1,
    collection: BudgetCollectionStatePortV1,
    *,
    period: BudgetPeriodV1,
    as_of: datetime,
) -> BudgetCloudResourceCurrentV1:
    try:
        context = CloudBudgetReportContextV1(
            "self",
            "7d" if period.end - period.start == timedelta(days=7) else "30d",
            period.start,
            period.end,
        )
    except ValueError:
        unavailable = QueryAvailabilityV1(
            "unavailable", "budget_cloud_context_unavailable", as_of
        )
        return BudgetCloudResourceCurrentV1(
            target, (), unavailable, (), None, unavailable
        )
    # Scope epoch 1 belongs to the canonical resource; the unresolved report
    # selector separately requires this exact credential lineage.
    result = reports.get_current_reports(
        BudgetCurrentQueryV1(
            target.account_id,
            target.resource_id,
            1,
            period,
            as_of,
            active_binding=target.binding,
        )
    )
    selected = visible_cloud_reports(result.items)
    try:
        latest = collection.get_latest_budget_run(
            target.account_id,
            target.resource_id,
            1,
            as_of,
            report_context=context,
        )
        collection_availability = QueryAvailabilityV1(
            "available",
            "budget_collection_read" if latest else "budget_collection_not_started",
            as_of,
        )
    except ValueError:
        latest = None
        collection_availability = QueryAvailabilityV1(
            "unavailable", "budget_collection_query_unavailable", as_of
        )
    return BudgetCloudResourceCurrentV1(
        target,
        selected,
        QueryAvailabilityV1("unavailable", "budget_current_reports_absent", as_of)
        if not selected and result.availability.state == "available"
        else result.availability,
        tuple(
            value
            for selection in default_cloud_spend_reports(selected)
            if (value := reported_spend(selection)) is not None
        ),
        latest,
        collection_availability,
    )

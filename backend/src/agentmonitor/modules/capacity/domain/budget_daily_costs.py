"""Exact daily chart inputs from one pinned report, without time prorating."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from agentmonitor.contracts.budget_query_v1 import BudgetSelectedReportV1
from agentmonitor.contracts.capacity_v1 import BudgetCostBucketV1, BudgetPeriodV1
from agentmonitor.contracts.common_quantity_v1 import CanonicalDecimalV1, ExactMoneyV1
from agentmonitor.modules.capacity.domain.budget_money import (
    BudgetMoneyError,
    sum_money,
)


@dataclass(frozen=True, slots=True)
class BudgetDailyCost:
    period: BudgetPeriodV1
    amount: ExactMoneyV1
    input_bucket_keys: tuple[str, ...]
    has_adjustment: bool
    derived_zero: bool = False


@dataclass(frozen=True, slots=True)
class BudgetDailyCosts:
    selected: BudgetSelectedReportV1
    days: tuple[BudgetDailyCost, ...]
    reason: str | None


def _utc(value: datetime) -> bool:
    return value.utcoffset() == timedelta(0)


def _midnight(value: datetime) -> bool:
    return _utc(value) and not any(
        (value.hour, value.minute, value.second, value.microsecond)
    )


def daily_costs(
    selected: BudgetSelectedReportV1,
    *,
    disjoint_costs: bool = False,
    zero_day_coverage: bool = False,
) -> BudgetDailyCosts:
    """Source admission supplies disjointness and sparse-day zero evidence.

    A grouping label never proves that its rows partition a daily total. Unknown
    omitted days stay absent. Derived zeros cite the original coverage receipt;
    they are calculation inputs, never new stored provider observations.
    """
    view = selected.report
    report = view.report
    period = report.requested_period
    if (
        type(disjoint_costs) is not bool
        or type(zero_day_coverage) is not bool
        or not _utc(selected.as_of)
        or not _midnight(period.start)
        or not _midnight(period.end)
        or not timedelta(days=1) <= period.end - period.start <= timedelta(days=30)
        or selected.reported_spend.report_id != view.report_id
        or view.stored_at > selected.as_of
        or period.end > selected.as_of
    ):
        raise ValueError("budget_daily_context_invalid")
    reason = (
        "report_incomplete"
        if report.completeness != "complete"
        else "report_coverage_incomplete"
        if report.covered_period != period
        else None
    )
    if report.currency is None:
        return BudgetDailyCosts(selected, (), "currency_unavailable")
    if report.grouping and not disjoint_costs:
        return BudgetDailyCosts(selected, (), "cost_disjointness_unproven")
    groups: dict[datetime, list[BudgetCostBucketV1]] = {}
    for bucket in report.cost_buckets:
        if not _midnight(
            bucket.period.start
        ) or bucket.period.end - bucket.period.start != timedelta(days=1):
            return BudgetDailyCosts(selected, (), "cost_bucket_not_daily")
        groups.setdefault(bucket.period.start, []).append(bucket)
    if not disjoint_costs and any(len(rows) > 1 for rows in groups.values()):
        return BudgetDailyCosts(selected, (), "cost_disjointness_unproven")
    fill_zero = reason is None and (
        not report.cost_buckets
        and report.empty_means_zero
        or zero_day_coverage
        and report.source_data_through is not None
        and report.source_data_through >= period.end
    )
    if not groups and not fill_zero:
        return BudgetDailyCosts(selected, (), reason or "cost_not_reported")
    if fill_zero:
        for day in range((period.end - period.start).days):
            groups.setdefault(period.start + timedelta(days=day), [])
    days: list[BudgetDailyCost] = []
    try:
        for start, rows in sorted(groups.items()):
            days.append(
                BudgetDailyCost(
                    BudgetPeriodV1(start, start + timedelta(days=1)),
                    sum_money(tuple(row.amount for row in rows))
                    if rows
                    else ExactMoneyV1(CanonicalDecimalV1("0", 0), report.currency),
                    tuple(sorted(row.bucket_key for row in rows)),
                    any(row.kind == "adjustment" for row in rows),
                    not rows,
                )
            )
    except BudgetMoneyError:
        return BudgetDailyCosts(selected, (), "cost_total_unavailable")
    return BudgetDailyCosts(selected, tuple(days), reason)

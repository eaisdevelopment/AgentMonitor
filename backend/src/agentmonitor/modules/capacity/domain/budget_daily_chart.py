"""Bounded derived daily bars over one exact immutable financial selection."""

import hashlib
import json
from dataclasses import dataclass

from agentmonitor.contracts.budget_forecast_v1 import BudgetSourceEvidenceV1
from agentmonitor.contracts.budget_query_v1 import (
    BudgetHistoryChartPointV1,
    BudgetSelectedReportV1,
)
from agentmonitor.modules.capacity.domain.budget_daily_costs import (
    BudgetDailyCost,
    daily_costs,
)


@dataclass(frozen=True, slots=True)
class BudgetDailyChartPoint:
    day: BudgetDailyCost
    chart: BudgetHistoryChartPointV1


@dataclass(frozen=True, slots=True)
class BudgetDailyChart:
    selected: BudgetSelectedReportV1
    points: tuple[BudgetDailyChartPoint, ...]
    reason: str | None
    source_evidence: BudgetSourceEvidenceV1 | None


def daily_chart(
    selected: BudgetSelectedReportV1,
    *,
    evidence: BudgetSourceEvidenceV1 | None = None,
) -> BudgetDailyChart:
    """Normalize once before geometry; no source-page or forecast-sample inputs.

    The existing daily policy owns exact sums, coverage, UTC bounds and zeros.
    Signed adjustments remain chartable even when they disqualify a forecast.
    Partial coverage retains actual normalized days and its original reason.
    """
    if evidence is not None and evidence.report_id != selected.report.report_id:
        raise ValueError("budget_source_evidence_context_invalid")
    daily = daily_costs(
        selected,
        disjoint_costs=evidence.disjoint_costs if evidence else False,
        zero_day_coverage=evidence.zero_day_coverage if evidence else False,
    )
    if evidence is None:
        return BudgetDailyChart(selected, (), "source_semantics_unavailable", None)
    report = selected.report.report
    # This is only a display-series key, never a new provider observation ID.
    key = hashlib.sha256(
        json.dumps(
            (
                "daily_cost",
                report.source_id,
                report.source_category,
                report.cost_basis,
                report.grouping,
                report.currency,
            ),
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    signed = tuple(
        int(day.amount.amount.coefficient) * 10 ** (18 - day.amount.amount.scale)
        for day in daily.days
    )
    maximum = max((abs(value) for value in signed), default=0)
    points = tuple(
        BudgetDailyChartPoint(
            day,
            BudgetHistoryChartPointV1(
                key,
                f"Daily cost · {day.amount.currency}",
                (abs(value) * 10000 + maximum - 1) // maximum if maximum else 0,
                "zero" if value == 0 else "negative" if value < 0 else "positive",
            ),
        )
        for day, value in zip(daily.days, signed, strict=True)
    )
    return BudgetDailyChart(selected, points, daily.reason, evidence)

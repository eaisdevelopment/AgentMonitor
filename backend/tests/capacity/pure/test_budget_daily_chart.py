"""T013 daily bars use exact derived facts, never source-row heights or I/O."""

from dataclasses import replace
from datetime import timedelta
from decimal import localcontext

import pytest
from agentmonitor.contracts.budget_forecast_v1 import BudgetSourceEvidenceV1
from agentmonitor.contracts.budget_query_v1 import (
    BudgetHistoryQueryV1,
    BudgetSelectedReportV1,
)
from agentmonitor.contracts.capacity_v1 import (
    BudgetPeriodV1,
    BudgetReportSelectionV1,
    BudgetUsageBucketV1,
)
from agentmonitor.contracts.common_quantity_v1 import (
    CanonicalDecimalV1,
    ExactQuantityV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.capacity.domain.budget_account_spend import reported_spend
from agentmonitor.modules.capacity.domain.budget_history import history_result

from backend.tests.capacity.pure.test_budget_daily_costs import (
    START,
    _money,
    _selected,
    _with_view,
)


def _evidence(selected: BudgetSelectedReportV1) -> BudgetSourceEvidenceV1:
    return BudgetSourceEvidenceV1(
        selected.report.report_id, "pure-daily-policy", "1.0.0", True, True, False, None
    )


def test_same_day_disjoint_facts_become_one_exact_bar_with_original_inputs() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_chart import daily_chart

    selected = _selected(((4, "1"), (4, "1"), (5, "4"), (6, "1")), grouped=True)
    result = daily_chart(selected, evidence=_evidence(selected))
    assert result.selected == selected
    assert result.source_evidence == _evidence(selected)
    assert result.reason is None
    assert [point.day.amount for point in result.points] == [
        _money("2"),
        _money("4"),
        _money("1"),
    ]
    assert result.points[0].day.input_bucket_keys == ("cost-0", "cost-1")
    assert [point.chart.magnitude_basis_points for point in result.points] == [
        5000,
        10000,
        2500,
    ]
    assert len({point.chart.series_key for point in result.points}) == 1


@pytest.mark.parametrize("grouped", (False, True))
def test_grouping_or_overlapping_rows_without_disjoint_evidence_are_unavailable(
    grouped: bool,
) -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_chart import daily_chart

    if not grouped:
        # The published report contract rejects same-context overlap before M05.
        with pytest.raises(ValueError, match="budget_overlapping_buckets"):
            _selected(((4, "10"), (4, "6")))
        return
    selected = _selected(((4, "10"), (4, "6")), grouped=grouped)
    result = daily_chart(
        selected, evidence=replace(_evidence(selected), disjoint_costs=False)
    )
    assert result.points == ()
    assert result.reason == "cost_disjointness_unproven"


def test_missing_or_other_report_evidence_cannot_enable_daily_totals() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_chart import daily_chart

    selected = _selected()
    result = daily_chart(selected)
    assert result.points == ()
    assert result.reason == "source_semantics_unavailable"
    with pytest.raises(ValueError, match="budget_source_evidence_context_invalid"):
        daily_chart(
            selected,
            evidence=replace(_evidence(selected), report_id=OpaqueIdV1("other-report")),
        )


@pytest.mark.parametrize(
    "amount,direction", (("-2", "negative"), ("2", "positive"), ("0", "zero"))
)
def test_signed_adjustments_keep_exact_amount_and_direction(
    amount: str,
    direction: str,
) -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_chart import daily_chart

    selected = _selected(((4, amount),), adjustments=True)
    result = daily_chart(selected, evidence=_evidence(selected))
    assert result.reason is None
    assert result.points[0].day.amount == _money(amount)
    assert result.points[0].day.has_adjustment
    assert result.points[0].chart.direction == direction


def test_missing_days_stay_absent_and_partial_report_keeps_actual_points() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_chart import daily_chart

    selected = _selected(((4, "2"), (6, "4")))
    selected = _with_view(
        replace(
            selected.report,
            report=replace(
                selected.report.report,
                completeness="partial",
                omission_codes=("page_missing",),
            ),
        )
    )
    result = daily_chart(selected, evidence=_evidence(selected))
    assert result.reason == "report_incomplete"
    assert [point.day.period.start for point in result.points] == [
        START + timedelta(days=4),
        START + timedelta(days=6),
    ]
    assert not any(point.day.derived_zero for point in result.points)


def test_counts_only_are_not_monetary_zero_days() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_chart import daily_chart

    selected = _selected(())
    usage = BudgetUsageBucketV1(
        "requests",
        BudgetPeriodV1(START, START + timedelta(days=1)),
        ExactQuantityV1(CanonicalDecimalV1("7", 0), "requests"),
        (),
    )
    selected = _with_view(
        replace(
            selected.report,
            report=replace(selected.report.report, usage_buckets=(usage,)),
        )
    )
    result = daily_chart(selected, evidence=_evidence(selected))
    assert result.reason == "cost_not_reported"
    assert result.points == ()


def test_qualified_empty_zero_retains_derived_flag_without_invented_source_keys() -> (
    None
):
    from agentmonitor.modules.capacity.domain.budget_daily_chart import daily_chart

    selected = _selected(())
    selected = _with_view(
        replace(
            selected.report,
            report=replace(selected.report.report, empty_means_zero=True),
        )
    )
    result = daily_chart(selected, evidence=_evidence(selected))
    assert result.reason is None and len(result.points) == 7
    assert all(
        point.day.derived_zero
        and point.day.input_bucket_keys == ()
        and point.chart.direction == "zero"
        and point.day.amount == _money("0")
        for point in result.points
    )


def test_geometry_preserves_tiny_nonzero_exact_amount_without_decimal_context() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_chart import daily_chart

    selected = _selected(((4, "9" * 78), (5, "0.000000000000000001"), (6, "0")))
    with localcontext() as context:
        context.prec = 2
        result = daily_chart(selected, evidence=_evidence(selected))
    assert [point.chart.magnitude_basis_points for point in result.points] == [
        10000,
        1,
        0,
    ]
    assert result.points[1].day.amount == _money("0.000000000000000001")


def test_source_fact_pages_cannot_change_full_daily_totals_or_scale() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_chart import daily_chart

    selected = _selected(((4, "1"), (4, "1"), (5, "4"), (6, "1")), grouped=True)
    subject = selected.report.report.subject
    query = BudgetHistoryQueryV1(
        subject.account_id,
        subject.resource_id,
        selected.report.report_id,
        selected.report.report.requested_period,
        selected.as_of,
        limit=1,
    )
    first = history_result(selected, query)
    whole = history_result(selected, replace(query, limit=200))
    assert len(first.page.items) == 1 and len(whole.page.items) == 4
    result = daily_chart(selected, evidence=_evidence(selected))
    assert len(result.points) == 3
    assert result.points[0].day.amount == _money("2")
    assert result.points[0].chart.magnitude_basis_points == 5000
    assert daily_chart(selected, evidence=_evidence(selected)) == result


@pytest.mark.parametrize("days", (30, 31))
def test_full_daily_series_is_bounded_to_thirty_days_and_sorted(days: int) -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_chart import daily_chart

    selected = _selected(((0, "1"),))
    period = BudgetPeriodV1(START, START + timedelta(days=days))
    as_of = period.end + timedelta(hours=12)
    base = selected.report.report.cost_buckets[0]
    buckets = tuple(
        replace(
            base,
            bucket_key=f"day-{day}",
            period=BudgetPeriodV1(
                START + timedelta(days=day), START + timedelta(days=day + 1)
            ),
        )
        for day in reversed(range(days))
    )
    view = replace(
        selected.report,
        stored_at=as_of,
        report=replace(
            selected.report.report,
            requested_period=period,
            covered_period=period,
            collected_at=as_of,
            source_data_through=period.end,
            cost_buckets=buckets,
        ),
    )
    spend = reported_spend(BudgetReportSelectionV1(view, view))
    assert spend is not None
    selected = BudgetSelectedReportV1(view, spend, as_of)
    if days == 31:
        with pytest.raises(ValueError, match="budget_daily_context_invalid"):
            daily_chart(selected, evidence=_evidence(selected))
        return
    result = daily_chart(selected, evidence=_evidence(selected))
    assert result.reason is None and len(result.points) == 30
    assert [point.day.period.start for point in result.points] == [
        START + timedelta(days=day) for day in range(30)
    ]


def test_history_projects_all_daily_totals_independently_of_source_page() -> None:
    selected = _selected(((4, "1"), (4, "1"), (5, "4"), (6, "1")), grouped=True)
    subject = selected.report.report.subject
    query = BudgetHistoryQueryV1(
        subject.account_id,
        subject.resource_id,
        selected.report.report_id,
        selected.report.report.requested_period,
        selected.as_of,
        limit=1,
    )
    first = history_result(selected, query, evidence=_evidence(selected))
    whole = history_result(
        selected, replace(query, limit=200), evidence=_evidence(selected)
    )
    assert first.daily_costs == whole.daily_costs
    daily = first.daily_costs
    assert daily is not None and daily.state == "available"
    assert daily.reason_code == "daily_costs_calculated"
    assert daily.policy_id == "pure-daily-policy"
    assert [row.amount for row in daily.items] == [
        _money("2"),
        _money("4"),
        _money("1"),
    ]
    assert [row.source_entry_count for row in daily.items] == [2, 1, 1]
    assert len(first.page.items) == 1
    assert len(whole.page.items) == 4


def test_history_without_source_semantics_exposes_reason_not_zero_totals() -> None:
    selected = _selected()
    subject = selected.report.report.subject
    query = BudgetHistoryQueryV1(
        subject.account_id,
        subject.resource_id,
        selected.report.report_id,
        selected.report.report.requested_period,
        selected.as_of,
    )
    daily = history_result(selected, query).daily_costs
    assert daily is not None and daily.state == "unavailable"
    assert daily.reason_code == "source_semantics_unavailable"
    assert daily.items == ()
    assert daily.policy_id is None and daily.policy_version is None

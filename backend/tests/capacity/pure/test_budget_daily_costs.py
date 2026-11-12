"""T013 daily cost policy: constructed exact values, no I/O boundaries."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext

import pytest
from agentmonitor.contracts.budget_query_v1 import BudgetSelectedReportV1
from agentmonitor.contracts.capacity_v1 import (
    BudgetCostBucketV1,
    BudgetDimensionV1,
    BudgetPeriodV1,
    BudgetReportSelectionV1,
    BudgetReportViewV1,
)
from agentmonitor.contracts.common_quantity_v1 import CanonicalDecimalV1, ExactMoneyV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.capacity.domain.budget_account_spend import reported_spend

from backend.tests.capacity.pure.test_budget_report_selection import _report

START = datetime(2026, 11, 1, tzinfo=UTC)
END = START + timedelta(days=7)
AS_OF = END + timedelta(hours=12)


def _money(value: str, currency: str = "USD") -> ExactMoneyV1:
    return ExactMoneyV1(CanonicalDecimalV1.from_decimal(Decimal(value)), currency)


def _selected(
    values: tuple[tuple[int, str], ...] = ((4, "2"), (5, "2"), (6, "2")),
    *,
    grouped: bool = False,
    adjustments: bool = False,
) -> BudgetSelectedReportV1:
    old = _report(1, "1")
    rows = tuple(
        BudgetCostBucketV1(
            f"cost-{index}",
            BudgetPeriodV1(
                START + timedelta(days=day), START + timedelta(days=day + 1)
            ),
            _money(value),
            (BudgetDimensionV1("model", f"model-{index}"),) if grouped else (),
            "adjustment" if adjustments else "charge",
        )
        for index, (day, value) in enumerate(values)
    )
    payload = replace(
        old.report,
        requested_period=BudgetPeriodV1(START, END),
        covered_period=BudgetPeriodV1(START, END),
        collected_at=AS_OF,
        source_data_through=END,
        empty_means_zero=False,
        grouping=("model",) if grouped else (),
        cost_buckets=rows,
    )
    return _with_view(replace(old, report=payload, stored_at=AS_OF))


def _with_view(view: BudgetReportViewV1) -> BudgetSelectedReportV1:
    spend = reported_spend(BudgetReportSelectionV1(view, view))
    assert spend is not None
    return BudgetSelectedReportV1(view, spend, AS_OF)


def test_disjoint_model_costs_sum_once_per_day_and_retain_inputs() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs

    selected = _selected(tuple((day, "1") for day in (4, 4, 5, 5, 6, 6)), grouped=True)
    result = daily_costs(selected, disjoint_costs=True)
    assert result.reason is None
    assert result.selected == selected
    assert [point.amount for point in result.days] == [_money("2")] * 3
    assert [len(point.input_bucket_keys) for point in result.days] == [2, 2, 2]
    assert all(
        not point.derived_zero and not point.has_adjustment for point in result.days
    )


def test_grouping_names_do_not_establish_disjointness() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs

    selected = _selected(((4, "2"), (4, "1")), grouped=True)
    result = daily_costs(selected)
    assert result.reason == "cost_disjointness_unproven"
    assert result.days == ()


@pytest.mark.parametrize("value", ("-2", "2", "0"))
def test_signed_adjustments_remain_chart_values(value: str) -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs

    result = daily_costs(_selected(((4, value),), adjustments=True))
    assert result.days[0].amount == _money(value)
    assert result.days[0].has_adjustment


def test_charge_and_distinct_adjustment_are_added_exactly_once() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs

    selected = _selected(((4, "10"),))
    report = selected.report
    charge = report.report.cost_buckets[0]
    adjustment = replace(
        charge, bucket_key="adjustment", kind="adjustment", amount=_money("-2")
    )
    selected = _with_view(
        replace(
            report, report=replace(report.report, cost_buckets=(charge, adjustment))
        )
    )
    result = daily_costs(selected, disjoint_costs=True)
    assert result.days[0].amount == _money("8")
    assert result.days[0].input_bucket_keys == ("adjustment", "cost-0")


def test_replaced_selected_report_does_not_accumulate_prior_revision() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs

    old = _selected(((4, "8"),))
    newer = _selected(((4, "6"),))
    newer = _with_view(replace(newer.report, report_id=OpaqueIdV1("new-report")))
    assert daily_costs(old).days[0].amount == _money("8")
    assert daily_costs(newer).days[0].amount == _money("6")
    assert daily_costs(newer) == daily_costs(newer)


@pytest.mark.parametrize("qualified", (False, True))
def test_complete_empty_zero_requires_admitted_monetary_semantics(
    qualified: bool,
) -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs

    selected = _selected(())
    selected = _with_view(
        replace(
            selected.report,
            report=replace(selected.report.report, empty_means_zero=qualified),
        )
    )
    result = daily_costs(selected)
    assert len(result.days) == (7 if qualified else 0)
    assert result.reason == (None if qualified else "cost_not_reported")
    assert all(
        p.amount == _money("0") and p.derived_zero and not p.input_bucket_keys
        for p in result.days
    )


def test_missing_day_is_not_filled_without_explicit_source_evidence() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs

    selected = _selected(((4, "2"), (6, "2")))
    assert len(daily_costs(selected).days) == 2
    result = daily_costs(selected, zero_day_coverage=True)
    assert len(result.days) == 7
    assert result.days[5].derived_zero


def test_partial_report_keeps_exact_chart_facts_but_not_complete_coverage() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs

    selected = _selected()
    payload = replace(
        selected.report.report, completeness="partial", omission_codes=("missing_page",)
    )
    result = daily_costs(
        _with_view(replace(selected.report, report=payload)), zero_day_coverage=True
    )
    assert result.reason == "report_incomplete"
    assert len(result.days) == 3
    assert all(not point.derived_zero for point in result.days)


def test_partial_day_is_not_prorated_into_a_daily_amount() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs

    selected = _selected(((4, "2"),))
    original = selected.report.report.cost_buckets[0]
    bucket = replace(
        original,
        period=BudgetPeriodV1(
            original.period.start, original.period.end - timedelta(hours=1)
        ),
    )
    payload = replace(selected.report.report, cost_buckets=(bucket,))
    result = daily_costs(_with_view(replace(selected.report, report=payload)))
    assert result.reason == "cost_bucket_not_daily"
    assert result.days == ()


@pytest.mark.parametrize("invalid", ("report_id", "future", "naive_as_of"))
def test_daily_projection_rejects_invalid_pinned_selection(invalid: str) -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs

    selected = _selected()
    reason = (
        "timestamp-must-be-aware-utc"
        if invalid == "naive_as_of"
        else "budget_daily_context_invalid"
    )
    with pytest.raises(ValueError, match=reason):
        if invalid == "report_id":
            selected = replace(
                selected,
                reported_spend=replace(
                    selected.reported_spend, report_id=OpaqueIdV1("other")
                ),
            )
        else:
            selected = replace(
                selected,
                as_of=START if invalid == "future" else AS_OF.replace(tzinfo=None),
            )
        daily_costs(selected)


def test_daily_sums_are_independent_of_decimal_precision() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs

    selected = _selected(
        ((4, "123456789012345678901234567890.1"), (4, "0.2")), grouped=True
    )
    with localcontext() as context:
        context.prec = 3
        result = daily_costs(selected, disjoint_costs=True)
    assert result.days[0].amount == _money("123456789012345678901234567890.3")


def test_daily_sum_overflow_is_unavailable_without_partial_total() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs

    selected = _selected(((4, "9" * 78), (4, "9" * 78)), grouped=True)
    result = daily_costs(selected, disjoint_costs=True)
    assert result.reason == "cost_total_unavailable"
    assert result.days == ()

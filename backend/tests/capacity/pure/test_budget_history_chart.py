"""Exact chart geometry is derived from the same immutable source facts."""

from dataclasses import replace
from datetime import timedelta

from agentmonitor.contracts.budget_query_v1 import (
    BudgetHistoryChartPointV1,
    BudgetHistoryRowV1,
)
from agentmonitor.contracts.capacity_v1 import BudgetDimensionV1, BudgetPeriodV1
from agentmonitor.contracts.common_quantity_v1 import CanonicalDecimalV1
from agentmonitor.modules.capacity.domain.budget_history import history_result

from backend.tests.capacity.pure.test_budget_daily_history import (
    _query,
    _selected,
    _with_report,
)


def _point(row: BudgetHistoryRowV1) -> BudgetHistoryChartPointV1:
    assert row.chart is not None
    return row.chart


def test_chart_scale_uses_whole_report_and_preserves_signed_exact_facts() -> None:
    selected = _selected()
    first = history_result(selected, _query(selected, limit=1))
    whole = history_result(selected, _query(selected, limit=200))
    assert first.page.items[0].chart == whole.page.items[0].chart
    assert _point(first.page.items[0]).magnitude_basis_points == 10000
    costs = [row for row in whole.page.items if row.cost is not None]
    assert [_point(row).magnitude_basis_points for row in costs] == [10000, 4000, 10000]
    assert [_point(row).direction for row in costs] == [
        "positive",
        "negative",
        "positive",
    ]
    assert len({_point(row).series_key for row in costs}) == 1
    assert all(_point(row).label == "Cost · USD" for row in costs)
    assert {row.cost for row in costs} == set(selected.report.report.cost_buckets)
    assert len({_point(row).series_key for row in whole.page.items}) == 3


def test_nonzero_geometry_does_not_underflow_and_zero_remains_zero() -> None:
    selected = _selected()
    base = selected.report.report.usage_buckets[0]
    buckets = tuple(
        replace(
            base,
            bucket_key=f"value-{i}",
            quantity=replace(base.quantity, amount=value),
            period=BudgetPeriodV1(
                base.period.start + timedelta(days=i),
                base.period.end + timedelta(days=i),
            ),
        )
        for i, value in enumerate(
            (
                CanonicalDecimalV1("9" * 78, 0),
                CanonicalDecimalV1("1", 18),
                CanonicalDecimalV1("0", 0),
            )
        )
    )
    selected = _with_report(
        replace(
            selected.report,
            report=replace(
                selected.report.report,
                cost_buckets=(),
                usage_buckets=buckets,
            ),
        )
    )
    rows = history_result(selected, _query(selected, limit=200)).page.items
    assert [_point(row).magnitude_basis_points for row in rows] == [10000, 1, 0]
    assert [_point(row).direction for row in rows] == ["positive", "positive", "zero"]


def test_distinct_model_dimensions_have_distinct_scales_not_an_invented_total() -> None:
    selected = _selected()
    base = selected.report.report.usage_buckets[0]
    buckets = tuple(
        replace(
            base,
            bucket_key=f"model-{i}",
            dimensions=(BudgetDimensionV1("model", name),),
            quantity=replace(base.quantity, amount=CanonicalDecimalV1(str(value), 0)),
        )
        for i, (name, value) in enumerate((("one", 1), ("two", 10)))
    )
    selected = _with_report(
        replace(
            selected.report,
            report=replace(
                selected.report.report,
                cost_buckets=(),
                usage_buckets=buckets,
                grouping=("model",),
            ),
        )
    )
    rows = history_result(selected, _query(selected, limit=200)).page.items
    assert len({_point(row).series_key for row in rows}) == 2
    assert all(_point(row).magnitude_basis_points == 10000 for row in rows)
    assert {row.usage for row in rows} == set(buckets)


def test_non_daily_source_period_is_retained_without_a_misleading_daily_bar() -> None:
    selected = _selected()
    base = selected.report.report.usage_buckets[0]
    bucket = replace(
        base,
        period=BudgetPeriodV1(base.period.start, base.period.end + timedelta(days=1)),
    )
    selected = _with_report(
        replace(
            selected.report,
            report=replace(
                selected.report.report,
                cost_buckets=(),
                usage_buckets=(bucket,),
            ),
        )
    )
    row = history_result(selected, _query(selected)).page.items[0]
    assert row.usage == bucket
    assert row.chart is None
    assert row.chart_unavailable_reason == "source_interval_not_daily"

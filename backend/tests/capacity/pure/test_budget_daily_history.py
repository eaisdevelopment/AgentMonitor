"""Pure selected-report facts and pagination; constructed values never enter I/O."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from typing import Any

import pytest
from agentmonitor.contracts import budget_query_v1 as contracts
from agentmonitor.contracts.capacity_v1 import (
    BudgetPeriodV1,
    BudgetReportSelectionV1,
    BudgetReportViewV1,
    BudgetUsageBucketV1,
)
from agentmonitor.contracts.common_quantity_v1 import (
    CanonicalDecimalV1,
    ExactQuantityV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.capacity.domain.budget_account_spend import reported_spend

from backend.tests.capacity.pure.test_budget_report_selection import _report


def _selected(*, days: int = 7) -> contracts.BudgetSelectedReportV1:
    view = _report(1, "1.25")
    start = view.report.requested_period.start
    period = BudgetPeriodV1(start, start + timedelta(days=days))
    costs = tuple(
        replace(
            view.report.cost_buckets[0],
            bucket_key="cost-" + str(day),
            period=BudgetPeriodV1(
                start + timedelta(days=day), start + timedelta(days=day + 1)
            ),
            amount=replace(
                view.report.cost_buckets[0].amount,
                amount=CanonicalDecimalV1("-5", 1)
                if day == 1
                else CanonicalDecimalV1("125", 2),
            ),
            kind="adjustment" if day == 1 else "charge",
        )
        for day in (2, 0, 1)
    )
    usage = tuple(
        BudgetUsageBucketV1(
            "usage-" + unit,
            costs[1].period,
            ExactQuantityV1(CanonicalDecimalV1("9007199254740993", 0), unit),
            (),
        )
        for unit in ("token", "request")
    )
    payload = replace(
        view.report,
        requested_period=period,
        covered_period=period,
        source_data_through=None,
        collected_at=period.end + timedelta(hours=1),
        empty_means_zero=False,
        cost_buckets=costs,
        usage_buckets=usage,
    )
    return _with_report(replace(view, report=payload, stored_at=payload.collected_at))


def _with_report(view: BudgetReportViewV1) -> contracts.BudgetSelectedReportV1:
    spend = reported_spend(
        BudgetReportSelectionV1(
            view if view.report.completeness == "complete" else None, view
        )
    )
    assert spend is not None
    return contracts.BudgetSelectedReportV1(
        view, spend, view.stored_at + timedelta(hours=1)
    )


def _query(
    selected: contracts.BudgetSelectedReportV1, **changes: Any
) -> contracts.BudgetHistoryQueryV1:
    values: dict[str, Any] = {
        "account_id": selected.report.report.subject.account_id,
        "resource_id": selected.report.report.subject.resource_id,
        "report_id": selected.report.report_id,
        "period": selected.report.report.requested_period,
        "as_of": selected.as_of,
        "limit": 1,
    }
    return contracts.BudgetHistoryQueryV1(**(values | changes))


def _row_key(row: contracts.BudgetHistoryRowV1) -> tuple[str, str]:
    bucket = row.cost or row.usage
    assert bucket is not None
    return row.kind, bucket.bucket_key


def test_pages_preserve_every_exact_cost_and_usage_fact_in_stable_order() -> None:
    from agentmonitor.modules.capacity.domain.budget_history import history_result

    selected = _selected()
    query = _query(selected)
    actual: list[contracts.BudgetHistoryRowV1] = []
    for _ in range(10):
        result = history_result(selected, query)
        assert result.report == selected.report
        assert result.reported_spend == selected.reported_spend
        assert result.as_of == selected.as_of
        assert result.page.availability.state == "available"
        assert len(result.page.items) == 1
        actual.extend(result.page.items)
        if not result.page.has_more:
            assert result.page.next_key is None
            break
        assert result.page.next_key is not None
        query = replace(query, after_key=result.page.next_key)
    else:
        pytest.fail("daily_history_cursor_did_not_terminate")
    assert [_row_key(row) for row in actual] == [
        ("cost", "cost-0"),
        ("usage", "usage-request"),
        ("usage", "usage-token"),
        ("cost", "cost-1"),
        ("cost", "cost-2"),
    ]
    assert {row.cost for row in actual if row.cost is not None} == set(
        selected.report.report.cost_buckets
    )
    assert {row.usage for row in actual if row.usage is not None} == set(
        selected.report.report.usage_buckets
    )
    assert all((row.cost is None) != (row.usage is None) for row in actual)


@pytest.mark.parametrize("days", [7, 30])
@pytest.mark.parametrize("state", ["partial", "empty"])
def test_partial_and_empty_coverage_do_not_create_zero_or_missing_days(
    days: int, state: str
) -> None:
    from agentmonitor.modules.capacity.domain.budget_history import history_result

    original = _selected(days=days).report
    if state == "partial":
        payload = replace(
            original.report,
            completeness="partial",
            covered_period=None,
            omission_codes=("missing_page",),
        )
    else:
        payload = replace(
            original.report, cost_buckets=(), usage_buckets=(), currency=None
        )
    selected = _with_report(replace(original, report=payload))
    result = history_result(selected, _query(selected, limit=200))
    assert result.report.report == payload
    assert result.reported_spend.total is None
    assert len(result.page.items) == (5 if state == "partial" else 0)
    assert result.page.has_more is False
    assert result.page.next_key is None


@pytest.mark.parametrize(
    "field", ["account_id", "resource_id", "report_id", "period", "as_of"]
)
def test_selected_report_must_match_every_requested_dimension(field: str) -> None:
    from agentmonitor.modules.capacity.domain.budget_history import history_result

    selected = _selected()
    query = _query(selected)
    value: Any = OpaqueIdV1("another-context")
    if field == "period":
        value = BudgetPeriodV1(
            query.period.start - timedelta(days=7), query.period.end - timedelta(days=7)
        )
    elif field == "as_of":
        value = query.as_of + timedelta(hours=1)
    with pytest.raises(ValueError, match="budget_history_context_invalid"):
        history_result(selected, replace(query, **{field: value}))


@pytest.mark.parametrize("cursor", ["garbage", "[]", "-1", "1.2.3", "a" * 100])
def test_malformed_continuation_is_not_a_first_page(cursor: str) -> None:
    from agentmonitor.modules.capacity.domain.budget_history import history_result

    selected = _selected()
    with pytest.raises(ValueError, match="budget_history_cursor_invalid"):
        history_result(selected, _query(selected, after_key=cursor))


@pytest.mark.parametrize("changed", ["body", "report", "as_of", "limit", "scope"])
def test_continuation_cannot_cross_immutable_selection_or_body(changed: str) -> None:
    from agentmonitor.modules.capacity.domain.budget_history import history_result

    selected = _selected()
    first = history_result(selected, _query(selected))
    assert first.page.next_key is not None
    if changed == "body":
        selected = _with_report(
            replace(
                selected.report,
                report=replace(
                    selected.report.report,
                    cost_buckets=selected.report.report.cost_buckets[1:],
                ),
            )
        )
    elif changed == "scope":
        selected = _with_report(
            replace(
                selected.report,
                report=replace(selected.report.report, scope_generation=2),
            )
        )
    elif changed == "report":
        selected = replace(
            selected,
            report=replace(selected.report, report_id=OpaqueIdV1("replacement-report")),
            reported_spend=replace(
                selected.reported_spend, report_id=OpaqueIdV1("replacement-report")
            ),
        )
    elif changed == "as_of":
        selected = replace(selected, as_of=selected.as_of + timedelta(hours=1))
    query = _query(
        selected, after_key=first.page.next_key, limit=2 if changed == "limit" else 1
    )
    with pytest.raises(ValueError, match="budget_history_cursor_invalid"):
        history_result(selected, query)


def test_selected_spend_cannot_belong_to_another_report() -> None:
    from agentmonitor.modules.capacity.domain.budget_history import history_result

    selected = _selected()
    query = _query(selected)
    selected = replace(
        selected,
        reported_spend=replace(
            selected.reported_spend, report_id=OpaqueIdV1("different-report")
        ),
    )
    with pytest.raises(ValueError, match="budget_history_context_invalid"):
        history_result(selected, query)


def test_history_continuation_key_fits_public_cursor_key_contract() -> None:
    import re

    from agentmonitor.modules.capacity.domain.budget_history import history_result

    selected = _selected()
    first = history_result(selected, _query(selected))
    key = first.page.next_key
    assert key is not None
    assert len(key) <= 64
    assert re.fullmatch(r"[A-Za-z0-9_-]{1,64}", key) is not None
    assert re.fullmatch(r"v1_[0-9a-f]{56}_[1-9][0-9]{0,3}", key) is not None
    following = history_result(selected, _query(selected, after_key=key))
    assert following.page.items != first.page.items


def test_last_continuation_at_report_fact_bound_fits_cursor_contract() -> None:
    from agentmonitor.modules.capacity.domain.budget_history import history_result

    original = _selected()
    report = replace(
        original.report.report,
        usage_buckets=(),
        cost_buckets=tuple(
            replace(
                original.report.report.cost_buckets[0],
                kind="adjustment",
                bucket_key=f"adjustment-{i:05}",
            )
            for i in range(10000)
        ),
    )
    selected = _with_report(replace(original.report, report=report))
    first = history_result(selected, _query(selected))
    assert first.page.next_key is not None
    prefix = first.page.next_key.rsplit("_", 1)[0]
    penultimate = history_result(selected, _query(selected, after_key=prefix + "_9998"))
    assert penultimate.page.next_key == prefix + "_9999"
    assert len(penultimate.page.next_key) <= 64
    last = history_result(
        selected, _query(selected, after_key=penultimate.page.next_key)
    )
    assert len(last.page.items) == 1
    assert last.page.next_key is None
    assert not last.page.has_more
    with pytest.raises(ValueError, match="budget_history_cursor_invalid"):
        history_result(selected, _query(selected, after_key=prefix + "_10000"))

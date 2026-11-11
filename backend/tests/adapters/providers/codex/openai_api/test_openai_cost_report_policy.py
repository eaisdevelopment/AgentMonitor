"""Pure normalized domain report coverage, not provider JSON parsing fixtures."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from agentmonitor.adapters.providers.codex.openai_api.policy import money_from_number
from agentmonitor.adapters.providers.codex.openai_api.source import _report
from agentmonitor.contracts.capacity_v1 import BudgetCostBucketV1, BudgetPeriodV1
from test_openai_cost_request_policy import request

COLLECTED = datetime(2026, 11, 11, 16, 45, tzinfo=UTC)


def test_empty_coverage_is_not_fabricated_currency_or_zero() -> None:
    target = request()
    report = _report(target, [], set(), set(), collected_at=COLLECTED)
    assert report.completeness == "complete"
    assert report.covered_period == target.period
    assert report.currency is None
    assert report.cost_buckets == ()
    assert report.source_data_through is None
    assert not report.empty_means_zero
    assert report.scope_evidence == "unresolved"
    assert report.collected_at == COLLECTED


def test_pagination_failure_cannot_be_complete_empty() -> None:
    report = _report(
        request(), [], set(), {"page_budget_exceeded"}, collected_at=COLLECTED
    )
    assert report.completeness == "partial"
    assert report.covered_period is None
    assert not report.empty_means_zero
    assert report.omission_codes == ("page_budget_exceeded",)


def test_complete_daily_coverage_preserves_actual_money_and_unknown_freshness() -> None:
    target = request()
    starts = {target.period.start + timedelta(days=day) for day in range(7)}
    rows = [
        BudgetCostBucketV1(
            bucket_key="daily_" + start.strftime("%Y%m%d"),
            period=BudgetPeriodV1(start, start + timedelta(days=1)),
            amount=money_from_number(Decimal("-0.003"), "gbp"),
            dimensions=(),
            kind="adjustment",
        )
        for start in sorted(starts)
    ]
    report = _report(target, rows, starts, set(), collected_at=COLLECTED)
    assert report.completeness == "complete"
    assert report.covered_period == target.period
    assert report.currency == "GBP"
    assert report.cost_basis == "openai_reported_cost"
    assert report.cost_buckets == tuple(rows)
    assert report.source_data_through is None
    assert not report.empty_means_zero


def test_missing_daily_coverage_is_not_zero_filled() -> None:
    target = request()
    omissions: set[str] = set()
    report = _report(
        target, [], {target.period.start}, omissions, collected_at=COLLECTED
    )
    assert report.completeness == "partial"
    assert report.omission_codes == ("daily_coverage_incomplete",)
    assert report.covered_period is None
    assert report.cost_buckets == ()
    assert omissions == set()


def test_mixed_currencies_are_not_combined() -> None:
    target = request()
    rows = [
        BudgetCostBucketV1(
            bucket_key="daily_" + str(day),
            period=BudgetPeriodV1(
                target.period.start + timedelta(days=day),
                target.period.start + timedelta(days=day + 1),
            ),
            amount=money_from_number(1, currency),
            dimensions=(),
            kind="charge",
        )
        for day, currency in enumerate(("usd", "gbp"))
    ]
    with pytest.raises(ValueError, match="openai_cost_currency_mixed"):
        _report(
            target,
            rows,
            {row.period.start for row in rows},
            set(),
            collected_at=COLLECTED,
        )

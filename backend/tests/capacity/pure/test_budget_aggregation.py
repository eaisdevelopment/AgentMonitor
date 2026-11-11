"""M7-MATH-09..12/15: constructed pure values, never boundary fixtures."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from agentmonitor.contracts.capacity_v1 import (
    BudgetCostBucketV1,
    BudgetDimensionV1,
    BudgetPeriodV1,
    BudgetReportInputV1,
    BudgetReportViewV1,
    CapacitySubjectV2,
)
from agentmonitor.contracts.common_quantity_v1 import CanonicalDecimalV1, ExactMoneyV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import ProviderTargetRefV1
from agentmonitor.modules.capacity.domain.budget_aggregation import (
    BudgetSpendInput,
    aggregate_budget_spend,
)
from agentmonitor.modules.capacity.domain.budget_reports import BudgetReportSelection

START = datetime(2026, 11, 1, tzinfo=UTC)
PERIOD = BudgetPeriodV1(START, START + timedelta(days=7))


def _input(
    resource: str,
    amount: str | None = "1",
    *,
    pool: str | None = None,
    hour: int = 1,
    currency: str = "USD",
) -> BudgetSpendInput:
    rows = (
        ()
        if amount is None
        else (
            BudgetCostBucketV1(
                "charge",
                PERIOD,
                ExactMoneyV1(
                    CanonicalDecimalV1.from_decimal(Decimal(amount)), currency
                ),
                (),
                "charge",
            ),
        )
    )
    report = BudgetReportInputV1(
        subject=CapacitySubjectV2(
            "claude",
            ProviderTargetRefV1("cloud_service", OpaqueIdV1("amat_" + "a" * 32)),
            OpaqueIdV1("account-" + resource),
            OpaqueIdV1(resource),
        ),
        binding_id=OpaqueIdV1("binding-" + resource),
        binding_generation=1,
        scope_generation=1,
        scope_id=OpaqueIdV1("scope-" + (pool or resource)),
        scope_evidence="provider_verified",
        source_id="pure-cost",
        source_category="costs",
        cost_basis="discounted_before_credits",
        grouping=(),
        requested_period=PERIOD,
        covered_period=PERIOD,
        source_data_through=PERIOD.end,
        collected_at=PERIOD.end + timedelta(hours=hour),
        completeness="complete",
        omission_codes=(),
        currency=currency,
        empty_means_zero=True,
        cost_buckets=rows,
        usage_buckets=(),
    )
    view = BudgetReportViewV1(
        OpaqueIdV1(f"report-{resource}-{hour}"), report, report.collected_at
    )
    return BudgetSpendInput(
        OpaqueIdV1(resource),
        OpaqueIdV1(pool or resource),
        "provider_verified",
        BudgetReportSelection(view, view),
    )


def _payload(item: BudgetSpendInput, **changes: Any) -> BudgetSpendInput:
    view = item.selection.current
    assert view is not None
    changed = replace(view, report=replace(view.report, **changes))
    return replace(item, selection=BudgetReportSelection(changed, changed))


def test_exact_spend_signed_adjustment_and_distinct_equal_pools() -> None:
    first, second = _input("one", "0.1"), _input("two", "0.2")
    adjusted = _input("three", "10")
    assert adjusted.selection.current is not None
    adjustment = BudgetCostBucketV1(
        "credit-correction",
        PERIOD,
        ExactMoneyV1(CanonicalDecimalV1("-2", 0), "USD"),
        (),
        "adjustment",
    )
    adjusted = _payload(
        adjusted,
        cost_buckets=(*adjusted.selection.current.report.cost_buckets, adjustment),
    )
    result = aggregate_budget_spend((first, second, adjusted, _input("four", "0.1")))
    assert result.reason is None
    assert len(result.groups) == 1
    assert result.groups[0].total == ExactMoneyV1(CanonicalDecimalV1("84", 1), "USD")
    assert len(result.groups[0].contributions) == 4
    assert all(row.reason == "included" for row in result.coverage)


def test_shared_pool_counts_latest_complete_report_once_across_access_paths() -> None:
    old = _input("one", "8", pool="shared", hour=1)
    new = _input("two", "6", pool="shared", hour=2)
    result = aggregate_budget_spend((old, new))
    assert result.groups[0].total.amount == CanonicalDecimalV1("6", 0)
    assert len(result.groups[0].contributions) == 1
    assert result.groups[0].contributions[0].report == new.selection.current
    assert [row.reason for row in result.coverage] == [
        "shared_pool_duplicate",
        "included",
    ]
    assert aggregate_budget_spend((new, old)).groups == result.groups


def test_unresolved_overlap_is_visible_but_excluded_from_partial_subtotal() -> None:
    ambiguous = replace(
        _input("unknown", "100"), canonical_pool_id=None, identity_evidence="unresolved"
    )
    result = aggregate_budget_spend((_input("known", "2"), ambiguous))
    assert result.groups[0].total.amount == CanonicalDecimalV1("2", 0)
    assert result.coverage[1].reason == "unresolved_overlap"
    assert result.coverage[1].selection == ambiguous.selection


def test_no_eligible_input_is_unavailable_but_authoritative_empty_can_be_zero() -> None:
    assert aggregate_budget_spend(()).reason == "no_eligible_reports"
    missing = replace(_input("missing"), selection=BudgetReportSelection(None, None))
    unknown = _payload(
        _input("unknown", None), empty_means_zero=False, source_data_through=None
    )
    result = aggregate_budget_spend((missing, unknown))
    assert result.groups == () and result.reason == "no_eligible_reports"
    assert [row.reason for row in result.coverage] == [
        "missing_report",
        "empty_zero_unproven",
    ]
    zero = aggregate_budget_spend((_input("zero", None),))
    assert zero.reason is None and zero.groups[0].total.amount == CanonicalDecimalV1(
        "0", 0
    )
    assert zero.groups[0].contributions[0].report.report.cost_buckets == ()


def test_partial_and_unequal_coverage_cannot_be_a_whole_period_subtotal() -> None:
    partial = _payload(
        _input("partial"),
        completeness="partial",
        omission_codes=("missing_page",),
        empty_means_zero=False,
    )
    short = _payload(
        _input("short"),
        cost_buckets=(),
        empty_means_zero=False,
        covered_period=BudgetPeriodV1(START + timedelta(days=1), PERIOD.end),
    )
    result = aggregate_budget_spend((partial, short))
    assert result.groups == ()
    assert [row.reason for row in result.coverage] == [
        "incomplete_report",
        "incomplete_report",
    ]


def test_old_complete_report_after_partial_refresh_keeps_original_evidence() -> None:
    old = _input("pool", "8", hour=1)
    attempt = _payload(
        _input("pool", "99", hour=3),
        completeness="partial",
        omission_codes=("missing_page",),
        empty_means_zero=False,
    )
    retained = replace(
        old,
        selection=BudgetReportSelection(
            old.selection.current, attempt.selection.current
        ),
    )
    result = aggregate_budget_spend((retained,))
    contribution = result.groups[0].contributions[0]
    assert contribution.retained_after_later_attempt
    assert contribution.report == old.selection.current
    assert contribution.report.report.source_data_through == PERIOD.end
    assert result.coverage[0].selection.latest_attempt == attempt.selection.current


def test_currency_period_basis_and_category_remain_separate_groups() -> None:
    shifted = BudgetPeriodV1(START - timedelta(days=7), START)
    period = _payload(
        _input("period", None), requested_period=shifted, covered_period=shifted
    )
    basis = _payload(_input("basis"), cost_basis="list_price")
    category = _payload(_input("category"), source_category="self_costs")
    result = aggregate_budget_spend(
        (_input("usd"), _input("gbp", currency="GBP"), period, basis, category)
    )
    assert len(result.groups) == 5
    assert {group.currency for group in result.groups} == {"USD", "GBP"}
    assert {group.period for group in result.groups} == {PERIOD, shifted}


def test_breakdown_is_an_alternative_not_added_to_pool_total() -> None:
    breakdown = _input("model", pool="shared")
    assert breakdown.selection.current is not None
    rows = tuple(
        replace(row, dimensions=(BudgetDimensionV1("model", "constructed"),))
        for row in breakdown.selection.current.report.cost_buckets
    )
    breakdown = _payload(breakdown, grouping=("model",), cost_buckets=rows)
    result = aggregate_budget_spend((_input("total", "3", pool="shared"), breakdown))
    assert result.groups[0].total.amount == CanonicalDecimalV1("3", 0)
    assert result.coverage[1].reason == "breakdown_report"


def test_shared_pool_with_conflicting_sources_is_excluded() -> None:
    first = _input("first", pool="shared")
    other = _payload(_input("other", pool="shared"), source_id="different-cost-source")
    result = aggregate_budget_spend((first, other))
    assert result.groups == ()
    assert all(row.reason == "incompatible_pool_reports" for row in result.coverage)


def test_owner_asserted_pool_identity_is_disclosed() -> None:
    item = replace(_input("owner"), identity_evidence="owner_asserted")
    result = aggregate_budget_spend((item,))
    assert result.groups[0].contributions[0].identity_evidence == "owner_asserted"


def test_inventory_limit_returns_no_truncated_total() -> None:
    items = tuple(
        BudgetSpendInput(
            OpaqueIdV1(f"resource-{n}"),
            OpaqueIdV1(f"pool-{n}"),
            "provider_verified",
            BudgetReportSelection(None, None),
        )
        for n in range(2001)
    )
    result = aggregate_budget_spend(items)
    assert result.reason == "selection_too_large" and result.groups == ()
    assert len(result.coverage) == 2001
    assert all(row.reason == "selection_too_large" for row in result.coverage)


def test_invalid_resource_association_and_duplicate_inventory_are_rejected() -> None:
    item = _input("one")
    with pytest.raises(ValueError, match="budget_spend_resource_mismatch"):
        replace(item, resource_id=OpaqueIdV1("other"))
    with pytest.raises(ValueError, match="budget_spend_duplicate_resource"):
        aggregate_budget_spend((item, item))


def test_final_exact_overflow_is_not_silently_rounded() -> None:
    with pytest.raises(ValueError, match="budget_money_overflow"):
        aggregate_budget_spend((_input("one", "9" * 78), _input("two", "9" * 78)))


def test_unknown_currency_cannot_create_a_zero_money_group() -> None:
    item = _payload(_input("unknown", None), currency=None, empty_means_zero=False)
    result = aggregate_budget_spend((item,))
    assert result.groups == () and result.reason == "no_eligible_reports"
    assert result.coverage[0].reason == "currency_unavailable"


@pytest.mark.parametrize("count,shared", [(2000, False), (2001, True)])
def test_inventory_bound_counts_canonical_pools_not_access_paths(
    count: int, shared: bool
) -> None:
    items = tuple(
        BudgetSpendInput(
            OpaqueIdV1(f"resource-{n}"),
            OpaqueIdV1("shared" if shared else f"pool-{n}"),
            "provider_verified",
            BudgetReportSelection(None, None),
        )
        for n in range(count)
    )
    result = aggregate_budget_spend(items)
    assert result.reason == "no_eligible_reports"
    assert len(result.coverage) == count


def test_net_negative_correction_is_retained_without_clamping() -> None:
    item = _input("adjusted", "1")
    assert item.selection.current is not None
    adjustment = BudgetCostBucketV1(
        "signed-adjustment",
        PERIOD,
        ExactMoneyV1(CanonicalDecimalV1("-2", 0), "USD"),
        (),
        "adjustment",
    )
    item = _payload(
        item, cost_buckets=(*item.selection.current.report.cost_buckets, adjustment)
    )
    assert aggregate_budget_spend((item,)).groups[0].total.amount == CanonicalDecimalV1(
        "-1", 0
    )

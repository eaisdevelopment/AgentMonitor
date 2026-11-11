"""Pure M7 contract examples; these values never cross an I/O boundary."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from agentmonitor.contracts import capacity_v1 as contracts
from agentmonitor.contracts.common_quantity_v1 import CanonicalDecimalV1, ExactMoneyV1
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.contracts.registry_v1 import ProviderTargetRefV1

START = datetime(2026, 11, 1, tzinfo=UTC)
END = START + timedelta(days=1)


def _report() -> contracts.BudgetReportInputV1:
    assert hasattr(contracts, "BudgetReportInputV1"), (
        "M7 typed billing report is absent"
    )
    period = contracts.BudgetPeriodV1(start=START, end=END)
    return contracts.BudgetReportInputV1(
        subject=contracts.CapacitySubjectV2(
            provider_key="claude",
            provider_target=ProviderTargetRefV1(
                target_kind="cloud_service", target_id=OpaqueIdV1("amat_" + "b" * 32)
            ),
            account_id=OpaqueIdV1("pure-account"),
            resource_id=OpaqueIdV1("pure-resource"),
        ),
        binding_id=OpaqueIdV1("pure-binding"),
        binding_generation=1,
        scope_generation=1,
        scope_id=OpaqueIdV1("pure-scope"),
        scope_evidence="provider_verified",
        source_id="pure-cost-contract",
        source_category="costs",
        cost_basis="after_discount_before_credit",
        grouping=(),
        requested_period=period,
        covered_period=period,
        source_data_through=END,
        collected_at=END + timedelta(hours=1),
        completeness="complete",
        omission_codes=(),
        currency="USD",
        empty_means_zero=True,
        cost_buckets=(),
        usage_buckets=(),
    )


def _cost(value: str = "1.25") -> contracts.BudgetCostBucketV1:
    return contracts.BudgetCostBucketV1(
        bucket_key="pure-bucket",
        period=contracts.BudgetPeriodV1(start=START, end=END),
        amount=ExactMoneyV1(
            amount=CanonicalDecimalV1.from_decimal(Decimal(value)), currency="USD"
        ),
        dimensions=(),
        kind="adjustment" if Decimal(value) < 0 else "charge",
    )


def test_real_empty_report_contract_needs_coverage_not_dummy_observations() -> None:
    report = _report()
    assert report.cost_buckets == ()
    assert report.usage_buckets == ()
    assert report.covered_period == report.requested_period
    assert report.empty_means_zero


def test_signed_adjustment_preserved_and_repeated_bucket_rejected() -> None:
    report = _report()
    cost = _cost("-0.004")
    assert replace(report, cost_buckets=(cost,)).cost_buckets[0].amount == cost.amount
    with pytest.raises(contracts.InvalidCapacityContractV1, match="duplicate_bucket"):
        replace(report, cost_buckets=(cost, cost))


def test_delayed_or_partial_report_cannot_claim_empty_zero() -> None:
    report = _report()
    with pytest.raises(contracts.InvalidCapacityContractV1, match="empty_zero"):
        replace(report, covered_period=None, source_data_through=None)
    with pytest.raises(contracts.InvalidCapacityContractV1, match="empty_zero"):
        replace(report, completeness="partial", omission_codes=("missing_page",))
    delayed = replace(
        report,
        completeness="unknown",
        covered_period=None,
        source_data_through=None,
        empty_means_zero=False,
        omission_codes=("source_delayed",),
    )
    assert delayed.covered_period is None and not delayed.empty_means_zero


def test_money_field_distinguishes_missing_and_exact_zero() -> None:
    _report()
    missing = contracts.ExactMoneyFieldV1(
        availability=FieldAvailabilityV1("unsupported"),
        value=None,
        precision="unknown",
        confidence="unknown",
        value_kind="unknown",
        reason_code="source_does_not_expose_balance",
    )
    zero = contracts.ExactMoneyFieldV1(
        availability=FieldAvailabilityV1("available"),
        value=_cost("0").amount,
        precision="exact",
        confidence="confirmed",
        value_kind="provider_reported",
        reason_code=None,
    )
    assert missing.value is None and zero.value is not None
    with pytest.raises(contracts.InvalidCapacityContractV1, match="field_state"):
        replace(missing, value=zero.value)


def test_report_rejects_incompatible_currency_and_outside_buckets() -> None:
    report = _report()
    cost = _cost()
    with pytest.raises(contracts.InvalidCapacityContractV1, match="currency"):
        replace(
            report,
            cost_buckets=(replace(cost, amount=replace(cost.amount, currency="GBP")),),
        )
    with pytest.raises(contracts.InvalidCapacityContractV1, match="bucket_period"):
        replace(
            report,
            cost_buckets=(
                replace(
                    cost,
                    period=contracts.BudgetPeriodV1(
                        start=START - timedelta(days=1),
                        end=END,
                    ),
                ),
            ),
        )


def test_grouping_and_scope_are_explicit_not_inferred_from_account() -> None:
    report = _report()
    unresolved = replace(report, scope_id=None, scope_evidence="unresolved")
    assert unresolved.scope_id is None
    with pytest.raises(contracts.InvalidCapacityContractV1, match="scope"):
        replace(report, scope_id=None)
    with pytest.raises(contracts.InvalidCapacityContractV1, match="grouping"):
        replace(report, grouping=("model",), cost_buckets=(_cost(),))


def test_partial_report_requires_reason_and_generation_is_positive() -> None:
    report = _report()
    with pytest.raises(contracts.InvalidCapacityContractV1, match="omissions"):
        replace(report, completeness="partial", empty_means_zero=False)
    for generation in (0, -1, True):
        with pytest.raises(contracts.InvalidCapacityContractV1, match="generation"):
            replace(report, binding_generation=generation)
        with pytest.raises(contracts.InvalidCapacityContractV1, match="generation"):
            replace(report, scope_generation=generation)


def test_duplicate_semantic_costs_cannot_hide_behind_different_keys() -> None:
    report = _report()
    cost = _cost()
    with pytest.raises(
        contracts.InvalidCapacityContractV1, match="overlapping_buckets"
    ):
        replace(report, cost_buckets=(cost, replace(cost, bucket_key="other-key")))
    # A distinct signed adjustment may refer to the same reporting interval.
    corrected = replace(
        report, cost_buckets=(cost, replace(_cost("-0.25"), bucket_key="adjustment"))
    )
    assert len(corrected.cost_buckets) == 2


def test_empty_report_with_lagging_watermark_cannot_assert_zero() -> None:
    with pytest.raises(contracts.InvalidCapacityContractV1, match="empty_zero"):
        replace(_report(), source_data_through=START)


def test_bucket_cannot_exceed_declared_partial_coverage() -> None:
    with pytest.raises(contracts.InvalidCapacityContractV1, match="bucket_period"):
        replace(
            _report(),
            completeness="partial",
            omission_codes=("missing_page",),
            empty_means_zero=False,
            covered_period=contracts.BudgetPeriodV1(START, START + timedelta(hours=12)),
            cost_buckets=(_cost(),),
        )


def test_distinct_adjustments_can_share_interval_but_not_identity() -> None:
    first = replace(_cost("-1"), bucket_key="adjustment-one")
    second = replace(_cost("-2"), bucket_key="adjustment-two")
    report = replace(_report(), cost_buckets=(first, second))
    assert len(report.cost_buckets) == 2
    with pytest.raises(contracts.InvalidCapacityContractV1, match="duplicate_bucket"):
        replace(report, cost_buckets=(first, first))

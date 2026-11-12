"""M7-MATH-03/09/10/15/16: explicit-time monetary policy, no I/O."""

from dataclasses import replace
from datetime import timedelta
from decimal import localcontext

import pytest
from agentmonitor.contracts.budget_query_v1 import BudgetFundComponentV1
from agentmonitor.contracts.capacity_v1 import ExactMoneyFieldV1
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.modules.capacity.domain.budget_forecast import BudgetForecastEvidence

from backend.tests.capacity.pure.test_budget_daily_costs import (
    AS_OF,
    END,
    START,
    _money,
    _selected,
    _with_view,
)
from backend.tests.providers.ollama.pure.test_funds_projection import _window


def _fund(value: str = "6") -> BudgetFundComponentV1:
    field = ExactMoneyFieldV1(
        FieldAvailabilityV1("available"),
        _money(value),
        "exact",
        "confirmed",
        "provider_reported",
        None,
    )
    return BudgetFundComponentV1(
        subject=_selected().report.report.subject,
        component_id=OpaqueIdV1("fund-component"),
        kind="balance",
        remaining=field,
        limit=ExactMoneyFieldV1(
            FieldAvailabilityV1("unknown"),
            None,
            "unknown",
            "unknown",
            "unknown",
            "not_reported",
        ),
        period=None,
        renewal_at=None,
        expires_at=None,
        is_constraining=None,
        scope_evidence="provider_verified",
        observation_id=OpaqueIdV1("fund-observation"),
        collection_run_id=OpaqueIdV1("fund-run"),
        observed_at=END,
        collected_at=END,
        stored_at=END,
        freshness="fresh",
        completeness="complete",
        provenance=replace(
            _window().provenance, freshness_deadline=AS_OF + timedelta(hours=1)
        ),
    )


def _evidence() -> BudgetForecastEvidence:
    from agentmonitor.modules.capacity.domain.budget_forecast import (
        BudgetForecastEvidence,
    )

    return BudgetForecastEvidence(
        corrections_resolved=True,
        funds_compatible=True,
        costs_allocated_to_fund=True,
        cost_freshness_deadline=AS_OF + timedelta(hours=1),
    )


def test_rate_without_funds_has_exact_numerator_duration_and_lineage() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs
    from agentmonitor.modules.capacity.domain.budget_forecast import forecast

    result = forecast(daily_costs(_selected()), evidence=_evidence())
    assert result.rate is not None
    assert result.rate.cost == _money("6")
    assert result.rate.covered_seconds == 3 * 86400
    assert result.rate.period.start == START + timedelta(days=4)
    assert result.rate.period.end == END
    assert result.rate.input_report_ids == (_selected().report.report_id,)
    assert result.rate_reason == "observed_rate_available"
    assert result.exhaustion_reason == "funds_unavailable"
    assert result.exhaustion_at is None
    assert result.method_id == "budget-observed-rate-v1"
    assert result.method_version == "1.0.0"


@pytest.mark.parametrize(
    "total,display",
    (
        ("1", "0.33 USD/day"),
        ("0.01", "<0.01 USD/day"),
        ("0", "0.00 USD/day"),
        ("3.015", "1.00 USD/day"),
        ("3.045", "1.02 USD/day"),
    ),
)
def test_rate_display_rounds_exact_ratio_without_false_zero(
    total: str, display: str
) -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs
    from agentmonitor.modules.capacity.domain.budget_forecast import forecast

    with localcontext() as context:
        context.prec = 2
        result = forecast(
            daily_costs(_selected(((4, total), (5, "0"), (6, "0")))),
            evidence=_evidence(),
        )
        assert result.rate is not None
        assert result.rate.display == display
        assert result.rate.display_decimal_places == 2
        assert result.rate.display_rounding == "half_even"
        assert result.rate.cost == _money(total)
        assert result.rate.covered_seconds == 259200
        other_currency = replace(result.rate, cost=_money(total, "GBP"))
        assert other_currency.display is None
        assert other_currency.display_decimal_places is None
        assert other_currency.display_rounding is None


@pytest.mark.parametrize("count", (200, 201))
def test_sample_contributing_bucket_bound_is_not_silently_truncated(count: int) -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs
    from agentmonitor.modules.capacity.domain.budget_forecast import forecast

    values = tuple((4 + index % 3, "1") for index in range(count))
    result = forecast(
        daily_costs(_selected(values, grouped=True), disjoint_costs=True),
        evidence=_evidence(),
    )
    if count == 200:
        assert result.rate is not None
        assert result.rate.cost == _money("200")
        assert len(result.rate.input_bucket_keys) == count
    else:
        assert result.rate is None
        assert result.rate_reason == "sample_bucket_limit_exceeded"
        assert result.exhaustion_at is None


def test_bucket_bound_counts_only_selected_contiguous_sample() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs
    from agentmonitor.modules.capacity.domain.budget_forecast import forecast

    values = tuple((0, "1") for _ in range(201)) + ((4, "2"), (5, "2"), (6, "2"))
    result = forecast(
        daily_costs(_selected(values, grouped=True), disjoint_costs=True),
        evidence=_evidence(),
    )
    assert result.rate is not None
    assert result.rate.cost == _money("6")
    assert len(result.rate.input_bucket_keys) == 3


def test_daily_row_count_does_not_replace_three_day_requirement() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs
    from agentmonitor.modules.capacity.domain.budget_forecast import forecast

    one_day = daily_costs(
        _selected(((6, "1"), (6, "1"), (6, "1")), grouped=True), disjoint_costs=True
    )
    assert forecast(one_day, evidence=_evidence()).rate is None
    three_days = daily_costs(
        _selected(tuple((day, "1") for day in (4, 4, 5, 5, 6, 6)), grouped=True),
        disjoint_costs=True,
    )
    rate = forecast(three_days, evidence=_evidence()).rate
    assert rate is not None
    assert rate.cost == _money("6") and rate.covered_seconds == 259200


def test_unknown_corrections_and_compatibility_default_to_unavailable() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs
    from agentmonitor.modules.capacity.domain.budget_forecast import (
        BudgetForecastEvidence,
        forecast,
    )

    daily = daily_costs(_selected())
    assert forecast(daily).rate_reason == "corrections_unresolved"
    result = forecast(
        daily, funds=_fund(), evidence=BudgetForecastEvidence(corrections_resolved=True)
    )
    assert result.rate is not None
    assert result.exhaustion_reason == "funds_incompatible"


@pytest.mark.parametrize(
    "values,expected_start",
    [
        (((0, "2"), (1, "2"), (2, "2"), (4, "4"), (5, "4"), (6, "4")), 4),
        (((0, "2"), (1, "2"), (2, "2"), (5, "4"), (6, "4")), 0),
    ],
)
def test_newest_qualifying_contiguous_interval_never_bridges_gap(
    values: tuple[tuple[int, str], ...], expected_start: int
) -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs
    from agentmonitor.modules.capacity.domain.budget_forecast import forecast

    result = forecast(daily_costs(_selected(values)), evidence=_evidence())
    assert result.rate is not None
    assert result.rate.period.start == START + timedelta(days=expected_start)
    assert result.rate.covered_seconds == 259200


@pytest.mark.parametrize("value", ("-2", "2", "0"))
def test_adjusted_sample_never_becomes_a_rate(value: str) -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs
    from agentmonitor.modules.capacity.domain.budget_forecast import forecast

    result = forecast(
        daily_costs(
            _selected(tuple((day, value) for day in (4, 5, 6)), adjustments=True)
        ),
        evidence=_evidence(),
    )
    assert result.rate is None
    assert result.exhaustion_at is None


def test_qualified_zero_coverage_is_zero_rate_not_infinite_date() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs
    from agentmonitor.modules.capacity.domain.budget_forecast import forecast

    selected = _selected(())
    selected = _with_view(
        replace(
            selected.report,
            report=replace(selected.report.report, empty_means_zero=True),
        )
    )
    result = forecast(daily_costs(selected), funds=_fund(), evidence=_evidence())
    assert result.rate is not None and result.rate.cost == _money("0")
    assert result.rate.covered_seconds == 7 * 86400
    assert result.exhaustion_reason == "no_consumption"
    assert result.exhaustion_at is None
    assert forecast(daily_costs(_selected(())), evidence=_evidence()).rate is None


@pytest.mark.parametrize(
    "invalid",
    (
        "stale",
        "incompatible",
        "allocation",
        "unknown_time",
        "currency",
        "future",
        "soft_limit",
        "hard_unenforced",
    ),
)
def test_ineligible_funds_do_not_move_rate_to_an_old_cutoff(invalid: str) -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs
    from agentmonitor.modules.capacity.domain.budget_forecast import forecast

    fund = replace(_fund(), observed_at=START, collected_at=START, stored_at=START)
    evidence = _evidence()
    if invalid == "stale":
        fund = replace(fund, freshness="stale")
    elif invalid == "incompatible":
        evidence = replace(evidence, funds_compatible=False)
    elif invalid == "allocation":
        evidence = replace(evidence, costs_allocated_to_fund=False)
    elif invalid == "unknown_time":
        fund = replace(fund, observed_at=None)
    elif invalid == "currency":
        fund = replace(
            fund, remaining=replace(fund.remaining, value=_money("6", "GBP"))
        )
    elif invalid == "future":
        fund = replace(
            fund,
            observed_at=AS_OF + timedelta(days=1),
            collected_at=AS_OF + timedelta(days=1),
            stored_at=AS_OF + timedelta(days=1),
        )
    elif invalid == "soft_limit":
        fund = replace(fund, kind="soft_limit")
    else:
        fund = replace(fund, kind="hard_limit")
    result = forecast(daily_costs(_selected()), funds=fund, evidence=evidence)
    assert result.rate is not None and result.rate.period.end == END
    assert result.exhaustion_at is None


def test_compatible_balance_estimate_is_anchored_to_observation_not_page_time() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs
    from agentmonitor.modules.capacity.domain.budget_forecast import forecast

    selected = _selected()
    daily = daily_costs(selected)
    result = forecast(daily, funds=_fund(), evidence=_evidence())
    assert result.exhaustion_at == END + timedelta(days=3)
    assert result.funds_observed_at == END
    assert result.input_observation_ids == (_fund().observation_id,)
    assert (
        result.time_left_numerator is not None
        and result.time_left_denominator is not None
    )
    assert result.time_left_numerator == 259200 * result.time_left_denominator
    later = replace(selected, as_of=AS_OF + timedelta(minutes=5))
    assert (
        forecast(daily_costs(later), funds=_fund(), evidence=_evidence()).exhaustion_at
        == result.exhaustion_at
    )


def test_eligible_older_funds_exclude_later_costs_from_the_rate() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs
    from agentmonitor.modules.capacity.domain.budget_forecast import forecast

    selected = _selected(tuple((day, "2" if day < 3 else "100") for day in range(7)))
    observed = START + timedelta(days=3, hours=1)
    funds = replace(
        _fund(), observed_at=observed, collected_at=observed, stored_at=observed
    )
    result = forecast(daily_costs(selected), funds=funds, evidence=_evidence())
    assert result.rate is not None and result.rate.cost == _money("6")
    assert result.rate.period.end == START + timedelta(days=3)
    assert result.exhaustion_at == observed + timedelta(days=3)


@pytest.mark.parametrize(
    "value,reason",
    (("0", "funds_depleted"), ("-1", "funds_exceeded"), ("100", "beyond_horizon")),
)
def test_nonpositive_funds_and_seven_day_horizon_have_no_date(
    value: str, reason: str
) -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs
    from agentmonitor.modules.capacity.domain.budget_forecast import forecast

    result = forecast(
        daily_costs(_selected()), funds=_fund(value), evidence=_evidence()
    )
    assert result.exhaustion_reason == reason
    assert result.exhaustion_at is None


@pytest.mark.parametrize(
    "field,days,reason",
    (
        ("expires_at", 1, "credits_expire_first"),
        ("renewal_at", 1, "renewal_first"),
        ("expires_at", 4, "exhaustion_estimated"),
    ),
)
def test_known_expiry_or_renewal_bounds_consumption_date(
    field: str, days: int, reason: str
) -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs
    from agentmonitor.modules.capacity.domain.budget_forecast import forecast

    boundary = END + timedelta(days=days)
    fund = (
        replace(_fund(), expires_at=boundary)
        if field == "expires_at"
        else replace(_fund(), renewal_at=boundary)
    )
    result = forecast(daily_costs(_selected()), funds=fund, evidence=_evidence())
    assert result.exhaustion_reason == reason
    assert (result.exhaustion_at is not None) == (days == 4)


@pytest.mark.parametrize(
    "missing", ("watermark", "policy", "expired_policy", "fund_deadline")
)
def test_unknown_or_expired_freshness_preserves_rate_without_date(missing: str) -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs
    from agentmonitor.modules.capacity.domain.budget_forecast import forecast

    selected, evidence, funds = _selected(), _evidence(), _fund()
    if missing == "watermark":
        selected = _with_view(
            replace(
                selected.report,
                report=replace(selected.report.report, source_data_through=None),
            )
        )
    elif missing == "policy":
        evidence = replace(evidence, cost_freshness_deadline=None)
    elif missing == "expired_policy":
        evidence = replace(evidence, cost_freshness_deadline=START)
    else:
        funds = replace(
            funds, provenance=replace(funds.provenance, freshness_deadline=None)
        )
    result = forecast(daily_costs(selected), funds=funds, evidence=evidence)
    assert result.rate is not None
    assert result.exhaustion_at is None


def test_exact_ratio_and_ceiling_second_are_independent_of_decimal_context() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs
    from agentmonitor.modules.capacity.domain.budget_forecast import forecast

    selected = _selected(tuple((day, "7") for day in (4, 5, 6)))
    with localcontext() as context:
        context.prec = 2
        result = forecast(daily_costs(selected), funds=_fund("1"), evidence=_evidence())
    assert (
        result.time_left_numerator is not None
        and result.time_left_denominator is not None
    )
    assert result.time_left_numerator * 7 == result.time_left_denominator * 86400
    assert result.exhaustion_at == END + timedelta(seconds=12343)
    assert result.time_rounding == "ceiling_second"


def test_zero_rate_has_no_consumption_reason_even_without_funds() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs
    from agentmonitor.modules.capacity.domain.budget_forecast import forecast

    result = forecast(
        daily_costs(_selected(((4, "0"), (5, "0"), (6, "0")))), evidence=_evidence()
    )
    assert result.rate is not None and result.rate.cost == _money("0")
    assert result.rate_reason == "no_consumption"
    assert result.exhaustion_at is None


@pytest.mark.parametrize(
    "value,available", (("14", True), ("14.000000000000000001", False))
)
def test_horizon_compares_exact_ratio_before_time_rounding(
    value: str, available: bool
) -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs
    from agentmonitor.modules.capacity.domain.budget_forecast import forecast

    result = forecast(
        daily_costs(_selected()), funds=_fund(value), evidence=_evidence()
    )
    assert (result.exhaustion_at is not None) is available
    assert result.exhaustion_reason == (
        "exhaustion_estimated" if available else "beyond_horizon"
    )


def test_enforced_headroom_requires_both_explicit_evidence_and_constraining_fund() -> (
    None
):
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs
    from agentmonitor.modules.capacity.domain.budget_forecast import forecast

    funds = replace(_fund(), kind="hard_limit", is_constraining=True)
    evidence = replace(_evidence(), limit_enforced=True)
    result = forecast(daily_costs(_selected()), funds=funds, evidence=evidence)
    assert result.exhaustion_at == END + timedelta(days=3)
    result = forecast(
        daily_costs(_selected()),
        funds=replace(funds, is_constraining=False),
        evidence=evidence,
    )
    assert result.exhaustion_at is None


def test_sample_cost_overflow_is_unavailable_even_when_each_day_fits() -> None:
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs
    from agentmonitor.modules.capacity.domain.budget_forecast import forecast

    result = forecast(
        daily_costs(_selected(tuple((day, "9" * 78) for day in (4, 5, 6)))),
        evidence=_evidence(),
    )
    assert result.rate is None
    assert result.rate_reason == "cost_total_unavailable"

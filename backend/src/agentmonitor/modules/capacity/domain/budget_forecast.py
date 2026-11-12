"""Pure observed monetary rate and bounded, observation-anchored exhaustion."""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from math import gcd
from typing import ClassVar

from agentmonitor.contracts.budget_query_v1 import BudgetFundComponentV1
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1
from agentmonitor.contracts.common_quantity_v1 import ExactMoneyV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.capacity.domain.budget_daily_costs import (
    BudgetDailyCost,
    BudgetDailyCosts,
)
from agentmonitor.modules.capacity.domain.budget_money import (
    BudgetMoneyError,
    sum_money,
)


@dataclass(frozen=True, slots=True)
class BudgetForecastEvidence:
    """Trusted source/selection decisions, never inferred from owner labels.

    The future application must establish these against the exact report and
    selected fund. They are not public caller-supplied proof or provider policy.
    """

    corrections_resolved: bool = False
    funds_compatible: bool = False
    costs_allocated_to_fund: bool = False
    limit_enforced: bool = False
    cost_freshness_deadline: datetime | None = None

    def __post_init__(self) -> None:
        if any(
            type(value) is not bool
            for value in (
                self.corrections_resolved,
                self.funds_compatible,
                self.costs_allocated_to_fund,
                self.limit_enforced,
            )
        ) or (
            self.cost_freshness_deadline is not None
            and self.cost_freshness_deadline.utcoffset() != timedelta(0)
        ):
            raise ValueError("budget_forecast_evidence_invalid")


@dataclass(frozen=True, slots=True)
class BudgetObservedRate:
    """Exact ratio: cost / covered_seconds; no rounded value drives decisions."""

    cost: ExactMoneyV1
    covered_seconds: int
    period: BudgetPeriodV1
    input_report_ids: tuple[OpaqueIdV1, ...]
    input_bucket_keys: tuple[str, ...]
    day_count: int

    @property
    def display_decimal_places(self) -> int | None:
        return 2 if self.cost.currency == "USD" else None

    @property
    def display_rounding(self) -> str | None:
        return "half_even" if self.cost.currency == "USD" else None

    @property
    def display(self) -> str | None:
        """Admitted USD/day presentation; exact ratio remains authoritative."""
        if self.cost.currency != "USD":
            return None
        numerator = int(self.cost.amount.coefficient) * 86400 * 100
        denominator = 10**self.cost.amount.scale * self.covered_seconds
        if 0 < numerator < denominator:
            return "<0.01 USD/day"
        cents, remainder = divmod(numerator, denominator)
        if remainder * 2 > denominator or (remainder * 2 == denominator and cents % 2):
            cents += 1
        return f"{cents // 100}.{cents % 100:02d} USD/day"


@dataclass(frozen=True, slots=True)
class BudgetForecast:
    as_of: datetime
    rate: BudgetObservedRate | None
    rate_reason: str
    exhaustion_reason: str
    exhaustion_at: datetime | None = None
    funds_observed_at: datetime | None = None
    input_observation_ids: tuple[OpaqueIdV1, ...] = ()
    time_left_numerator: int | None = None
    time_left_denominator: int | None = None
    method_id: ClassVar[str] = "budget-observed-rate-v1"
    method_version: ClassVar[str] = "1.0.0"
    time_rounding: ClassVar[str] = "ceiling_second"


def _funds_reason(
    daily: BudgetDailyCosts,
    funds: BudgetFundComponentV1 | None,
    evidence: BudgetForecastEvidence,
) -> str | None:
    as_of = daily.selected.as_of
    if funds is None:
        return "funds_unavailable"
    if not evidence.funds_compatible:
        return "funds_incompatible"
    if not evidence.costs_allocated_to_fund:
        return "fund_allocation_unknown"
    if (
        funds.kind == "soft_limit"
        or funds.kind == "hard_limit"
        and (not evidence.limit_enforced or funds.is_constraining is not True)
    ):
        return "limit_not_enforced"
    if (
        funds.remaining.availability.state != "available"
        or funds.remaining.value is None
        or funds.remaining.precision != "exact"
    ):
        return "funds_unavailable"
    if funds.remaining.value.currency != daily.selected.report.report.currency:
        return "funds_incompatible"
    if funds.observed_at is None:
        return "funds_time_unknown"
    if (
        any(
            value.utcoffset() != timedelta(0)
            for value in (funds.observed_at, funds.collected_at, funds.stored_at)
        )
        or funds.stored_at > as_of
        or funds.observed_at > as_of
    ):
        return "funds_not_known_at_snapshot"
    deadline = funds.provenance.freshness_deadline
    if (
        funds.freshness != "fresh"
        or funds.completeness != "complete"
        or deadline is None
        or deadline <= as_of
    ):
        return "funds_not_fresh"
    if funds.expires_at is not None and funds.expires_at <= as_of:
        return "funds_expired"
    report = daily.selected.report.report
    if (
        report.source_data_through is None
        or evidence.cost_freshness_deadline is None
        or evidence.cost_freshness_deadline <= as_of
    ):
        return "cost_freshness_unknown"
    return None


def _sample(
    days: tuple[BudgetDailyCost, ...], cutoff: datetime
) -> tuple[BudgetDailyCost, ...]:
    """Newest qualifying contiguous segment; neither gaps nor adjustments bridge."""
    lower = cutoff - timedelta(days=7)
    segments: list[list[BudgetDailyCost]] = [[]]
    for day in days:
        if day.period.start < lower or day.period.end > cutoff:
            continue
        if day.has_adjustment:
            segments.append([])
            continue
        segment = segments[-1]
        if segment and segment[-1].period.end != day.period.start:
            segments.append([])
        segments[-1].append(day)
    return next(
        (tuple(segment) for segment in reversed(segments) if len(segment) >= 3), ()
    )


def _microseconds(delta: timedelta) -> int:
    return (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds


def forecast(
    daily: BudgetDailyCosts,
    *,
    funds: BudgetFundComponentV1 | None = None,
    evidence: BudgetForecastEvidence | None = None,
) -> BudgetForecast:
    """One pinned financial identity; acquisition/authority remain application-owned.

    Daily inputs come from daily_costs, independently of HTTP history pagination.
    Unknown cost freshness permits a labelled historical rate, never a date.
    """
    evidence = evidence if evidence is not None else BudgetForecastEvidence()
    selected = daily.selected
    result = BudgetForecast(
        selected.as_of, None, "insufficient_daily_history", "rate_unavailable"
    )
    if daily.reason is not None:
        return replace(result, rate_reason=daily.reason)
    if not evidence.corrections_resolved:
        return replace(result, rate_reason="corrections_unresolved")
    funds_reason = _funds_reason(daily, funds, evidence)
    anchor = (
        funds.observed_at
        if funds is not None and funds_reason is None
        else selected.as_of
    )
    assert anchor is not None
    cutoff = anchor.replace(hour=0, minute=0, second=0, microsecond=0)
    sample = _sample(daily.days, cutoff)
    if not sample:
        return result
    if sum(len(day.input_bucket_keys) for day in sample) > 200:
        return replace(result, rate_reason="sample_bucket_limit_exceeded")
    try:
        total = sum_money(tuple(day.amount for day in sample))
    except BudgetMoneyError:
        return replace(result, rate_reason="cost_total_unavailable")
    duration = len(sample) * 86400
    rate = BudgetObservedRate(
        total,
        duration,
        BudgetPeriodV1(sample[0].period.start, sample[-1].period.end),
        (selected.report.report_id,),
        tuple(key for day in sample for key in day.input_bucket_keys),
        len(sample),
    )
    result = replace(
        result,
        rate=rate,
        rate_reason="no_consumption"
        if int(total.amount.coefficient) == 0
        else "observed_rate_available",
        exhaustion_reason=funds_reason or "exhaustion_estimated",
    )
    if funds_reason is not None:
        return result
    assert (
        funds is not None
        and funds.remaining.value is not None
        and funds.observed_at is not None
    )
    result = replace(
        result,
        funds_observed_at=funds.observed_at,
        input_observation_ids=(funds.observation_id,),
    )
    watermark = selected.report.report.source_data_through
    if watermark is None or watermark < rate.period.end:
        return replace(result, exhaustion_reason="cost_freshness_unknown")
    remaining = funds.remaining.value.amount
    if int(remaining.coefficient) <= 0:
        return replace(
            result,
            exhaustion_reason="funds_depleted"
            if int(remaining.coefficient) == 0
            else "funds_exceeded",
        )
    if int(total.amount.coefficient) <= 0:
        return replace(result, exhaustion_reason="no_consumption")
    scale = max(remaining.scale, total.amount.scale)
    numerator = int(remaining.coefficient) * 10 ** (scale - remaining.scale) * duration
    denominator = int(total.amount.coefficient) * 10 ** (scale - total.amount.scale)
    factor = gcd(numerator, denominator)
    numerator, denominator = numerator // factor, denominator // factor
    for boundary, reason in (
        (funds.expires_at, "credits_expire_first"),
        (funds.renewal_at, "renewal_first"),
    ):
        if (
            boundary is not None
            and _microseconds(boundary - anchor) * denominator < numerator * 1000000
        ):
            return replace(result, exhaustion_reason=reason)
    if numerator > 604800 * denominator:
        return replace(result, exhaustion_reason="beyond_horizon")
    seconds = (numerator + denominator - 1) // denominator
    try:
        exhaustion_at = anchor + timedelta(seconds=seconds)
    except OverflowError:
        return replace(result, exhaustion_reason="forecast_time_unavailable")
    return replace(
        result,
        exhaustion_at=exhaustion_at,
        time_left_numerator=numerator,
        time_left_denominator=denominator,
    )

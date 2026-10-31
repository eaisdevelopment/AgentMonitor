"""Pure bounded-secant forecasting with explicit time, segments and precision."""

import hashlib
import json
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, Decimal, localcontext
from typing import Literal

from agentmonitor.contracts.capacity_v1 import (
    CapacityBurnRateV1,
    CapacityForecastPolicyV1,
    CapacityForecastSampleV1,
    CapacityForecastV1,
    ExactMetricFieldV1,
    ForecastAlertConditionV1,
    InvalidCapacityContractV1,
)
from agentmonitor.contracts.common_quantity_v1 import (
    CanonicalDecimalV1,
    ExactQuantityV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def _seconds(delta: timedelta) -> Decimal:
    return Decimal(delta.days * 86400 + delta.seconds) + Decimal(
        delta.microseconds
    ) / Decimal(1000000)


def select_latest_compatible_suffix_v1(
    samples: tuple[CapacityForecastSampleV1, ...],
) -> tuple[CapacityForecastSampleV1, ...]:
    """Keep only the newest evidenced definition, source and reset segment."""
    if not samples:
        return ()
    ordered = tuple(
        sorted(samples, key=lambda p: (p.observed_at, p.observation_id.value))
    )
    latest = ordered[-1]
    selected: list[CapacityForecastSampleV1] = []
    for point in reversed(ordered):
        if (
            point.subject != latest.subject
            or point.window_key != latest.window_key
            or point.metric != latest.metric
            or point.window_definition_id != latest.window_definition_id
            or point.definition_version != latest.definition_version
            or point.source_compatibility_id != latest.source_compatibility_id
            or point.reset_segment_id != latest.reset_segment_id
            or point.reset_at != latest.reset_at
        ):
            break
        selected.append(point)
    return tuple(reversed(selected))


def derive_forecast_alert_condition_v1(
    forecast: CapacityForecastV1,
    *,
    reset_at: datetime | None,
    observed_at: datetime | None = None,
    recorded_at: datetime | None = None,
) -> ForecastAlertConditionV1:
    """Only an entire bounded interval can have a definite reset relation."""
    earliest = forecast.earliest_exhaustion_at
    latest = forecast.latest_exhaustion_at
    before_reset = (
        True
        if latest is not None and reset_at is not None and latest < reset_at
        else False
        if earliest is not None and reset_at is not None and earliest >= reset_at
        else None
    )
    return ForecastAlertConditionV1(
        forecast.subject.resource_id,
        forecast.subject.account_id,
        forecast.window_id,
        forecast.generation,
        forecast.state,
        latest,
        earliest,
        latest,
        reset_at,
        before_reset,
        forecast.confidence,
        forecast.precision,
        forecast.input_observation_ids,
        forecast.reason_codes[0] if forecast.reason_codes else "forecast_available",
        observed_at,
        recorded_at or forecast.generated_at,
        forecast.valid_until,
    )


def _bounds(
    field: ExactMetricFieldV1,
    lower: ExactQuantityV1 | None,
    upper: ExactQuantityV1 | None,
) -> tuple[Decimal, Decimal] | None:
    if field.availability.state != "available" or field.value is None:
        return None
    value = field.value.as_decimal()
    if field.precision == "exact":
        return value, value
    if lower is None or upper is None:
        return None
    if lower.unit != field.value.unit or upper.unit != field.value.unit:
        return None
    left, right = lower.as_decimal(), upper.as_decimal()
    if not left <= value <= right:
        return None
    return max(Decimal(0), left), right


def _digest(
    samples: tuple[CapacityForecastSampleV1, ...], policy: CapacityForecastPolicyV1
) -> str:
    def quantity(value: ExactQuantityV1 | None) -> tuple[str, int, str] | None:
        return (
            None
            if value is None
            else (value.amount.coefficient, value.amount.scale, value.unit)
        )

    def metric(value: ExactMetricFieldV1) -> tuple[object, ...]:
        return (
            value.availability.state,
            quantity(value.value),
            value.precision,
            value.confidence,
            value.value_kind,
        )

    data = (
        policy.method_id,
        policy.method_version,
        policy.minimum_samples,
        policy.minimum_span_seconds,
        policy.maximum_gap_seconds,
        policy.maximum_samples,
        policy.maximum_horizon_seconds,
        tuple(
            (
                item.observation_id.value,
                item.window_definition_id.value,
                item.definition_version,
                item.subject.provider_key,
                item.subject.installation_id.value,
                item.subject.account_id.value,
                item.subject.resource_id.value,
                item.window_key,
                item.metric,
                item.observed_at.isoformat(),
                metric(item.consumed),
                metric(item.remaining),
                item.source_compatibility_id,
                item.reset_segment_id.value if item.reset_segment_id else None,
                item.reset_at.isoformat() if item.reset_at else None,
                item.freshness_deadline.isoformat()
                if item.freshness_deadline
                else None,
                quantity(item.lower_consumed_bound),
                quantity(item.upper_consumed_bound),
                quantity(item.lower_remaining_bound),
                quantity(item.upper_remaining_bound),
            )
            for item in samples
        ),
    )
    return hashlib.sha256(
        json.dumps(data, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def derive_capacity_forecast_v1(
    samples: tuple[CapacityForecastSampleV1, ...],
    *,
    policy: CapacityForecastPolicyV1,
    window_id: OpaqueIdV1,
    as_of: datetime,
) -> CapacityForecastV1:
    """Derive one explainable result; unknown evidence never creates a number."""
    if not samples:
        raise InvalidCapacityContractV1("capacity_forecast_samples_absent")
    if as_of.utcoffset() != timedelta(0):
        raise InvalidCapacityContractV1("capacity_forecast_time_invalid")
    ordered = tuple(
        sorted(samples, key=lambda p: (p.observed_at, p.observation_id.value))
    )
    digest = _digest(ordered, policy)
    latest = ordered[-1]
    base = CapacityForecastV1(
        forecast_id=OpaqueIdV1(
            hashlib.sha256((window_id.value + digest).encode()).hexdigest()
        ),
        generation=1,
        subject=latest.subject,
        window_id=window_id,
        window_definition_id=latest.window_definition_id,
        metric=latest.metric,
        state="insufficient_input",
        burn_rate=None,
        earliest_exhaustion_at=None,
        latest_exhaustion_at=None,
        reset_relation="unknown",
        confidence="unknown",
        precision="unknown",
        uncertainty_codes=(),
        reason_codes=(),
        input_observation_ids=tuple(p.observation_id for p in ordered),
        input_set_digest=digest,
        method_id=policy.method_id,
        method_version=policy.method_version,
        generated_at=as_of,
        valid_until=latest.freshness_deadline,
    )

    def unavailable(
        reason: str,
        state: Literal[
            "insufficient_input", "stale", "conflicted"
        ] = "insufficient_input",
    ) -> CapacityForecastV1:
        return replace(base, state=state, reason_codes=(reason,))

    if len(ordered) > policy.maximum_samples:
        return unavailable("too_many_samples")
    if any(p.observed_at > as_of for p in ordered):
        return unavailable("observation_after_query")
    by_time: dict[datetime, CapacityForecastSampleV1] = {}
    by_id: dict[OpaqueIdV1, CapacityForecastSampleV1] = {}
    for point in ordered:
        previous_time = by_time.get(point.observed_at)
        previous_id = by_id.get(point.observation_id)
        if previous_id is not None and previous_id != point:
            return unavailable("conflicting_observation_id", "conflicted")
        if previous_time is not None and (
            previous_time.consumed != point.consumed
            or previous_time.remaining != point.remaining
        ):
            return unavailable("conflicting_same_time_samples", "conflicted")
        by_time[point.observed_at] = point
        by_id[point.observation_id] = point
    unique = tuple(sorted(by_time.values(), key=lambda p: p.observed_at))
    if len(unique) < policy.minimum_samples:
        return unavailable("too_few_samples")
    if any(
        p.subject != latest.subject
        or p.window_key != latest.window_key
        or p.metric != latest.metric
        for p in unique
    ):
        return unavailable("incompatible_window")
    if any(
        p.window_definition_id != latest.window_definition_id
        or p.definition_version != latest.definition_version
        for p in unique
    ):
        return unavailable("incompatible_definition")
    if any(p.source_compatibility_id != latest.source_compatibility_id for p in unique):
        return unavailable("incompatible_source")
    if any(p.reset_segment_id is None for p in unique):
        return unavailable("reset_segment_unknown")
    if any(
        p.reset_segment_id != latest.reset_segment_id or p.reset_at != latest.reset_at
        for p in unique
    ):
        return unavailable("incompatible_reset_segment")
    if latest.freshness_deadline is None:
        return unavailable("freshness_unknown")
    if as_of >= latest.freshness_deadline:
        return unavailable("current_observation_stale", "stale")
    values = tuple(p.consumed.value for p in unique)
    if any(value is None for value in values) or latest.remaining.value is None:
        return unavailable("capacity_value_unknown")
    amounts = tuple(value.as_decimal() for value in values if value is not None)
    units = {value.unit for value in values if value is not None} | {
        latest.remaining.value.unit
    }
    if len(units) != 1:
        return unavailable("incompatible_unit")
    if any(right < left for left, right in zip(amounts, amounts[1:], strict=False)):
        return unavailable("consumption_decreased")
    if amounts[-1] <= amounts[0]:
        return unavailable("no_positive_consumption")
    span = _seconds(unique[-1].observed_at - unique[0].observed_at)
    if span < policy.minimum_span_seconds:
        return unavailable("insufficient_observation_span")
    if any(
        _seconds(right.observed_at - left.observed_at) > policy.maximum_gap_seconds
        for left, right in zip(unique, unique[1:], strict=False)
    ):
        return unavailable("observation_gap_too_large")
    consumed_bounds = tuple(
        _bounds(p.consumed, p.lower_consumed_bound, p.upper_consumed_bound)
        for p in unique
    )
    remaining_bounds = _bounds(
        latest.remaining, latest.lower_remaining_bound, latest.upper_remaining_bound
    )
    if any(bound is None for bound in consumed_bounds) or remaining_bounds is None:
        return unavailable("precision_bounds_unknown")
    first_bounds, last_bounds = consumed_bounds[0], consumed_bounds[-1]
    assert first_bounds is not None and last_bounds is not None
    with localcontext() as context:
        context.prec = 128
        quantum = Decimal("1e-18")
        estimate = ((amounts[-1] - amounts[0]) / span).quantize(
            quantum, rounding=ROUND_HALF_EVEN
        )
        lower = ((last_bounds[0] - first_bounds[1]) / span).quantize(
            quantum, rounding=ROUND_FLOOR
        )
        upper = ((last_bounds[1] - first_bounds[0]) / span).quantize(
            quantum, rounding=ROUND_CEILING
        )
        if lower <= 0 or upper <= 0:
            return unavailable("rate_uncertainty_too_large")
        earliest_seconds = int(
            (remaining_bounds[0] / upper).to_integral_value(rounding=ROUND_FLOOR)
        )
        latest_seconds = int(
            (remaining_bounds[1] / lower).to_integral_value(rounding=ROUND_CEILING)
        )
        if latest_seconds > policy.maximum_horizon_seconds:
            return unavailable("forecast_horizon_exceeded")
        earliest = latest.observed_at + timedelta(seconds=earliest_seconds)
        last = latest.observed_at + timedelta(seconds=latest_seconds)
        if last < as_of:
            return unavailable("forecast_projection_elapsed")
        unit = next(iter(units))
        rate = CapacityBurnRateV1(
            ExactQuantityV1.from_decimal(estimate, unit=unit),
            ExactQuantityV1.from_decimal(lower, unit=unit),
            ExactQuantityV1.from_decimal(upper, unit=unit),
            len(unique),
            CanonicalDecimalV1.from_decimal(span),
            tuple(p.observation_id for p in unique),
        )
    relation: Literal["before", "after", "unknown"] = (
        "before"
        if latest.reset_at is not None and latest.reset_at <= earliest
        else "after"
        if latest.reset_at is not None and latest.reset_at > last
        else "unknown"
    )
    return replace(
        base,
        state="available",
        burn_rate=rate,
        earliest_exhaustion_at=earliest,
        latest_exhaustion_at=last,
        reset_relation=relation,
        confidence="medium",
        precision="range" if earliest != last else "estimated",
        uncertainty_codes=("future_consumption_assumed_constant",),
    )

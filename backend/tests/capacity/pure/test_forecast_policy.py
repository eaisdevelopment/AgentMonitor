"""M4-CAP-P06..10: constructed domain values; no I/O or patched clock."""

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from agentmonitor.contracts import capacity_v1 as contracts
from agentmonitor.contracts.common_quantity_v1 import ExactQuantityV1
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.modules.capacity.application import queries

START = datetime(2026, 1, 1, tzinfo=UTC)


def _type(name: str) -> Any:
    result = getattr(contracts, name, None)
    assert result is not None, f"approved capacity contract {name} is unpublished"
    return result


def _field(
    value: str | int, *, precision: Any = "exact", unit: str = "requests"
) -> Any:
    return contracts.ExactMetricFieldV1(
        FieldAvailabilityV1("available"),
        ExactQuantityV1.from_decimal(Decimal(value), unit=unit),
        precision,
        "confirmed",
        "provider_reported",
        None,
    )


def _samples() -> Any:
    sample_type = _type("CapacityForecastSampleV1")
    subject = contracts.CapacitySubjectV1(
        "domain_provider",
        OpaqueIdV1("installation"),
        OpaqueIdV1("account"),
        OpaqueIdV1("resource"),
    )
    return tuple(
        sample_type(
            observation_id=OpaqueIdV1(f"observation_{index}"),
            window_definition_id=OpaqueIdV1("definition"),
            definition_version=1,
            subject=subject,
            window_key="native_window",
            metric="used",
            observed_at=START + timedelta(seconds=seconds),
            consumed=_field(consumed),
            remaining=_field(100 - consumed),
            source_compatibility_id="source_schema_v1",
            reset_segment_id=OpaqueIdV1("segment"),
            reset_at=START + timedelta(hours=3),
            freshness_deadline=START + timedelta(minutes=25),
            lower_consumed_bound=None,
            upper_consumed_bound=None,
            lower_remaining_bound=None,
            upper_remaining_bound=None,
        )
        for index, seconds, consumed in ((1, 0, 0), (2, 450, 9), (3, 900, 18))
    )


def _forecast(samples: Any = None, *, as_of: datetime | None = None) -> Any:
    derive = getattr(queries, "derive_capacity_forecast_v1", None)
    assert callable(derive), "approved pure capacity forecast behavior is absent"
    selected = _samples() if samples is None else samples
    return derive(
        selected,
        policy=_type("CapacityForecastPolicyV1")(),
        window_id=OpaqueIdV1("window"),
        as_of=max(p.observed_at for p in selected) if as_of is None else as_of,
    )


def test_exact_linear_consumption_has_explained_rate_and_exhaustion() -> None:
    samples = _samples()
    result = _forecast(samples)
    assert result.state == "available"
    assert result.burn_rate.estimate.as_decimal() == Decimal("0.02")
    assert result.burn_rate.time_basis == "second"
    assert result.earliest_exhaustion_at == START + timedelta(seconds=5000)
    assert result.latest_exhaustion_at == result.earliest_exhaustion_at
    assert result.input_observation_ids == tuple(p.observation_id for p in samples)
    assert result.confidence == "medium"
    assert result.reset_relation == "after"
    assert "future_consumption_assumed_constant" in result.uncertainty_codes


@pytest.mark.parametrize(
    "reason,change",
    [
        ("too_few_samples", lambda s: s[:2]),
        (
            "insufficient_observation_span",
            lambda s: tuple(
                replace(p, observed_at=START + timedelta(seconds=i * 100))
                for i, p in enumerate(s)
            ),
        ),
        (
            "observation_gap_too_large",
            lambda s: (
                s[:2] + (replace(s[-1], observed_at=START + timedelta(seconds=1400)),)
            ),
        ),
        (
            "reset_segment_unknown",
            lambda s: tuple(replace(p, reset_segment_id=None) for p in s),
        ),
        (
            "incompatible_reset_segment",
            lambda s: (
                s[:2] + (replace(s[-1], reset_segment_id=OpaqueIdV1("other_segment")),)
            ),
        ),
        (
            "incompatible_source",
            lambda s: (
                s[:2] + (replace(s[-1], source_compatibility_id="source_schema_v2"),)
            ),
        ),
        (
            "incompatible_definition",
            lambda s: s[:2] + (replace(s[-1], definition_version=2),),
        ),
        (
            "consumption_decreased",
            lambda s: s[:2] + (replace(s[-1], consumed=_field(2)),),
        ),
        (
            "no_positive_consumption",
            lambda s: tuple(replace(p, consumed=_field(0)) for p in s),
        ),
        (
            "precision_bounds_unknown",
            lambda s: tuple(
                replace(p, consumed=replace(p.consumed, precision="rounded")) for p in s
            ),
        ),
    ],
)
def test_insufficient_inputs_never_invent_numeric_forecast(
    reason: str, change: Callable[[Any], Any]
) -> None:
    result = _forecast(change(_samples()))
    assert result.state == "insufficient_input"
    assert reason in result.reason_codes
    assert result.burn_rate is None
    assert result.earliest_exhaustion_at is None
    assert result.latest_exhaustion_at is None


def test_freshness_deadline_equality_invalidates_forecast() -> None:
    result = _forecast(as_of=START + timedelta(minutes=25))
    assert result.state == "stale"
    assert "current_observation_stale" in result.reason_codes
    assert result.burn_rate is None


def test_equal_time_conflict_is_not_an_arbitrary_winner() -> None:
    samples = _samples()
    conflicting = replace(
        samples[-1], observation_id=OpaqueIdV1("conflict"), consumed=_field(19)
    )
    result = _forecast(samples + (conflicting,))
    assert result.state == "conflicted"
    assert "conflicting_same_time_samples" in result.reason_codes


def test_native_unit_mismatch_cannot_be_forecast() -> None:
    samples = _samples()
    result = _forecast(
        samples[:2] + (replace(samples[-1], consumed=_field(18, unit="tokens")),)
    )
    assert result.state == "insufficient_input"
    assert "incompatible_unit" in result.reason_codes


def test_known_rounding_bounds_yield_outward_uncertainty_range() -> None:
    samples = tuple(
        replace(
            p,
            consumed=replace(p.consumed, precision="rounded"),
            remaining=replace(p.remaining, precision="rounded"),
            lower_consumed_bound=ExactQuantityV1.from_decimal(
                p.consumed.value.as_decimal() - Decimal("0.5"), unit="requests"
            ),
            upper_consumed_bound=ExactQuantityV1.from_decimal(
                p.consumed.value.as_decimal() + Decimal("0.5"), unit="requests"
            ),
            lower_remaining_bound=ExactQuantityV1.from_decimal(
                p.remaining.value.as_decimal() - Decimal("0.5"), unit="requests"
            ),
            upper_remaining_bound=ExactQuantityV1.from_decimal(
                p.remaining.value.as_decimal() + Decimal("0.5"), unit="requests"
            ),
        )
        for p in _samples()
    )
    result = _forecast(samples)
    assert result.state == "available"
    assert result.earliest_exhaustion_at < START + timedelta(seconds=5000)
    assert result.latest_exhaustion_at > START + timedelta(seconds=5000)
    assert result.precision == "range"
    assert result.burn_rate.lower_bound.as_decimal() < Decimal("0.02")
    assert result.burn_rate.upper_bound.as_decimal() > Decimal("0.02")


def test_reset_before_exhaustion_is_explicit() -> None:
    result = _forecast(
        tuple(replace(p, reset_at=START + timedelta(seconds=2000)) for p in _samples())
    )
    assert result.state == "available"
    assert result.reset_relation == "before"


def test_current_forecast_selects_latest_evidenced_segment_without_old_rate() -> None:
    from agentmonitor.modules.capacity.domain import forecast as domain

    select = getattr(domain, "select_latest_compatible_suffix_v1", None)
    assert callable(select), "current forecast lacks reset-preserving suffix selection"
    recent = _samples()
    older = replace(
        recent[0],
        observation_id=OpaqueIdV1("older_observation"),
        observed_at=START - timedelta(minutes=1),
        reset_segment_id=OpaqueIdV1("previous_segment"),
    )
    assert select((older,) + recent) == recent


def test_current_forecast_alert_requires_whole_interval_before_exact_reset() -> None:
    from agentmonitor.modules.capacity.domain import forecast as domain

    derive = getattr(domain, "derive_forecast_alert_condition_v1", None)
    assert callable(derive), "durable forecast alert condition is absent"
    forecast = _forecast()
    safe = derive(forecast, reset_at=START + timedelta(hours=3))
    assert safe.before_reset is True
    assert safe.exhaustion_at == forecast.latest_exhaustion_at
    crossing = derive(
        forecast,
        reset_at=forecast.latest_exhaustion_at,
    )
    assert crossing.before_reset is False
    unknown = derive(forecast, reset_at=None)
    assert unknown.before_reset is None

"""Pure percentage derivation inputs; no constructed value reaches any I/O."""

from decimal import Decimal

import pytest
from agentmonitor.contracts.capacity_v1 import ExactMetricFieldV1
from agentmonitor.contracts.common_quantity_v1 import ExactQuantityV1
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1
from agentmonitor.modules.capacity.domain.allowance import remaining_percentage_v1


def _unknown() -> ExactMetricFieldV1:
    return ExactMetricFieldV1(
        FieldAvailabilityV1("unknown"),
        None,
        "unknown",
        "unknown",
        "unknown",
        "source_does_not_report_value",
    )


def _percent(
    value: str, *, stale: bool = False, unit: str = "percent"
) -> ExactMetricFieldV1:
    return ExactMetricFieldV1(
        FieldAvailabilityV1("stale" if stale else "available"),
        ExactQuantityV1.from_decimal(Decimal(value), unit=unit),
        "rounded",
        "confirmed",
        "provider_reported",
        None,
    )


@pytest.mark.parametrize(
    ("used", "expected"), [("0", "100"), ("100", "0"), ("37.25", "62.75")]
)
def test_used_percent_complement_preserves_precision_and_confidence(
    used: str, expected: str
) -> None:
    result = remaining_percentage_v1(_percent(used), _unknown())
    assert result is not None
    metric, method = result
    assert method == "100_minus_used_percent"
    assert metric.value is not None and metric.value.as_decimal() == Decimal(expected)
    assert metric.value.unit == "percent"
    assert metric.precision == "rounded" and metric.confidence == "confirmed"
    assert metric.value_kind == "derived"


def test_reported_remaining_ratio_takes_precedence() -> None:
    result = remaining_percentage_v1(_percent("20"), _percent("0.3", unit="ratio"))
    assert result is not None
    metric, method = result
    assert metric.value is not None and metric.value.as_decimal() == Decimal(30)
    assert method == "remaining_ratio_times_100"


def test_stale_input_stays_stale() -> None:
    result = remaining_percentage_v1(_percent("25", stale=True), _unknown())
    assert result is not None and result[0].availability.state == "stale"


@pytest.mark.parametrize(
    ("value", "unit"), [("-1", "percent"), ("101", "percent"), ("20", "token")]
)
def test_invalid_used_percentage_does_not_produce_an_allowance(
    value: str, unit: str
) -> None:
    assert remaining_percentage_v1(_percent(value, unit=unit), _unknown()) is None


def test_unavailable_inputs_stay_unavailable() -> None:
    assert remaining_percentage_v1(_unknown(), _unknown()) is None

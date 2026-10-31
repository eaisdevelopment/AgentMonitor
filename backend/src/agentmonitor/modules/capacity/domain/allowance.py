"""Pure per-window percentage presentation; no health or account aggregation."""

from decimal import Decimal
from typing import Literal

from agentmonitor.contracts.capacity_v1 import ExactMetricFieldV1
from agentmonitor.contracts.common_quantity_v1 import ExactQuantityV1


def remaining_percentage_v1(
    used: ExactMetricFieldV1,
    remaining_ratio: ExactMetricFieldV1,
) -> (
    tuple[
        ExactMetricFieldV1,
        Literal["remaining_ratio_times_100", "100_minus_used_percent"],
    ]
    | None
):
    for source, unit, maximum in (
        (remaining_ratio, "ratio", Decimal(1)),
        (used, "percent", Decimal(100)),
    ):
        if (
            source.availability.state not in {"available", "stale"}
            or source.value is None
        ):
            continue
        if source.value.unit != unit:
            continue
        value = source.value.as_decimal()
        if not 0 <= value <= maximum:
            continue
        percentage = value * 100 if unit == "ratio" else Decimal(100) - value
        method: Literal["remaining_ratio_times_100", "100_minus_used_percent"] = (
            "remaining_ratio_times_100" if unit == "ratio" else "100_minus_used_percent"
        )
        return ExactMetricFieldV1(
            source.availability,
            ExactQuantityV1.from_decimal(percentage, unit="percent"),
            source.precision,
            source.confidence,
            "derived",
            None,
        ), method
    return None

"""Pure producer facts from current native ratio evidence."""

from datetime import datetime
from decimal import Decimal, localcontext
from typing import Literal

from agentmonitor.contracts.capacity_v1 import (
    CapacityAlertAvailabilityV1,
    CapacityAlertConditionV1,
    CapacityAlertReasonV1,
    InvalidCapacityContractV1,
    QuotaWindowViewV1OrV2,
)
from agentmonitor.contracts.common_quantity_v1 import CanonicalDecimalV1
from agentmonitor.modules.capacity.domain.allowance import remaining_percentage_v1


def derive_capacity_alert_condition_v1(
    window: QuotaWindowViewV1OrV2, *, as_of: datetime
) -> CapacityAlertConditionV1:
    """Only fresh complete native allowance evidence can activate or recover."""
    if window.projection_version is None or window.projection_version < 1:
        raise InvalidCapacityContractV1("capacity_projection_generation_unknown")
    ratio = window.remaining_ratio
    allowance = remaining_percentage_v1(window.used, ratio)
    denominator: Literal["remaining_ratio", "used_percent_complement", "unknown"] = (
        "unknown"
        if allowance is None
        else "remaining_ratio"
        if allowance[1] == "remaining_ratio_times_100"
        else "used_percent_complement"
    )
    deadline = window.provenance.freshness_deadline
    availability: CapacityAlertAvailabilityV1 = "unknown"
    reason: CapacityAlertReasonV1 = "capacity_ratio_unknown"
    if window.is_constraining is False:
        availability, reason = "unavailable", "capacity_ratio_unavailable"
    elif window.freshness == "conflicted":
        reason = "capacity_reading_conflicted"
    elif window.freshness == "stale" or deadline is not None and as_of >= deadline:
        availability, reason = "stale", "capacity_reading_stale"
    elif window.freshness != "fresh" or deadline is None:
        reason = "capacity_freshness_unknown"
    elif window.completeness != "complete":
        reason = "capacity_reading_partial"
    elif allowance is not None and allowance[0].availability.state == "available":
        availability = "current"
        reason = (
            "capacity_ratio_current"
            if denominator == "remaining_ratio"
            else "capacity_used_percent_current"
        )
    elif allowance is not None and allowance[0].availability.state == "stale":
        availability, reason = "stale", "capacity_reading_stale"
    elif ratio.availability.state == "unsupported":
        availability, reason = "unsupported", "capacity_ratio_unsupported"
    elif ratio.availability.state in {"withheld_or_denied", "not_applicable"}:
        availability, reason = "unavailable", "capacity_ratio_unavailable"
    elif ratio.availability.state == "stale":
        availability, reason = "stale", "capacity_reading_stale"
    basis_points = None
    exhausted = None
    if (
        availability == "current"
        and allowance is not None
        and allowance[0].value is not None
    ):
        with localcontext() as context:
            context.prec = 128
            basis_points = CanonicalDecimalV1.from_decimal(
                allowance[0].value.as_decimal() * Decimal(100)
            )
        exhausted = allowance[0].value.as_decimal() == 0
    return CapacityAlertConditionV1(
        window.subject.resource_id,
        window.subject.account_id,
        window.subject.provider_key,
        window.window_id,
        window.projection_version,
        basis_points,
        denominator,
        availability,
        exhausted,
        window.reset_at,
        deadline,
        (window.current_observation_id,),
        allowance[0].precision if allowance is not None else ratio.precision,
        allowance[0].confidence if allowance is not None else ratio.confidence,
        reason,
        window.observed_at,
        window.stored_at,
    )

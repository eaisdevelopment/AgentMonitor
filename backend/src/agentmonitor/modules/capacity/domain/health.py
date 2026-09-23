"""Pure M05 capacity-health classification over exact normalized inputs."""

from dataclasses import dataclass
from typing import Literal

from agentmonitor.contracts.capacity_v1 import (
    CapacityHealthPolicyV1,
    CapacityHealthStateV1,
    CapacityHealthViewV1,
)
from agentmonitor.contracts.common_quantity_v1 import CanonicalDecimalV1

FreshnessV1 = Literal["fresh", "stale", "freshness_unknown", "conflicted"]


@dataclass(frozen=True, slots=True)
class CapacityConstraintInputV1:
    window_id: str
    remaining_ratio: CanonicalDecimalV1 | None
    freshness: FreshnessV1
    is_constraining: bool


def classify_capacity_health(
    inputs: tuple[CapacityConstraintInputV1, ...],
    *,
    policy: CapacityHealthPolicyV1,
    is_reauthentication_required: bool = False,
) -> CapacityHealthViewV1:
    if is_reauthentication_required:
        return CapacityHealthViewV1(
            state="reauthentication_required",
            completeness="unknown",
            freshness="freshness_unknown",
            constraining_window_id=None,
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            explanation_codes=("provider_reauthentication_required",),
        )
    constraints = tuple(item for item in inputs if item.is_constraining)
    known = tuple(
        item
        for item in constraints
        if item.remaining_ratio is not None and item.freshness == "fresh"
    )
    unresolved = tuple(item for item in constraints if item not in known)
    if not known:
        freshness: FreshnessV1 = (
            "conflicted"
            if any(item.freshness == "conflicted" for item in unresolved)
            else "stale"
            if any(item.freshness == "stale" for item in unresolved)
            else "freshness_unknown"
        )
        return CapacityHealthViewV1(
            state="unknown",
            completeness="unknown" if not constraints else "partial",
            freshness=freshness,
            constraining_window_id=None,
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            explanation_codes=("no_trustworthy_constraint",),
        )
    constraining = min(known, key=lambda item: item.remaining_ratio.as_decimal())  # type: ignore[union-attr]
    ratio = constraining.remaining_ratio.as_decimal()  # type: ignore[union-attr]
    if ratio == 0:
        state: CapacityHealthStateV1 = "exhausted"
    elif ratio <= policy.critical_remaining_ratio.as_decimal():
        state = "critical"
    elif ratio <= policy.constrained_remaining_ratio.as_decimal():
        state = "constrained"
    else:
        state = "available"
    if unresolved and state == "available":
        state = "unknown"
        constraining_id = None
    else:
        constraining_id = constraining.window_id
    return CapacityHealthViewV1(
        state=state,
        completeness="partial" if unresolved else "complete",
        freshness="freshness_unknown" if unresolved else "fresh",
        constraining_window_id=constraining_id,
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
        explanation_codes=(
            "incomplete_constraints" if unresolved else "lowest_remaining_ratio",
        ),
    )

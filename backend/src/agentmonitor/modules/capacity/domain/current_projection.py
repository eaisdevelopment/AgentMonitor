"""Pure source-evidence policy for M05 current capability availability."""

from typing import Literal

from agentmonitor.contracts.capacity_v1 import CapacityAvailabilityStateV1


def classify_capability_availability_v1(
    freshness: Literal[
        "fresh", "stale", "freshness_unknown", "conflicted", "no_observation"
    ],
    completeness: Literal["complete", "partial", "unknown"],
    metric_state: str,
    *,
    identity_bound: bool,
) -> tuple[CapacityAvailabilityStateV1, str]:
    """Do not infer provider failure or recovery from a missing quota value."""
    if freshness == "conflicted":
        return "unknown", "capability_reading_conflicted"
    if freshness == "stale":
        return "stale", "capability_reading_stale"
    if freshness != "fresh":
        return "unknown", "capability_freshness_unknown"
    if completeness == "partial":
        return "unknown", "capability_reading_partial"
    if completeness != "complete":
        return "unknown", "capability_completeness_unknown"
    if not identity_bound:
        return "unknown", "identity_binding_unproven"
    if metric_state == "available":
        return "available", "capability_observed_current"
    if metric_state == "unsupported":
        return "unsupported", "capability_metric_unsupported"
    if metric_state == "withheld_or_denied":
        return "withheld_or_denied", "capability_metric_withheld"
    return "unknown", "capability_metric_unknown"

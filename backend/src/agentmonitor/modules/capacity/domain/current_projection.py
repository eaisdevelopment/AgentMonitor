"""Pure source-evidence policy for M05 current capability availability."""

from datetime import datetime
from typing import Literal

from agentmonitor.contracts.capacity_v1 import CapacityAvailabilityStateV1

WindowIdentityScopeV1 = tuple[str, str, str, str, str, int]
WindowLifecycleV1 = Literal["active", "not_observed_currently", "retired"]


def omitted_current_window_keys_v1(
    current_window_keys: tuple[str, ...],
    observed_window_keys: tuple[str, ...],
    *,
    completeness: Literal["complete_scope", "partial_scope"],
    current_lifecycle: WindowLifecycleV1,
    current_semantic_at: datetime,
    incoming_semantic_at: datetime,
    identity_scheme_proven: bool,
    current_scope: WindowIdentityScopeV1,
    incoming_scope: WindowIdentityScopeV1,
) -> tuple[str, ...]:
    """Select absent keys only when one complete observation is strictly newer."""
    if (
        completeness != "complete_scope"
        or current_lifecycle not in {"active", "not_observed_currently"}
        or not identity_scheme_proven
        or current_scope != incoming_scope
        or incoming_semantic_at <= current_semantic_at
    ):
        return ()
    return tuple(sorted(set(current_window_keys) - set(observed_window_keys)))


def current_window_candidate_wins_v1(
    *,
    current_semantic_at: datetime | None,
    lifecycle_semantic_at: datetime | None,
    incoming_semantic_at: datetime,
) -> bool:
    """Advance presence only beyond both current and lifecycle watermarks."""

    watermark = current_window_lifecycle_semantic_v1(
        current_semantic_at,
        lifecycle_semantic_at,
    )
    return watermark is None or incoming_semantic_at > watermark


def current_window_lifecycle_semantic_v1(
    *semantic_times: datetime | None,
) -> datetime | None:
    """Carry the newest presence or absence time across definition versions."""

    known = tuple(value for value in semantic_times if value is not None)
    return max(known) if known else None


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

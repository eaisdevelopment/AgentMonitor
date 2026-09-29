"""Pure M04 current condition policy; no clock, provider or persistence import."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from agentmonitor.contracts.collection_control_v1 import (
    CollectorAlertConditionV1,
    CollectorConditionReasonV1,
    CollectorFreshnessStateV1,
    CollectorHealthStateV1,
    CollectorRetryCategoryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1, TechnicalValueV1


@dataclass(frozen=True, slots=True)
class CollectorRunFactV1(TechnicalValueV1):
    run_id: OpaqueIdV1
    record_version: int
    target_generation: int
    state: str
    completed_at: datetime | None
    provider_outcome: str | None
    retry_disposition: str | None
    retry_after: datetime | None
    has_committed_references: bool


@dataclass(frozen=True, slots=True)
class CollectorSourceSnapshotV1(TechnicalValueV1):
    target_id: OpaqueIdV1
    account_id: OpaqueIdV1 | None
    provider_key: str
    capability_id: str
    schedule_record_version: int
    target_generation: int
    schedule_state: str
    effective_interval_seconds: int
    not_before_at: datetime | None
    backoff_kind: str | None
    latest_run: CollectorRunFactV1 | None
    last_success: CollectorRunFactV1 | None


def classify_collector_condition_v1(
    source: CollectorSourceSnapshotV1, *, generation: int, as_of: datetime
) -> CollectorAlertConditionV1:
    health: CollectorHealthStateV1 = "unknown"
    freshness: CollectorFreshnessStateV1 = "unknown"
    category: CollectorRetryCategoryV1 = "unclassified"
    reason: CollectorConditionReasonV1 = "collector_no_success"
    successful_at: datetime | None = None
    deadline: datetime | None = None
    latest = source.latest_run
    success = source.last_success
    if (
        success is not None
        and success.state == "succeeded"
        and success.has_committed_references
        and success.target_generation == source.target_generation
        and success.completed_at is not None
        and success.completed_at <= as_of
    ):
        successful_at = success.completed_at
        deadline = successful_at + timedelta(seconds=source.effective_interval_seconds)
        freshness = "current" if as_of < deadline else "stale"
    if source.schedule_state in {"paused_monitoring_disabled", "retired"}:
        health, freshness, category, reason = (
            "paused",
            "not_applicable",
            "none",
            "collector_paused",
        )
    elif source.schedule_state == "unsupported" or (
        latest is not None and latest.state == "unsupported"
    ):
        health, freshness, category, reason = (
            "unsupported",
            "unsupported",
            "unsupported",
            "collector_unsupported",
        )
    elif latest is not None and (
        latest.target_generation != source.target_generation
        or latest.completed_at is None
        or latest.completed_at > as_of
    ):
        health, freshness, reason = (
            "unknown",
            "unknown",
            "collector_clock_invalid"
            if latest.completed_at is not None and latest.completed_at > as_of
            else "collector_source_unknown",
        )
    elif source.schedule_state.startswith("blocked_") or (
        latest is not None and latest.state == "blocked"
    ):
        health, reason = "blocked", "collector_blocked_unclassified"
        mapping: dict[
            str, tuple[CollectorRetryCategoryV1, CollectorConditionReasonV1]
        ] = {
            "blocked_authentication": (
                "authentication",
                "collector_blocked_authentication",
            ),
            "blocked_user_action": ("user_action", "collector_blocked_user_action"),
            "blocked_compatibility": (
                "compatibility",
                "collector_blocked_compatibility",
            ),
            "blocked_unknown_constraints": (
                "unknown_constraints",
                "collector_blocked_unknown_constraints",
            ),
            "reauthentication_required": (
                "authentication",
                "collector_blocked_authentication",
            ),
            "authorization_insufficient": (
                "authorization",
                "collector_blocked_authorization",
            ),
            "blocked_user_action_required": (
                "user_action",
                "collector_blocked_user_action",
            ),
            "unverified_provider_version": (
                "compatibility",
                "collector_blocked_compatibility",
            ),
        }
        category, reason = mapping.get(
            source.schedule_state,
            mapping.get(
                (latest.provider_outcome or "") if latest else "",
                ("unclassified", reason),
            ),
        )
    elif latest is not None:
        if latest.state == "succeeded" and latest.has_committed_references:
            health, category, reason = "healthy", "none", "collector_healthy"
        elif latest.state == "partial":
            health, reason = "degraded", "collector_partial"
        elif latest.state == "failed":
            health, reason = "failed", "collector_failed"
            if (
                source.not_before_at is not None
                and source.not_before_at > as_of
                and latest.retry_disposition == "after_delay"
                and latest.retry_after is not None
                and source.not_before_at >= latest.retry_after
            ):
                if latest.provider_outcome == "rate_limited":
                    health, category, reason = (
                        "backoff",
                        "rate_backoff",
                        "collector_rate_backoff",
                    )
                elif latest.provider_outcome in {
                    "provider_unavailable",
                    "deadline_exceeded",
                }:
                    health, category, reason = (
                        "backoff",
                        "transient_backoff",
                        "collector_transient_backoff",
                    )
        elif latest.state == "cancelled":
            health, category, reason = "unknown", "cancelled", "collector_cancelled"
    if health != "healthy" and freshness == "current":
        freshness = "unknown"
    if freshness == "stale" and health == "healthy":
        reason = "collector_stale"
    return CollectorAlertConditionV1(
        source.target_id,
        source.account_id,
        source.provider_key,
        source.capability_id,
        generation,
        health,
        freshness,
        category,
        latest.run_id if latest else None,
        successful_at,
        deadline,
        source.not_before_at,
        as_of,
        reason,
    )

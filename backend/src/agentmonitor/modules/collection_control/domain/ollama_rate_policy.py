"""Pure single-instance Ollama cloud request spacing policy.

Persistence and atomic admission are separate responsibilities: this function
alone does not prevent concurrent requests or enforce a provider's rate limit.
"""

from datetime import UTC, datetime, timedelta
from typing import Literal

_MIN_SPACING_SECONDS = 60
_MAX_BACKOFF_SECONDS = 300
_MAX_JITTER_SECONDS = 10


def next_cloud_work_lane(
    last_was_verification: bool | None,
) -> Literal["verification", "scheduled"]:
    """Alternate from durable last admission, including across worker restarts."""
    if last_was_verification is not None and type(last_was_verification) is not bool:
        raise ValueError("ollama_cloud_lane_invalid")
    return "scheduled" if last_was_verification else "verification"


def after_ollama_attempt(
    started_at: datetime,
    consecutive_rate_limits: int,
    retry_after_seconds: int | None,
    jitter_seconds: int,
    *,
    response_received_at: datetime,
) -> datetime:
    """Calculate a next start, preserving longer provider-directed waits."""
    if not isinstance(started_at, datetime) or not isinstance(
        response_received_at, datetime
    ):
        raise ValueError("ollama_rate_time_invalid")
    if started_at.utcoffset() is None or response_received_at.utcoffset() is None:
        raise ValueError("ollama_rate_time_requires_timezone")
    started_at = started_at.astimezone(UTC)
    response_received_at = response_received_at.astimezone(UTC)
    if response_received_at < started_at:
        raise ValueError("ollama_rate_time_order_invalid")
    if (
        type(consecutive_rate_limits) is not int
        or not 0 <= consecutive_rate_limits <= 100
    ):
        raise ValueError("ollama_rate_count_invalid")
    if (
        type(jitter_seconds) is not int
        or not 0 <= jitter_seconds <= _MAX_JITTER_SECONDS
    ):
        raise ValueError("ollama_rate_jitter_invalid")
    if retry_after_seconds is not None and (
        type(retry_after_seconds) is not int or retry_after_seconds < 0
    ):
        raise ValueError("ollama_retry_after_invalid")
    fallback = (
        min(_MAX_BACKOFF_SECONDS, 2 ** min(consecutive_rate_limits, 9))
        if consecutive_rate_limits
        else 0
    )
    try:
        minimum = started_at + timedelta(seconds=_MIN_SPACING_SECONDS)
        provider_wait = response_received_at + timedelta(
            seconds=max(retry_after_seconds or 0, fallback)
        )
        return max(minimum, provider_wait) + timedelta(seconds=jitter_seconds)
    except OverflowError as exc:
        # The caller must block admission; an unrepresentable provider wait is
        # not an invalid header that can fall back to a shorter delay.
        raise ValueError("ollama_rate_wait_unrepresentable") from exc


def reserve_after_lease(lease_expires_at: datetime, jitter_seconds: int) -> datetime:
    """Space next admission after the latest allowed request dispatch."""
    return after_ollama_attempt(
        lease_expires_at,
        0,
        None,
        jitter_seconds,
        response_received_at=lease_expires_at,
    )


def cloud_schedule_generation_action(
    current: int, proposed: int, active_work: bool
) -> str:
    """Advance a stable schedule only when no prior generation is in flight."""
    if (
        type(current) is not int
        or type(proposed) is not int
        or current < 1
        or proposed < 1
        or type(active_work) is not bool
        or proposed < current
    ):
        raise ValueError("ollama_cloud_schedule_conflict")
    if proposed == current:
        return "unchanged"
    if active_work:
        raise ValueError("ollama_cloud_schedule_busy")
    return "advance"


def after_unknown_ollama_attempt(
    known_deadline: datetime,
    recovered_at: datetime,
    jitter_seconds: int,
    *,
    verification_job_state: str | None = None,
) -> datetime | None:
    """Wait the full fallback cap after recovery without erasing known waits.

    This is a local retry policy for an unknown response, never evidence of a
    provider response, absence of throttling, or a provider-directed deadline.
    """
    if (
        known_deadline.utcoffset() != timedelta(0)
        or recovered_at.utcoffset() != timedelta(0)
        or type(jitter_seconds) is not int
        or not 0 <= jitter_seconds <= _MAX_JITTER_SECONDS
    ):
        raise ValueError("ollama_unknown_recovery_invalid")
    if verification_job_state is not None:
        return None
    try:
        return max(
            known_deadline, recovered_at + timedelta(seconds=_MAX_BACKOFF_SECONDS)
        ) + timedelta(seconds=jitter_seconds)
    except OverflowError:
        raise ValueError("ollama_rate_wait_unrepresentable") from None


def ollama_lease_time_allows_action(
    started_at: datetime,
    expires_at: datetime,
    observed_at: datetime,
    *,
    conservative_hold: bool = False,
) -> bool:
    """Check lease time; a conservative hold never grants dispatch or commit."""
    return (
        all(
            value.utcoffset() == timedelta(0)
            for value in (started_at, expires_at, observed_at)
        )
        and started_at <= expires_at
        and started_at <= observed_at
        and (conservative_hold or observed_at <= expires_at)
    )


def ollama_completion_time_allows_record(
    started_at: datetime,
    expires_at: datetime,
    received_at: datetime,
    recorded_at: datetime,
    outcome: str,
) -> bool:
    """Fence response time without discarding an observed provider restriction."""
    return (
        all(
            value.utcoffset() == timedelta(0)
            for value in (started_at, expires_at, received_at, recorded_at)
        )
        and started_at <= expires_at
        and started_at <= received_at <= recorded_at
        and (
            outcome == "rate_limited"
            or (received_at <= expires_at and recorded_at <= expires_at)
        )
    )

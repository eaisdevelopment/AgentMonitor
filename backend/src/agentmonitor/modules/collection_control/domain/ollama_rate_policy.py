"""Pure single-instance Ollama cloud request spacing policy.

Persistence and atomic admission are separate responsibilities: this function
alone does not prevent concurrent requests or enforce a provider's rate limit.
"""

from datetime import datetime, timedelta

_MIN_SPACING_SECONDS = 60
_MAX_BACKOFF_SECONDS = 300
_MAX_JITTER_SECONDS = 10


def after_ollama_attempt(
    started_at: datetime,
    consecutive_rate_limits: int,
    retry_after_seconds: int | None,
    jitter_seconds: int,
) -> datetime:
    """Calculate a next start, preserving longer provider-directed waits."""
    if started_at.utcoffset() is None:
        raise ValueError("ollama_rate_time_requires_timezone")
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
        type(retry_after_seconds) is not int or not 0 <= retry_after_seconds <= 2678400
    ):
        raise ValueError("ollama_retry_after_invalid")
    fallback = (
        min(_MAX_BACKOFF_SECONDS, 2 ** min(consecutive_rate_limits, 9))
        if consecutive_rate_limits
        else 0
    )
    delay = max(_MIN_SPACING_SECONDS, retry_after_seconds or 0, fallback)
    return started_at + timedelta(seconds=delay + jitter_seconds)

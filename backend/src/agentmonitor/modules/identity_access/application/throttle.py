"""Pure installation-global login throttle transitions; persistence owns atomicity."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import ceil

WINDOW_SECONDS = 900
MAX_FAILURES = 5
INITIAL_LOCK_SECONDS = 30
MAX_LOCK_SECONDS = 900


@dataclass(frozen=True, slots=True)
class LoginThrottleStateV1:
    window_started_at: datetime
    failure_count: int
    consecutive_lock_count: int
    locked_until: datetime | None


def retry_after_seconds(state: LoginThrottleStateV1, as_of: datetime) -> int:
    """Bounded HTTP Retry-After; zero means a verifier may be admitted."""
    if state.locked_until is None or as_of >= state.locked_until:
        return 0
    seconds = ceil((state.locked_until - as_of).total_seconds())
    return min(MAX_LOCK_SECONDS, max(1, seconds))


def after_failed_login(
    state: LoginThrottleStateV1, as_of: datetime
) -> LoginThrottleStateV1:
    """An expired lock retains its threshold count inside the active window."""
    if retry_after_seconds(state, as_of):
        return state
    expired_window = as_of >= state.window_started_at + timedelta(
        seconds=WINDOW_SECONDS
    )
    window_start = as_of if expired_window else state.window_started_at
    failures = (0 if expired_window else state.failure_count) + 1
    if failures < MAX_FAILURES:
        return LoginThrottleStateV1(
            window_start, failures, state.consecutive_lock_count, None
        )
    lock_count = state.consecutive_lock_count + 1
    duration = min(MAX_LOCK_SECONDS, INITIAL_LOCK_SECONDS * 2 ** min(lock_count - 1, 5))
    return LoginThrottleStateV1(
        window_start, failures, lock_count, as_of + timedelta(seconds=duration)
    )


def after_successful_login(
    state: LoginThrottleStateV1, as_of: datetime
) -> LoginThrottleStateV1:
    """Only verified success resets both failure and consecutive-lock history."""
    return LoginThrottleStateV1(as_of, 0, 0, None)

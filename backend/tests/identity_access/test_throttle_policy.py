"""Pure deterministic global login-throttle transitions."""

from datetime import UTC, datetime, timedelta

from agentmonitor.modules.identity_access.application.throttle import (
    LoginThrottleStateV1,
    after_failed_login,
    after_successful_login,
    retry_after_seconds,
)


def test_five_failures_lock_for_30_seconds_then_next_lock_doubles() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    state = LoginThrottleStateV1(start, 0, 0, None)
    for index in range(4):
        state = after_failed_login(state, start + timedelta(seconds=index))
        assert state.locked_until is None
    state = after_failed_login(state, start + timedelta(seconds=4))
    assert state.failure_count == 5
    assert state.consecutive_lock_count == 1
    assert state.locked_until == start + timedelta(seconds=34)
    assert retry_after_seconds(state, start + timedelta(seconds=5)) == 29
    assert retry_after_seconds(state, state.locked_until) == 0
    state = after_failed_login(state, start + timedelta(seconds=35))
    assert state.consecutive_lock_count == 2
    assert state.locked_until == start + timedelta(seconds=95)


def test_success_resets_window_and_consecutive_locks() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    state = LoginThrottleStateV1(start, 0, 0, None)
    for index in range(5):
        state = after_failed_login(state, start + timedelta(seconds=index))
    cleared = after_successful_login(state, start + timedelta(seconds=34))
    assert cleared.failure_count == 0
    assert cleared.consecutive_lock_count == 0
    assert cleared.locked_until is None

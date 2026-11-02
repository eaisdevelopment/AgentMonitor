"""Pure M6 cloud scheduling rules; no provider calls or clock I/O."""

from datetime import UTC, datetime, timedelta

from agentmonitor.modules.collection_control.domain.ollama_rate_policy import (
    after_ollama_attempt,
)


def test_success_keeps_at_least_one_minute_between_cloud_starts():
    started = datetime(2026, 11, 2, 12, tzinfo=UTC)
    result = after_ollama_attempt(started, 0, None, 3, response_received_at=started)
    assert result == started + timedelta(seconds=63)


def test_retry_after_cannot_shorten_the_minimum_or_a_longer_provider_wait():
    started = datetime(2026, 11, 2, 12, tzinfo=UTC)
    assert after_ollama_attempt(
        started, 2, 10, 0, response_received_at=started
    ) == started + timedelta(seconds=60)
    assert after_ollama_attempt(
        started, 2, 120, 5, response_received_at=started
    ) == started + timedelta(seconds=125)


def test_missing_retry_after_backs_off_without_busy_retry():
    started = datetime(2026, 11, 2, 12, tzinfo=UTC)
    assert after_ollama_attempt(
        started, 8, None, 0, response_received_at=started
    ) == started + timedelta(seconds=256)


def test_invalid_timestamps_and_inputs_fail_closed():
    import pytest

    started = datetime(2026, 11, 2, 12, tzinfo=UTC)
    for args in (
        (started.replace(tzinfo=None), 0, None, 0),
        (started, -1, None, 0),
        (started, 0, None, 11),
    ):
        with pytest.raises(ValueError):
            after_ollama_attempt(*args, response_received_at=started)


def test_retry_after_is_measured_from_response_not_request_start():
    started = datetime(2026, 11, 2, 12, tzinfo=UTC)
    completed = started + timedelta(seconds=20)
    assert after_ollama_attempt(
        started, 1, 120, 0, response_received_at=completed
    ) == completed + timedelta(seconds=120)


def test_backward_clock_is_rejected_before_scheduling():
    import pytest

    started = datetime(2026, 11, 2, 12, tzinfo=UTC)
    with pytest.raises(ValueError, match="ollama_rate_time_order_invalid"):
        after_ollama_attempt(
            started, 1, 3600, 0, response_received_at=started - timedelta(hours=1)
        )


def test_long_valid_provider_wait_is_not_shortened():
    started = datetime(2026, 11, 2, 12, tzinfo=UTC)
    assert after_ollama_attempt(
        started, 1, 2678401, 0, response_received_at=started
    ) == started + timedelta(seconds=2678401)


def test_output_is_normalized_to_utc():
    from datetime import timezone

    started = datetime(2026, 11, 2, 12, tzinfo=timezone(timedelta(hours=1)))
    assert (
        after_ollama_attempt(started, 0, None, 0, response_received_at=started).tzinfo
        is UTC
    )


def test_unrepresentable_wait_is_a_distinct_blocking_error():
    import pytest

    started = datetime(2026, 11, 2, 12, tzinfo=UTC)
    with pytest.raises(ValueError, match="ollama_rate_wait_unrepresentable"):
        after_ollama_attempt(started, 1, 10**30, 0, response_received_at=started)

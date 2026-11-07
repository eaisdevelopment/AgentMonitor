"""Pure unknown-response backoff and signal semantics; no provider I/O."""

from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.modules.collection_control.domain.ollama_rate_policy import (
    after_unknown_ollama_attempt,
)
from agentmonitor.modules.collection_control.domain.ollama_verification import (
    classify_latest_ollama_cloud_source_signal_v1,
)

NOW = datetime(2026, 11, 7, tzinfo=UTC)


def test_unknown_response_gets_full_fallback_without_inventing_rate_limit() -> None:
    assert after_unknown_ollama_attempt(
        NOW - timedelta(days=2), NOW, 7
    ) == NOW + timedelta(seconds=307)


def test_known_long_wait_survives_unknown_recovery() -> None:
    deadline = NOW + timedelta(days=3)
    assert after_unknown_ollama_attempt(deadline, NOW, 10) == deadline + timedelta(
        seconds=10
    )


@pytest.mark.parametrize("jitter", [-1, 11, True])
def test_invalid_jitter_fails_closed(jitter: int) -> None:
    with pytest.raises(ValueError, match="ollama_unknown_recovery_invalid"):
        after_unknown_ollama_attempt(NOW, NOW, jitter)


def test_abandoned_failure_can_retry_without_claiming_a_response() -> None:
    assert (
        classify_latest_ollama_cloud_source_signal_v1(
            run_state="failed",
            dispatch_certainty="may_have_started",
            outcome=None,
            failure_code="outcome_unknown",
        )
        == "transient_failure"
    )
    assert (
        classify_latest_ollama_cloud_source_signal_v1(
            run_state="running",
            dispatch_certainty="may_have_started",
            outcome=None,
            failure_code="outcome_unknown",
        )
        == "outcome_unresolved"
    )
    assert (
        classify_latest_ollama_cloud_source_signal_v1(
            run_state="failed",
            dispatch_certainty="may_have_started",
            outcome=None,
            failure_code=None,
        )
        == "outcome_unresolved"
    )


def test_conservative_hold_can_record_after_expiry_but_cannot_authorize_request() -> (
    None
):
    from agentmonitor.modules.collection_control.domain.ollama_rate_policy import (
        ollama_lease_time_allows_action,
    )

    expired = NOW - timedelta(seconds=1)
    started = NOW - timedelta(minutes=1)
    assert ollama_lease_time_allows_action(
        started, expired, NOW, conservative_hold=True
    )
    assert not ollama_lease_time_allows_action(started, expired, NOW)
    assert not ollama_lease_time_allows_action(
        started, expired, started - timedelta(seconds=1), conservative_hold=True
    )


def test_late_known_rate_limit_is_recorded_without_allowing_late_quota() -> None:
    from agentmonitor.modules.collection_control.domain.ollama_rate_policy import (
        ollama_completion_time_allows_record,
    )

    started = NOW - timedelta(minutes=2)
    expired = NOW - timedelta(minutes=1)
    received = NOW - timedelta(seconds=1)
    assert ollama_completion_time_allows_record(
        started, expired, received, NOW, "rate_limited"
    )
    assert not ollama_completion_time_allows_record(
        started, expired, received, NOW, "succeeded"
    )
    assert not ollama_completion_time_allows_record(
        started, expired, received, NOW, "failed"
    )
    assert not ollama_completion_time_allows_record(
        started, expired, NOW + timedelta(seconds=1), NOW, "rate_limited"
    )
    assert not ollama_completion_time_allows_record(
        started, expired, started - timedelta(seconds=1), NOW, "rate_limited"
    )

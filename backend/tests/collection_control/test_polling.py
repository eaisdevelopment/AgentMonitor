"""Constructed inputs exercise only the pure polling decision."""

from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.modules.collection_control.domain.polling import poll_is_due


def test_first_poll_and_minimum_interval() -> None:
    now = datetime(2026, 9, 28, tzinfo=UTC)
    assert poll_is_due(now, None, None, 300)
    assert not poll_is_due(now + timedelta(seconds=299), now, "succeeded", 300)
    assert poll_is_due(now + timedelta(seconds=300), now, "succeeded", 300)
    assert poll_is_due(now + timedelta(seconds=300), now, "partial", 300)


@pytest.mark.parametrize(
    "state",
    [
        "queued",
        "running",
        "committing",
        "failed",
        "blocked",
        "cancelled",
        "unsupported",
    ],
)
def test_no_repeat_without_a_successful_source_attempt(state: str) -> None:
    then = datetime(2026, 9, 28, tzinfo=UTC)
    assert not poll_is_due(then + timedelta(days=1), then, state, 300)


def test_invalid_pair_is_rejected() -> None:
    with pytest.raises(ValueError, match="collection_poll_input_invalid"):
        poll_is_due(datetime.now(UTC), None, "succeeded", 300)

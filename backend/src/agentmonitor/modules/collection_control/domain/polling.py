"""Pure cadence decision for a source with a known minimum request interval."""

from datetime import UTC, datetime, timedelta


def poll_is_due(
    now: datetime,
    last_attempt_at: datetime | None,
    last_state: str | None,
    minimum_interval_seconds: int,
) -> bool:
    if (
        now.utcoffset() != timedelta(0)
        or type(minimum_interval_seconds) is not int
        or minimum_interval_seconds < 1
        or (last_attempt_at is None) != (last_state is None)
        or (last_attempt_at is not None and last_attempt_at.utcoffset() != timedelta(0))
    ):
        raise ValueError("collection_poll_input_invalid")
    if last_attempt_at is None:
        return True
    # The adapter gives no automatic retry grant for failed or blocked reads.
    if last_state not in {"succeeded", "partial"}:
        return False
    return now >= last_attempt_at.astimezone(UTC) + timedelta(
        seconds=minimum_interval_seconds
    )

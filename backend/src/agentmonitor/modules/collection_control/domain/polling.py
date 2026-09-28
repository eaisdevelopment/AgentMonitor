"""Pure cadence decision for a source with a known minimum request interval."""

from datetime import UTC, datetime, timedelta


def poll_is_due(
    now: datetime,
    last_attempt_at: datetime | None,
    last_state: str | None,
    minimum_interval_seconds: int,
    *,
    transient_read_failure: bool = False,
) -> bool:
    if (
        now.utcoffset() != timedelta(0)
        or type(minimum_interval_seconds) is not int
        or minimum_interval_seconds < 1
        or type(transient_read_failure) is not bool
        or (last_attempt_at is None) != (last_state is None)
        or (last_attempt_at is not None and last_attempt_at.utcoffset() != timedelta(0))
    ):
        raise ValueError("collection_poll_input_invalid")
    if last_attempt_at is None:
        return True
    # Never retry an existing failed run. An admitted transient failure may
    # permit a distinct future scheduled observation after the full cadence.
    if last_state not in {"succeeded", "partial"} and not (
        last_state == "failed" and transient_read_failure
    ):
        return False
    return now >= last_attempt_at.astimezone(UTC) + timedelta(
        seconds=minimum_interval_seconds
    )

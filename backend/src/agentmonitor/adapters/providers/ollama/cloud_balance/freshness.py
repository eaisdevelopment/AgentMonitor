"""Dashboard-owned freshness policy for fair Ollama cloud polling."""

from datetime import UTC, datetime, timedelta


def cloud_freshness_deadline_v1(
    observed_at: datetime, monitored_account_count: int | None
) -> datetime | None:
    """Allow two nominal round-robin turns, at least 15 minutes.

    This is an application display/alert policy, not an Ollama guarantee. Long
    cooldowns may make a reading stale before the next allowed poll.
    """
    if (
        observed_at.utcoffset() != UTC.utcoffset(observed_at)
        or type(monitored_account_count) is not int
        or not 1 <= monitored_account_count <= 1000
    ):
        return None
    return observed_at + timedelta(seconds=max(900, monitored_account_count * 140))

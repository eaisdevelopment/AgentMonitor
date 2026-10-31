"""Pure UTC cutoff and deletion eligibility; no I/O or fake clock."""

from datetime import datetime, timedelta

from agentmonitor.contracts.alerting_v1 import AlertViewV1


def retention_cutoff(as_of: datetime) -> datetime:
    if as_of.utcoffset() != timedelta(0):
        raise ValueError("alert_retention_utc_required")
    return as_of - timedelta(days=365)


def terminal_alert_is_expired(
    alert: AlertViewV1,
    as_of: datetime,
    *,
    has_pending_work: bool,
    has_retained_dependencies: bool,
    replay_safe: bool,
) -> bool:
    cutoff = retention_cutoff(as_of)
    if (
        alert.lifecycle == "open"
        or has_pending_work
        or has_retained_dependencies
        or not replay_safe
    ):
        return False
    terminal_at = (
        alert.recovered_at if alert.lifecycle == "recovered" else alert.closed_at
    )
    return terminal_at is not None and terminal_at < cutoff

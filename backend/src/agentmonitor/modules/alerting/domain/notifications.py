"""Pure authoritative dashboard ordering/counts from actual alert projections."""

from datetime import datetime

from agentmonitor.contracts.alerting_v1 import (
    AlertViewV1,
    DashboardNotificationCountsV1,
    DashboardNotificationViewV1,
)


def is_snoozed(alert: AlertViewV1, as_of: datetime) -> bool:
    return (
        alert.lifecycle == "open"
        and alert.snoozed_until is not None
        and alert.snoozed_until > as_of
    )


def _rank(alert: AlertViewV1, as_of: datetime) -> int:
    if alert.lifecycle == "open" and not is_snoozed(alert, as_of):
        return 0 if alert.severity == "critical" else 1
    if alert.lifecycle == "recovered" and alert.unread:
        return 2
    return 3


def ordered_notifications(
    alerts: tuple[AlertViewV1, ...], as_of: datetime
) -> tuple[DashboardNotificationViewV1, ...]:
    # Stable sorts avoid converting exact UTC datetime into a lossy floating timestamp.
    ordered = sorted(
        alerts,
        key=lambda item: (item.latest_notification_at, item.alert_id.value),
        reverse=True,
    )
    ordered.sort(key=lambda item: _rank(item, as_of))
    return tuple(
        DashboardNotificationViewV1(
            item, _rank(item, as_of), item.unread and not is_snoozed(item, as_of)
        )
        for item in ordered
    )


def notification_counts(
    alerts: tuple[AlertViewV1, ...], as_of: datetime
) -> DashboardNotificationCountsV1:
    return DashboardNotificationCountsV1(
        sum(
            item.lifecycle == "open"
            and item.severity == "critical"
            and not is_snoozed(item, as_of)
            for item in alerts
        ),
        sum(
            item.lifecycle == "open"
            and item.severity == "warning"
            and not is_snoozed(item, as_of)
            for item in alerts
        ),
        sum(item.unread and not is_snoozed(item, as_of) for item in alerts),
        sum(item.unread for item in alerts),
        sum(item.acknowledged_at is not None for item in alerts),
        sum(is_snoozed(item, as_of) for item in alerts),
        sum(item.lifecycle == "recovered" for item in alerts),
    )

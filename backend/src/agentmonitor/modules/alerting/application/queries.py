"""M07 bounded read facades. GET never changes alert state."""

from datetime import datetime, timedelta

from agentmonitor.contracts.alerting_v1 import (
    AlertHistoryEntryV1,
    AlertHistoryQueryV1,
    AlertListQueryV1,
    AlertViewV1,
    DashboardNotificationCountsV1,
    DashboardNotificationViewV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1, QueryPageV1
from agentmonitor.modules.alerting.application.ports import AlertActionRepositoryV1


class GetAlertV1:
    def __init__(self, repository: AlertActionRepositoryV1) -> None:
        self._repository = repository

    def __call__(self, alert_id: OpaqueIdV1, *, as_of: datetime) -> AlertViewV1 | None:
        if as_of.utcoffset() != timedelta(0):
            raise ValueError("alert_query_time_invalid")
        alert = self._repository.get_alert(alert_id)
        if alert is not None and as_of < alert.last_seen_at:
            raise ValueError("alert_query_time_invalid")
        return alert


class ListAlertsV1:
    def __init__(self, repository: AlertActionRepositoryV1) -> None:
        self._repository = repository

    def __call__(self, query: AlertListQueryV1) -> QueryPageV1[AlertViewV1]:
        return self._repository.list_alerts(query)


class ListAlertHistoryV1:
    def __init__(self, repository: AlertActionRepositoryV1) -> None:
        self._repository = repository

    def __call__(self, query: AlertHistoryQueryV1) -> QueryPageV1[AlertHistoryEntryV1]:
        return self._repository.list_history(query)


class ListDashboardNotificationsV1:
    def __init__(self, repository: AlertActionRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self, query: AlertListQueryV1
    ) -> QueryPageV1[DashboardNotificationViewV1]:
        return self._repository.list_notifications(query)


class GetDashboardNotificationCountsV1:
    def __init__(self, repository: AlertActionRepositoryV1) -> None:
        self._repository = repository

    def __call__(self, query: AlertListQueryV1) -> DashboardNotificationCountsV1:
        return self._repository.notification_counts(query)

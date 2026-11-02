"""Read enabled cloud lane registrations without mutating scheduler state."""

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.contracts.cloud_schedule_status_v1 import CloudScheduleStatusV1


class SqliteCloudScheduleStatusV1:
    def __init__(self, reference: DatabaseRefV1) -> None:
        self._reference = reference

    def list_registered(self) -> tuple[CloudScheduleStatusV1, ...]:
        with open_sqlite_database(self._reference, "runtime_read_only") as handle:
            with handle.connect() as connection:
                rows = connection.exec_driver_sql(
                    "SELECT s.schedule_id,s.target_key_digest,s.account_id,"
                    "s.profile_id,s.resource_id,s.provider_target_id,"
                    "s.target_generation "
                    "FROM collection_schedule s JOIN collection_cloud_schedule_lane l "
                    "ON l.schedule_id=s.schedule_id "
                    "WHERE l.source_id='ollama.cloud.balance.v1' "
                    "AND s.provider_key='ollama' "
                    "AND s.capability_id='subscription.quota' "
                    "AND s.provider_target_kind='cloud_service' AND s.state='enabled' "
                    "ORDER BY s.schedule_id LIMIT 1001"
                ).all()
        if len(rows) > 1000:
            raise ValueError("cloud_schedule_status_limit_exceeded")
        if any(any(value is None for value in row) for row in rows):
            raise ValueError("cloud_schedule_status_invalid")
        return tuple(CloudScheduleStatusV1(*row) for row in rows)

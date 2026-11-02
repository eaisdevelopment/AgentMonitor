"""Read enabled cloud lane registrations without mutating scheduler state."""

from datetime import UTC, datetime

from sqlalchemy.engine import Connection

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

    def read_snapshot(
        self, connection: Connection, target: CloudScheduleStatusV1, fingerprint: str
    ) -> tuple[bool, bool, str | None]:
        """Read lane, exact in-flight fence and latest run from one transaction."""
        if not connection.in_transaction():
            raise ValueError("cloud_schedule_snapshot_transaction_required")
        now = (
            datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
        )
        row = connection.exec_driver_sql(
            "SELECT s.schedule_id FROM collection_schedule s "
            "JOIN collection_cloud_schedule_lane l ON l.schedule_id=s.schedule_id "
            "WHERE s.schedule_id=? AND s.target_key_digest=? AND s.account_id=? "
            "AND s.profile_id=? AND s.resource_id=? AND s.provider_target_id=? "
            "AND s.target_generation=? AND s.provider_key='ollama' "
            "AND s.provider_target_kind='cloud_service' AND s.state='enabled' "
            "AND s.capability_id='subscription.quota' "
            "AND l.source_id='ollama.cloud.balance.v1'",
            (
                target.schedule_id,
                target.target_key_digest,
                target.account_id,
                target.profile_id,
                target.resource_id,
                target.access_target_id,
                target.target_generation,
            ),
        ).first()
        if row is None:
            return False, False, None
        active = (
            connection.exec_driver_sql(
                "SELECT 1 FROM collection_ollama_cloud_gate g "
                "JOIN collection_ollama_cloud_admission a "
                "ON a.admission_id=g.active_admission_id "
                "JOIN collection_cloud_attempt_journal j "
                "ON j.admission_id=a.admission_id "
                "JOIN collection_run r ON r.run_id=j.run_id "
                "JOIN collection_lease l ON l.run_id=r.run_id "
                "WHERE a.gate_id=g.gate_id AND a.schedule_id=? "
                "AND a.account_id=? AND a.state='active' "
                "AND a.fencing_token=g.fencing_token AND a.lease_expires_at>? "
                "AND j.phase='dispatched' AND r.state='running' AND r.account_id=? "
                "AND r.schedule_id=a.schedule_id "
                "AND r.provider_target_kind='cloud_service' "
                "AND r.provider_target_id=? AND r.target_generation=? "
                "AND r.source_id='ollama.cloud.balance.v1' "
                "AND r.manifest_fingerprint=? "
                "AND l.owner_instance_id=a.scheduler_instance_id "
                "AND l.fencing_token=r.fencing_token AND l.expires_at>?",
                (
                    target.schedule_id,
                    target.account_id,
                    now,
                    target.account_id,
                    target.access_target_id,
                    target.target_generation,
                    fingerprint,
                    now,
                ),
            ).first()
            is not None
        )
        latest = connection.exec_driver_sql(
            "SELECT run_id FROM collection_run WHERE provider_key='ollama' "
            "AND account_id=? AND provider_target_kind='cloud_service' "
            "AND provider_target_id=? AND target_generation=? "
            "AND capability_id='subscription.quota' "
            "AND source_id='ollama.cloud.balance.v1' "
            "AND manifest_fingerprint=? ORDER BY requested_at DESC,run_id DESC LIMIT 1",
            (
                target.account_id,
                target.access_target_id,
                target.target_generation,
                fingerprint,
            ),
        ).first()
        return True, active, str(latest[0]) if latest is not None else None

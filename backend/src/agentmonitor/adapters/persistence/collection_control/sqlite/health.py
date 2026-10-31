"""M04-owned schedule/run counts; no quota, identity, target or provider payload."""

from datetime import UTC, datetime, timedelta
from typing import ClassVar

from agentmonitor.adapters.persistence._shared.sqlite.core.bounded_read import (
    open_bounded_sqlite_read,
)
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
)
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1
from agentmonitor.contracts.operations_v1 import (
    ComponentHealthRequestV1,
    ComponentHealthResultV1,
    ComponentHealthSampleV1,
    ComponentIndicatorV1,
)


class GetCollectorComponentHealthV1:
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-006"
    OWNER: ClassVar[str] = "PLAN-M08"

    def __init__(self, reference: DatabaseRefV1) -> None:
        self._reference = reference

    async def __call__(
        self, request: ComponentHealthRequestV1
    ) -> ComponentHealthResultV1:
        try:
            with open_bounded_sqlite_read(
                self._reference,
                deadline=request.deadline,
                allowed_tables=frozenset({"collection_schedule", "collection_run"}),
            ) as connection:
                instant = request.as_of.isoformat(timespec="microseconds").replace(
                    "+00:00", "Z"
                )
                due = connection.fetch_one(
                    "SELECT count(*) FROM collection_schedule "
                    "WHERE state='enabled' AND next_due_at<=?",
                    (instant,),
                )
                blocked = connection.fetch_one(
                    "SELECT count(*) FROM collection_schedule WHERE state IN "
                    "('blocked_authentication','blocked_user_action',"
                    "'blocked_compatibility','blocked_unknown_constraints')"
                )
                running = connection.fetch_one(
                    "SELECT count(*) FROM collection_run "
                    "WHERE state IN ('running','committing')"
                )

            def count(row: tuple[object, ...] | None) -> int:
                if row is None or type(row[0]) is not int or row[0] < 0:
                    raise SqlitePolicyError("database_result_invalid")
                return row[0]

            counts = {
                "due_count": count(due),
                "running_count": count(running),
                "blocked_count": count(blocked),
            }
            now = datetime.now(UTC)
            degraded = counts["blocked_count"] > 0
            code = (
                "operations_collector_degraded"
                if degraded
                else "operations_component_healthy"
            )
            sample = ComponentHealthSampleV1(
                "collection_control",
                None,
                "degraded" if degraded else "healthy",
                now,
                now + timedelta(seconds=30),
                now if not degraded else None,
                (code,),
                tuple(
                    ComponentIndicatorV1(
                        key, counts[key], "count", FieldAvailabilityV1("available")
                    )
                    for key in request.indicator_keys
                    if key in counts
                ),
            )
            return ComponentHealthResultV1(
                "collection_control", "available", sample, now, code
            )
        except SqlitePolicyError:
            return ComponentHealthResultV1(
                "collection_control",
                "unavailable",
                None,
                datetime.now(UTC),
                "operations_collector_unavailable",
            )

"""M01-owned bounded operational metadata; credential columns are never read."""

from datetime import UTC, datetime, timedelta
from typing import ClassVar

from agentmonitor.adapters.persistence._shared.sqlite.core.bounded_read import (
    open_bounded_sqlite_read,
)
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
)
from agentmonitor.contracts.operations_v1 import (
    ComponentHealthRequestV1,
    ComponentHealthResultV1,
    ComponentHealthSampleV1,
)


class GetIamComponentHealthV1:
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
                allowed_tables=frozenset({"iam_administrator"}),
            ) as connection:
                row = connection.fetch_one("SELECT count(*) FROM iam_administrator")
            initialized = row is not None and row[0] == 1
            now = datetime.now(UTC)
            code = (
                "operations_component_healthy"
                if initialized
                else "operations_setup_required"
            )
            sample = ComponentHealthSampleV1(
                "identity_access",
                None,
                "healthy" if initialized else "unknown",
                now,
                now + timedelta(seconds=30),
                now if initialized else None,
                (code,),
                (),
            )
            return ComponentHealthResultV1(
                "identity_access", "available", sample, now, code
            )
        except SqlitePolicyError:
            return ComponentHealthResultV1(
                "identity_access",
                "unavailable",
                None,
                datetime.now(UTC),
                "operations_component_unavailable",
            )

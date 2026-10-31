"""M02-owned registry reachability metadata, without labels or identities."""

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


class GetRegistryComponentHealthV1:
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
                allowed_tables=frozenset({"reg_registry_state", "reg_account"}),
            ) as connection:
                connection.fetch_one("SELECT count(*) FROM reg_account")
                connection.fetch_one(
                    "SELECT registry_revision FROM reg_registry_state "
                    "WHERE singleton_key=1"
                )
            now = datetime.now(UTC)
            sample = ComponentHealthSampleV1(
                "registry",
                None,
                "healthy",
                now,
                now + timedelta(seconds=30),
                now,
                ("operations_component_healthy",),
                (),
            )
            return ComponentHealthResultV1(
                "registry", "available", sample, now, "operations_component_healthy"
            )
        except SqlitePolicyError:
            return ComponentHealthResultV1(
                "registry",
                "unavailable",
                None,
                datetime.now(UTC),
                "operations_component_unavailable",
            )

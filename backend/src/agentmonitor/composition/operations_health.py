"""M4 composition maps published operational receipts, without business SQL."""

from datetime import UTC, datetime, timedelta
from typing import ClassVar

from agentmonitor.contracts.common_v1 import FieldAvailabilityV1
from agentmonitor.contracts.configuration_v1 import BootstrapConfigurationV1
from agentmonitor.contracts.database_v1 import (
    DatabaseHealthRequestV1,
    GetDatabaseHealthV1,
)
from agentmonitor.contracts.foundation_v1 import GetLifecycleStateV1
from agentmonitor.contracts.operations_v1 import (
    ComponentHealthRequestV1,
    ComponentHealthResultV1,
    ComponentHealthSampleV1,
    OperationsQueryRequestV1,
    VersionValueV1,
)


class FoundationHealthLeafV1:
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-006"
    OWNER: ClassVar[str] = "PLAN-M08"

    def __init__(self, lifecycle: GetLifecycleStateV1) -> None:
        self._lifecycle = lifecycle

    async def __call__(
        self, request: ComponentHealthRequestV1
    ) -> ComponentHealthResultV1:
        state = self._lifecycle()
        now = datetime.now(UTC)
        healthy = state.phase == "running" and state.failure_code is None
        code = (
            "operations_component_healthy" if healthy else "operations_service_stopping"
        )
        sample = ComponentHealthSampleV1(
            "foundation",
            None,
            "healthy" if healthy else "unavailable",
            now,
            now + timedelta(seconds=30),
            now if healthy else None,
            (code,),
            (),
        )
        return ComponentHealthResultV1("foundation", "available", sample, now, code)


class ConfigurationHealthLeafV1:
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-006"
    OWNER: ClassVar[str] = "PLAN-M08"

    def __init__(self, configuration: BootstrapConfigurationV1) -> None:
        self._configuration = configuration

    async def __call__(
        self, request: ComponentHealthRequestV1
    ) -> ComponentHealthResultV1:
        now = datetime.now(UTC)
        healthy = self._configuration.configuration_version == "1.0.0"
        code = (
            "operations_component_healthy"
            if healthy
            else "operations_configuration_invalid"
        )
        sample = ComponentHealthSampleV1(
            "configuration",
            None,
            "healthy" if healthy else "incompatible",
            now,
            now + timedelta(seconds=30),
            now if healthy else None,
            (code,),
            (),
        )
        return ComponentHealthResultV1("configuration", "available", sample, now, code)


class DatabaseHealthLeafV1:
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-006"
    OWNER: ClassVar[str] = "PLAN-M08"

    def __init__(self, query: GetDatabaseHealthV1) -> None:
        self._query = query

    async def __call__(
        self, request: ComponentHealthRequestV1
    ) -> ComponentHealthResultV1:
        result = await self._query(
            DatabaseHealthRequestV1(
                request.as_of, request.deadline, request.correlation_id
            )
        )
        if not result.reachable:
            return ComponentHealthResultV1(
                "database",
                "unavailable",
                None,
                result.checked_at,
                "operations_database_unavailable",
            )
        healthy = (
            result.compatibility_state == "compatible"
            and result.integrity_state == "passed"
            and result.policy_state == "passed"
        )
        unknown = result.compatibility_state is None
        code = (
            "operations_component_healthy"
            if healthy
            else (
                "operations_readiness_unknown"
                if unknown
                else "operations_schema_incompatible"
            )
        )
        sample = ComponentHealthSampleV1(
            "database",
            None,
            "healthy" if healthy else "unknown" if unknown else "incompatible",
            result.checked_at,
            result.checked_at + timedelta(seconds=30),
            result.checked_at if healthy else None,
            (code,),
            (),
        )
        return ComponentHealthResultV1(
            "database", "available", sample, result.checked_at, code
        )


class DatabaseSchemaVersionQueryV1:
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-004"
    OWNER: ClassVar[str] = "PLAN-M08"

    def __init__(self, query: GetDatabaseHealthV1) -> None:
        self._query = query

    async def __call__(self, request: OperationsQueryRequestV1) -> VersionValueV1:
        result = await self._query(
            DatabaseHealthRequestV1(
                request.as_of, request.deadline, request.correlation_id
            )
        )
        return VersionValueV1(
            result.schema_revision,
            FieldAvailabilityV1(
                "available" if result.schema_revision is not None else "unknown"
            ),
            "schema_port",
        )

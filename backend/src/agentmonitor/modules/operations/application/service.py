"""M08 public read-only facade; deferred operational actions are not implemented."""

from datetime import datetime

from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.configuration_v1 import (
    BootstrapConfigurationV1,
    ConfigurationRegistryV1,
)
from agentmonitor.contracts.foundation_v1 import BuildMetadataV1, GetLifecycleStateV1
from agentmonitor.contracts.operations_v1 import (
    ComponentRegistrationV1,
    DiagnosticSummaryV1,
    GetComponentHealthV1,
    GetSchemaVersionV1,
    HealthViewV1,
    InvalidOperationsContractV1,
    LivenessViewV1,
    OperationsQueryRequestV1,
    ReadinessViewV1,
    VersionInventoryV1,
)
from agentmonitor.modules.operations.application.diagnostics import (
    OperationsDiagnosticQueriesV1,
)
from agentmonitor.modules.operations.application.health import OperationsHealthQueriesV1


class OperationsServiceV1:
    """Composition supplies real producer leaves and already-validated receipts."""

    def __init__(
        self,
        manifest: tuple[ComponentRegistrationV1, ...],
        leaves: tuple[tuple[str, GetComponentHealthV1], ...],
        lifecycle: GetLifecycleStateV1,
        build: BuildMetadataV1,
        configuration: BootstrapConfigurationV1,
        configuration_registry: ConfigurationRegistryV1,
        schema_version: GetSchemaVersionV1,
    ) -> None:
        self._health = OperationsHealthQueriesV1(
            manifest, leaves, lifecycle, schema_version
        )
        self._diagnostics = OperationsDiagnosticQueriesV1(
            self._health, build, configuration, configuration_registry
        )

    def get_liveness(
        self, as_of: datetime, correlation_id: OpaqueIdV1
    ) -> LivenessViewV1:
        return self._health.get_liveness(as_of, correlation_id)

    async def get_health(self, request: OperationsQueryRequestV1) -> HealthViewV1:
        if request.disclosure_level != "administrator":
            raise InvalidOperationsContractV1("operations_disclosure_denied")
        health, _ = await self._health.get_health_and_readiness(request)
        return health

    async def get_readiness(self, request: OperationsQueryRequestV1) -> ReadinessViewV1:
        _, readiness = await self._health.get_health_and_readiness(request)
        return readiness

    async def get_versions(
        self, request: OperationsQueryRequestV1
    ) -> VersionInventoryV1:
        return await self._diagnostics.get_versions(request)

    async def get_diagnostic_summary(
        self, request: OperationsQueryRequestV1
    ) -> DiagnosticSummaryV1:
        return await self._diagnostics.get_diagnostic_summary(request)

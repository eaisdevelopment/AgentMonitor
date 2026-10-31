"""Typed diagnostics orchestration; no file, provider, DB or configuration reads."""

from agentmonitor.contracts.common_v1 import QueryAvailabilityV1
from agentmonitor.contracts.configuration_v1 import (
    BootstrapConfigurationV1,
    ConfigurationRegistryV1,
)
from agentmonitor.contracts.foundation_v1 import BuildMetadataV1
from agentmonitor.contracts.operations_v1 import (
    DiagnosticSummaryV1,
    InvalidOperationsContractV1,
    OperationsQueryRequestV1,
    VersionInventoryV1,
)
from agentmonitor.modules.operations.application.health import OperationsHealthQueriesV1
from agentmonitor.modules.operations.domain.diagnostics import (
    diagnostic_valid_until_v1,
    project_configuration_presence_v1,
    project_version_inventory_v1,
)


class OperationsDiagnosticQueriesV1:
    def __init__(
        self,
        health: OperationsHealthQueriesV1,
        build: BuildMetadataV1,
        configuration: BootstrapConfigurationV1,
        configuration_registry: ConfigurationRegistryV1,
    ) -> None:
        self._health = health
        self._build = build
        self._presence = project_configuration_presence_v1(
            configuration, configuration_registry
        )

    async def get_versions(
        self, request: OperationsQueryRequestV1
    ) -> VersionInventoryV1:
        if request.disclosure_level != "administrator":
            raise InvalidOperationsContractV1("operations_disclosure_denied")
        schema = await self._health.get_schema_version(request)
        return project_version_inventory_v1(
            self._build, schema, (), as_of=request.as_of
        )

    async def get_diagnostic_summary(
        self, request: OperationsQueryRequestV1
    ) -> DiagnosticSummaryV1:
        if request.disclosure_level != "administrator":
            raise InvalidOperationsContractV1("operations_disclosure_denied")
        health, readiness = await self._health.get_health_and_readiness(request)
        schema = await self._health.get_schema_version(request)
        versions = project_version_inventory_v1(
            self._build, schema, health.components, as_of=health.generated_at
        )
        complete = (
            health.availability.state == "available"
            and versions.availability.state == "available"
        )
        code = (
            "operations_diagnostics_complete"
            if complete
            else "operations_diagnostics_partial"
        )
        return DiagnosticSummaryV1(
            versions,
            health,
            readiness,
            self._presence,
            health.generated_at,
            diagnostic_valid_until_v1(health.valid_until, readiness.valid_until),
            QueryAvailabilityV1(
                "available" if complete else "partial", code, health.generated_at
            ),
            (code,),
            request.correlation_id,
        )

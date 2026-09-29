"""Closed administrator health and diagnostic wire records."""

from datetime import datetime
from typing import Literal

from agentmonitor.api.v1.schemas.registry import AvailabilityV1
from pydantic import BaseModel, ConfigDict, Field


class _ClosedV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class OperationsIndicatorWireV1(_ClosedV1):
    key: str
    value: int | None = Field(ge=0)
    unit: Literal["count", "milliseconds"]
    availability: str


class OperationsSampleWireV1(_ClosedV1):
    component_key: str
    component_version: str | None
    state: Literal[
        "healthy", "degraded", "unavailable", "incompatible", "maintenance", "unknown"
    ]
    checked_at: datetime
    valid_until: datetime
    last_success_at: datetime | None
    reason_codes: tuple[str, ...]
    indicators: tuple[OperationsIndicatorWireV1, ...]


class OperationsComponentWireV1(_ClosedV1):
    component_key: str
    outcome: Literal["available", "unavailable", "incompatible"]
    sample: OperationsSampleWireV1 | None
    checked_at: datetime
    reason_code: str
    contract_major: Literal[1]


class OperationsHealthWireV1(_ClosedV1):
    state: Literal[
        "healthy", "degraded", "unavailable", "incompatible", "maintenance", "unknown"
    ]
    generated_at: datetime
    valid_until: datetime
    components: tuple[OperationsComponentWireV1, ...]
    availability: AvailabilityV1
    reason_codes: tuple[str, ...]
    correlation_id: str


class OperationsReadinessWireV1(_ClosedV1):
    state: Literal["ready", "not_ready", "setup_required", "maintenance", "unknown"]
    generated_at: datetime
    valid_until: datetime
    blocker_component_keys: tuple[str, ...]
    reason_codes: tuple[str, ...]
    correlation_id: str


class OperationsLivenessWireV1(_ClosedV1):
    state: Literal["healthy", "unavailable"]
    checked_at: datetime
    correlation_id: str


class OperationsVersionValueWireV1(_ClosedV1):
    value: str | None
    availability: str
    source: Literal[
        "application_manifest",
        "build_manifest",
        "schema_port",
        "adapter_manifest",
        "generated_artifact",
    ]


class OperationsComponentVersionWireV1(_ClosedV1):
    component_key: str
    version: OperationsVersionValueWireV1


class OperationsVersionsWireV1(_ClosedV1):
    application_version: OperationsVersionValueWireV1
    schema_version: OperationsVersionValueWireV1
    api_version: OperationsVersionValueWireV1
    openapi_version: OperationsVersionValueWireV1
    client_version: OperationsVersionValueWireV1
    frontend_version: OperationsVersionValueWireV1
    components: tuple[OperationsComponentVersionWireV1, ...]
    availability: AvailabilityV1


class OperationsConfigurationPresenceWireV1(_ClosedV1):
    key: str
    owner: str
    presence: Literal["configured", "missing", "invalid", "unknown"]


class OperationsDiagnosticsWireV1(_ClosedV1):
    versions: OperationsVersionsWireV1
    health: OperationsHealthWireV1
    readiness: OperationsReadinessWireV1
    configuration_presence: tuple[OperationsConfigurationPresenceWireV1, ...]
    generated_at: datetime
    valid_until: datetime
    availability: AvailabilityV1
    reason_codes: tuple[str, ...]
    correlation_id: str

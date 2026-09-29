"""M08-owned V1 health/diagnostic contracts and deferred operations declarations.

No filesystem, database, provider, framework, process or network implementation.
Deferred backup/export/participant protocols are declarations, never placeholders.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import ClassVar, Literal, Protocol

from agentmonitor.contracts.alerting_v1 import DashboardNotificationCountsV1
from agentmonitor.contracts.capacity_v1 import CapacityAggregateViewV1
from agentmonitor.contracts.collection_control_v1 import CollectorHealthV1
from agentmonitor.contracts.common_v1 import (
    FieldAvailabilityV1,
    OpaqueIdV1,
    QueryAvailabilityV1,
    TechnicalValueV1,
)
from agentmonitor.contracts.registry_v1 import (
    RegistryScopeKindV1,
    RegistryScopeSnapshotV1,
)
from agentmonitor.contracts.runtime_observation_v1 import RuntimeOverviewViewV1

HealthStateV1 = Literal[
    "healthy", "degraded", "unavailable", "incompatible", "maintenance", "unknown"
]
ReadinessStateV1 = Literal[
    "ready", "not_ready", "setup_required", "maintenance", "unknown"
]
ComponentCriticalityV1 = Literal["required_for_normal_readiness", "optional_degraded"]
ComponentResultStateV1 = Literal["available", "unavailable", "incompatible"]
DisclosureLevelV1 = Literal["administrator", "service"]

COMPONENT_KEYS_V1 = frozenset(
    {
        "foundation",
        "configuration",
        "database",
        "identity_access",
        "registry",
        "provider_system",
        "collection_control",
        "capacity",
        "runtime_observation",
        "alerting",
        "provider.claude",
    }
)
INDICATOR_UNITS_V1 = {
    "due_count": "count",
    "running_count": "count",
    "blocked_count": "count",
    "health_duration_ms": "milliseconds",
}
REASON_CODES_V1 = frozenset(
    {
        "operations_ready",
        "operations_not_ready",
        "operations_liveness_healthy",
        "operations_liveness_unavailable",
        "operations_health_complete",
        "operations_health_partial",
        "operations_health_unavailable",
        "operations_component_healthy",
        "operations_component_degraded",
        "operations_component_unavailable",
        "operations_component_incompatible",
        "operations_component_timeout",
        "operations_component_invalid",
        "operations_component_stale",
        "operations_component_future",
        "operations_required_component_missing",
        "operations_setup_required",
        "operations_maintenance_active",
        "operations_readiness_unknown",
        "operations_configuration_invalid",
        "operations_secret_missing",
        "operations_version_unknown",
        "operations_version_mismatch",
        "operations_schema_incompatible",
        "operations_service_stopping",
        "operations_database_unavailable",
        "operations_database_locked",
        "operations_collector_unavailable",
        "operations_collector_degraded",
        "operations_diagnostics_complete",
        "operations_diagnostics_partial",
        "operations_backup_unavailable",
        "operations_artifact_unavailable",
        "operations_artifact_rejected",
        "operations_artifact_expired",
        "operations_retention_participant_blocked",
        "operations_internal_error",
    }
)
MAX_COMPONENTS_V1 = 32
MAX_INDICATORS_V1 = 16
MAX_REASONS_V1 = 8
MAX_HEALTH_BUDGET_MS_V1 = 2000
_VERSION = re.compile(
    r"(?:[0-9]{1,8}\.[0-9]{1,8}\.[0-9]{1,8}(?:-[a-z0-9.-]{1,32})?"
    r"|v1_[0-9]{4}|[a-f0-9]{64})"
)
_DIGEST = re.compile(r"[a-f0-9]{64}")


class InvalidOperationsContractV1(ValueError):
    """Arguments contain a code-owned classification only."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.__suppress_context__ = True


def _component(key: str) -> None:
    if key not in COMPONENT_KEYS_V1:
        raise InvalidOperationsContractV1("operations_component_invalid")


def _reason(code: str) -> None:
    if code not in REASON_CODES_V1:
        raise InvalidOperationsContractV1("operations_reason_invalid")


def _reasons(codes: tuple[str, ...]) -> None:
    if type(codes) is not tuple or len(codes) > MAX_REASONS_V1:
        raise InvalidOperationsContractV1("operations_reason_invalid")
    for code in codes:
        _reason(code)


def _deadline(as_of: datetime, deadline: datetime) -> None:
    duration = deadline - as_of
    if not timedelta(0) < duration <= timedelta(milliseconds=MAX_HEALTH_BUDGET_MS_V1):
        raise InvalidOperationsContractV1("operations_deadline_invalid")


def _version(value: str | None) -> None:
    if value is not None and (type(value) is not str or not _VERSION.fullmatch(value)):
        raise InvalidOperationsContractV1("operations_version_invalid")


def _count(value: int | None, code: str) -> None:
    if value is not None and (type(value) is not int or value < 0):
        raise InvalidOperationsContractV1(code)


@dataclass(frozen=True, slots=True)
class ComponentRegistrationV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-006"
    OWNER: ClassVar[str] = "PLAN-M08"
    component_key: str
    criticality: ComponentCriticalityV1
    indicator_keys: tuple[str, ...]
    contract_major: int = 1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _component(self.component_key)
        if (
            self.contract_major != 1
            or type(self.contract_major) is not int
            or len(self.indicator_keys) > MAX_INDICATORS_V1
            or len(set(self.indicator_keys)) != len(self.indicator_keys)
            or any(key not in INDICATOR_UNITS_V1 for key in self.indicator_keys)
        ):
            raise InvalidOperationsContractV1("operations_manifest_invalid")


@dataclass(frozen=True, slots=True)
class ComponentHealthRequestV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-006"
    OWNER: ClassVar[str] = "PLAN-M08"
    component_key: str
    correlation_id: OpaqueIdV1
    as_of: datetime
    deadline: datetime
    disclosure_level: DisclosureLevelV1
    indicator_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _component(self.component_key)
        _deadline(self.as_of, self.deadline)
        if len(self.indicator_keys) > MAX_INDICATORS_V1 or any(
            key not in INDICATOR_UNITS_V1 for key in self.indicator_keys
        ):
            raise InvalidOperationsContractV1("operations_indicator_invalid")


@dataclass(frozen=True, slots=True)
class ComponentIndicatorV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-006"
    OWNER: ClassVar[str] = "PLAN-M08"
    key: str
    value: int | None
    unit: Literal["count", "milliseconds"]
    availability: FieldAvailabilityV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _count(self.value, "operations_indicator_invalid")
        if (
            self.key not in INDICATOR_UNITS_V1
            or INDICATOR_UNITS_V1[self.key] != self.unit
            or (self.value is not None) != (self.availability.state == "available")
        ):
            raise InvalidOperationsContractV1("operations_indicator_invalid")


@dataclass(frozen=True, slots=True)
class ComponentHealthSampleV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-006"
    OWNER: ClassVar[str] = "PLAN-M08"
    component_key: str
    component_version: str | None
    state: HealthStateV1
    checked_at: datetime
    valid_until: datetime
    last_success_at: datetime | None
    reason_codes: tuple[str, ...]
    indicators: tuple[ComponentIndicatorV1, ...]

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _component(self.component_key)
        _version(self.component_version)
        _reasons(self.reason_codes)
        if (
            self.valid_until <= self.checked_at
            or self.last_success_at is not None
            and self.last_success_at > self.checked_at
            or len(self.indicators) > MAX_INDICATORS_V1
            or len({item.key for item in self.indicators}) != len(self.indicators)
        ):
            raise InvalidOperationsContractV1("operations_sample_invalid")


@dataclass(frozen=True, slots=True)
class ComponentHealthResultV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-006"
    OWNER: ClassVar[str] = "PLAN-M08"
    component_key: str
    outcome: ComponentResultStateV1
    sample: ComponentHealthSampleV1 | None
    checked_at: datetime
    reason_code: str
    contract_major: int = 1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _component(self.component_key)
        _reason(self.reason_code)
        if (
            (self.outcome == "available") != (self.sample is not None)
            or self.sample is not None
            and self.sample.component_key != self.component_key
            or type(self.contract_major) is not int
            or self.contract_major != 1
        ):
            raise InvalidOperationsContractV1("operations_result_invalid")


class GetComponentHealthV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-006"
    OWNER: ClassVar[str] = "PLAN-M08"

    async def __call__(
        self, request: ComponentHealthRequestV1
    ) -> ComponentHealthResultV1: ...


@dataclass(frozen=True, slots=True)
class OperationsQueryRequestV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-001"
    OWNER: ClassVar[str] = "PLAN-M08"
    as_of: datetime
    deadline: datetime
    correlation_id: OpaqueIdV1
    disclosure_level: DisclosureLevelV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _deadline(self.as_of, self.deadline)


@dataclass(frozen=True, slots=True)
class HealthViewV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-001"
    OWNER: ClassVar[str] = "PLAN-M08"
    state: HealthStateV1
    generated_at: datetime
    valid_until: datetime
    components: tuple[ComponentHealthResultV1, ...]
    availability: QueryAvailabilityV1
    reason_codes: tuple[str, ...]
    correlation_id: OpaqueIdV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _reasons(self.reason_codes)
        if len(self.components) > MAX_COMPONENTS_V1 or len(
            {item.component_key for item in self.components}
        ) != len(self.components):
            raise InvalidOperationsContractV1("operations_result_invalid")


@dataclass(frozen=True, slots=True)
class ReadinessViewV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-002"
    OWNER: ClassVar[str] = "PLAN-M08"
    state: ReadinessStateV1
    generated_at: datetime
    valid_until: datetime
    blocker_component_keys: tuple[str, ...]
    reason_codes: tuple[str, ...]
    correlation_id: OpaqueIdV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _reasons(self.reason_codes)
        for key in self.blocker_component_keys:
            _component(key)
        if self.state == "ready" and self.blocker_component_keys:
            raise InvalidOperationsContractV1("operations_readiness_invalid")


@dataclass(frozen=True, slots=True)
class LivenessViewV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-002"
    OWNER: ClassVar[str] = "PLAN-M08"
    state: Literal["healthy", "unavailable"]
    checked_at: datetime
    correlation_id: OpaqueIdV1


@dataclass(frozen=True, slots=True)
class VersionValueV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-004"
    OWNER: ClassVar[str] = "PLAN-M08"
    value: str | None
    availability: FieldAvailabilityV1
    source: Literal[
        "application_manifest",
        "build_manifest",
        "schema_port",
        "adapter_manifest",
        "generated_artifact",
    ]

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _version(self.value)
        if (self.value is not None) != (self.availability.state == "available"):
            raise InvalidOperationsContractV1("operations_version_invalid")


@dataclass(frozen=True, slots=True)
class ComponentVersionV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-004"
    OWNER: ClassVar[str] = "PLAN-M08"
    component_key: str
    version: VersionValueV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _component(self.component_key)


@dataclass(frozen=True, slots=True)
class VersionInventoryV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-004"
    OWNER: ClassVar[str] = "PLAN-M08"
    application_version: VersionValueV1
    schema_version: VersionValueV1
    api_version: VersionValueV1
    openapi_version: VersionValueV1
    client_version: VersionValueV1
    frontend_version: VersionValueV1
    components: tuple[ComponentVersionV1, ...]
    availability: QueryAvailabilityV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if len(self.components) > MAX_COMPONENTS_V1 or len(
            {item.component_key for item in self.components}
        ) != len(self.components):
            raise InvalidOperationsContractV1("operations_version_invalid")


class GetSchemaVersionV1(Protocol):
    """Root maps actual PLAN-DB schema query into this safe version receipt."""

    CONTRACT_ID: ClassVar[str] = "CTR-OPS-004"
    OWNER: ClassVar[str] = "PLAN-M08"

    async def __call__(self, request: OperationsQueryRequestV1) -> VersionValueV1: ...


@dataclass(frozen=True, slots=True)
class ConfigurationPresenceV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-004"
    OWNER: ClassVar[str] = "PLAN-M08"
    key: str
    owner: str
    presence: Literal["configured", "missing", "invalid", "unknown"]

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not re.fullmatch(
            r"AGENTMONITOR_[A-Z][A-Z0-9_]{0,95}", self.key
        ) or not re.fullmatch(r"[A-Z][A-Z0-9-]{0,47}", self.owner):
            raise InvalidOperationsContractV1("operations_configuration_invalid")


@dataclass(frozen=True, slots=True)
class DiagnosticSummaryV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-004"
    OWNER: ClassVar[str] = "PLAN-M08"
    versions: VersionInventoryV1
    health: HealthViewV1
    readiness: ReadinessViewV1
    configuration_presence: tuple[ConfigurationPresenceV1, ...]
    generated_at: datetime
    valid_until: datetime
    availability: QueryAvailabilityV1
    reason_codes: tuple[str, ...]
    correlation_id: OpaqueIdV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _reasons(self.reason_codes)
        if len(self.configuration_presence) > 128 or len(
            {item.key for item in self.configuration_presence}
        ) != len(self.configuration_presence):
            raise InvalidOperationsContractV1("operations_configuration_invalid")


@dataclass(frozen=True, slots=True)
class BackupViewV1(TechnicalValueV1):
    """Deferred CTR-OPS-003 publication; no backup workflow is exposed."""

    CONTRACT_ID: ClassVar[str] = "CTR-OPS-003"
    OWNER: ClassVar[str] = "PLAN-M08"
    backup_id: OpaqueIdV1
    job_id: OpaqueIdV1
    trigger: Literal["automatic", "manual", "migration_preflight"]
    state: Literal[
        "requested", "creating", "verifying", "valid", "invalid", "missing", "retired"
    ]
    requested_at: datetime
    completed_at: datetime | None
    schema_version: str | None
    application_version: str | None
    size_bytes: int | None
    checksum: str | None
    integrity_state: Literal[
        "not_checked", "checking", "valid", "invalid", "unavailable"
    ]
    reason_code: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _reason(self.reason_code)
        _count(self.size_bytes, "operations_backup_invalid")
        _version(self.schema_version)
        _version(self.application_version)
        if self.checksum is not None and not _DIGEST.fullmatch(self.checksum):
            raise InvalidOperationsContractV1("operations_backup_invalid")
        if self.state == "valid" and (
            self.completed_at is None
            or self.size_bytes is None
            or self.checksum is None
            or self.integrity_state != "valid"
            or self.schema_version is None
            or self.application_version is None
        ):
            raise InvalidOperationsContractV1("operations_backup_invalid")


@dataclass(frozen=True, slots=True)
class RestoreJobViewV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-003"
    OWNER: ClassVar[str] = "PLAN-M08"
    restore_id: OpaqueIdV1
    backup_id: OpaqueIdV1
    job_id: OpaqueIdV1
    phase: Literal[
        "requested",
        "preflight",
        "journal",
        "stage",
        "validate",
        "invalidate_security",
        "preserve_activate",
        "restricted_start",
        "complete",
        "failed",
        "blocked",
        "rollback_required",
        "rolled_back",
    ]
    requested_at: datetime
    completed_at: datetime | None
    reason_code: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _reason(self.reason_code)


class GetBackupV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-003"
    OWNER: ClassVar[str] = "PLAN-M08"

    def __call__(self, backup_id: OpaqueIdV1) -> BackupViewV1 | None: ...


class GetRestoreJobV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-003"
    OWNER: ClassVar[str] = "PLAN-M08"

    def __call__(self, restore_id: OpaqueIdV1) -> RestoreJobViewV1 | None: ...


@dataclass(frozen=True, slots=True)
class ExportJobViewV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-005"
    OWNER: ClassVar[str] = "PLAN-M08"
    job_id: OpaqueIdV1
    artifact_id: OpaqueIdV1 | None
    purpose: Literal["owner_requested", "pre_retention_checkpoint"]
    format: Literal["agentmonitor-ndjson-v1"]
    schema_version: int
    state: Literal[
        "queued",
        "collecting",
        "validating",
        "scanning",
        "finalizing",
        "available",
        "rejected",
        "expired",
        "failed",
        "blocked",
    ]
    requested_at: datetime
    completed_at: datetime | None
    expires_at: datetime | None
    record_count: int | None
    size_bytes: int | None
    checksum: str | None
    safety_state: Literal[
        "not_scanned", "scanning", "safe", "rejected", "scanner_unavailable"
    ]
    download_available: bool
    reason_code: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _reason(self.reason_code)
        _count(self.record_count, "operations_artifact_invalid")
        _count(self.size_bytes, "operations_artifact_invalid")
        if (
            type(self.schema_version) is not int
            or self.schema_version != 1
            or self.checksum is not None
            and not _DIGEST.fullmatch(self.checksum)
            or type(self.download_available) is not bool
            or self.download_available
            and self.state != "available"
            or self.state == "available"
            and (
                self.artifact_id is None
                or self.completed_at is None
                or self.expires_at is None
                or self.record_count is None
                or self.size_bytes is None
                or self.checksum is None
                or self.safety_state != "safe"
                or self.expires_at <= self.completed_at
            )
        ):
            raise InvalidOperationsContractV1("operations_artifact_invalid")


class GetExportJobV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-005"
    OWNER: ClassVar[str] = "PLAN-M08"

    def __call__(self, job_id: OpaqueIdV1) -> ExportJobViewV1 | None: ...


@dataclass(frozen=True, slots=True)
class OperationsParticipantRequestV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-007"
    OWNER: ClassVar[str] = "PLAN-M08"
    operation_id: OpaqueIdV1
    correlation_id: OpaqueIdV1
    deadline: datetime
    contract_major: int
    cutoff: datetime | None
    limit: int
    cursor: str | None
    preview_digest: str | None
    checkpoint_id: OpaqueIdV1 | None
    prepared_database_ref: OpaqueIdV1 | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.contract_major) is not int
            or self.contract_major != 1
            or type(self.limit) is not int
            or not 1 <= self.limit <= 200
            or self.preview_digest is not None
            and not _DIGEST.fullmatch(self.preview_digest)
            or self.cursor is not None
            and not re.fullmatch(r"[a-zA-Z0-9_-]{1,256}", self.cursor)
        ):
            raise InvalidOperationsContractV1("operations_participant_invalid")


@dataclass(frozen=True, slots=True)
class OperationsParticipantReceiptV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-007"
    OWNER: ClassVar[str] = "PLAN-M08"
    participant_key: str
    operation_id: OpaqueIdV1
    outcome: Literal["complete", "partial", "blocked", "unavailable", "incompatible"]
    generation: int | None
    digest: str | None
    count: int | None
    next_cursor: str | None
    checked_at: datetime
    reason_code: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _component(self.participant_key)
        _reason(self.reason_code)
        _count(self.generation, "operations_participant_invalid")
        _count(self.count, "operations_participant_invalid")
        if (
            self.digest is not None
            and not _DIGEST.fullmatch(self.digest)
            or self.next_cursor is not None
            and not re.fullmatch(r"[a-zA-Z0-9_-]{1,256}", self.next_cursor)
        ):
            raise InvalidOperationsContractV1("operations_participant_invalid")


class RetentionExportAndConsistencyParticipantV1[TRecordV1](Protocol):
    """Deferred source-module implementation; record type belongs to its producer."""

    CONTRACT_ID: ClassVar[str] = "CTR-OPS-007"
    OWNER: ClassVar[str] = "PLAN-M08"

    def preview_expired(
        self, request: OperationsParticipantRequestV1
    ) -> OperationsParticipantReceiptV1: ...
    def query_export_records(
        self, request: OperationsParticipantRequestV1
    ) -> tuple[TRecordV1, ...]: ...
    def purge_expired(
        self, request: OperationsParticipantRequestV1
    ) -> OperationsParticipantReceiptV1: ...
    def validate_staged_consistency(
        self, request: OperationsParticipantRequestV1
    ) -> OperationsParticipantReceiptV1: ...
    def validate_activated_consistency(
        self, request: OperationsParticipantRequestV1
    ) -> OperationsParticipantReceiptV1: ...


@dataclass(frozen=True, slots=True)
class DashboardOverviewRequestV1(TechnicalValueV1):
    """Bounded dashboard request over a revisioned registry scope."""

    CONTRACT_ID: ClassVar[str] = "CTR-APP-001"
    OWNER: ClassVar[str] = "PLAN-M08"
    scope_kind: RegistryScopeKindV1
    scope_id: OpaqueIdV1 | None
    as_of: datetime
    deadline: datetime
    correlation_id: OpaqueIdV1
    limit: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _deadline(self.as_of, self.deadline)
        if (
            (self.scope_kind == "global") != (self.scope_id is None)
            or type(self.limit) is not int
            or not 1 <= self.limit <= 200
        ):
            raise InvalidOperationsContractV1("operations_overview_invalid")


@dataclass(frozen=True, slots=True)
class DashboardOverviewV1(TechnicalValueV1):
    """Typed producer sections; an unavailable section never becomes zero."""

    CONTRACT_ID: ClassVar[str] = "CTR-APP-001"
    OWNER: ClassVar[str] = "PLAN-M08"
    scope_kind: RegistryScopeKindV1
    scope_id: OpaqueIdV1 | None
    generated_at: datetime
    registry: RegistryScopeSnapshotV1 | None
    capacity: CapacityAggregateViewV1 | None
    runtime: RuntimeOverviewViewV1 | None
    alerts: DashboardNotificationCountsV1 | None
    collection: CollectorHealthV1 | None
    operations: HealthViewV1 | None
    registry_availability: QueryAvailabilityV1
    capacity_availability: QueryAvailabilityV1
    runtime_availability: QueryAvailabilityV1
    alerts_availability: QueryAvailabilityV1
    collection_availability: QueryAvailabilityV1
    operations_availability: QueryAvailabilityV1
    availability: QueryAvailabilityV1
    correlation_id: OpaqueIdV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (self.scope_kind == "global") != (self.scope_id is None):
            raise InvalidOperationsContractV1("operations_overview_invalid")
        for section, availability in (
            (self.registry, self.registry_availability),
            (self.capacity, self.capacity_availability),
            (self.runtime, self.runtime_availability),
            (self.alerts, self.alerts_availability),
            (self.collection, self.collection_availability),
            (self.operations, self.operations_availability),
        ):
            if availability.state == "available" and section is None:
                raise InvalidOperationsContractV1("operations_overview_invalid")
        if self.registry is not None and (
            self.registry.scope_kind != self.scope_kind
            or self.registry.scope_id != self.scope_id
        ):
            raise InvalidOperationsContractV1("operations_overview_invalid")
        if self.capacity is not None and (
            self.capacity.scope_kind != self.scope_kind
            or self.capacity.scope_id != self.scope_id
            or self.registry is None
            or self.capacity.registry_revision != self.registry.registry_revision
        ):
            raise InvalidOperationsContractV1("operations_overview_invalid")


class GetDashboardOverviewV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-APP-001"
    OWNER: ClassVar[str] = "PLAN-M08"

    async def __call__(
        self, request: DashboardOverviewRequestV1
    ) -> DashboardOverviewV1: ...

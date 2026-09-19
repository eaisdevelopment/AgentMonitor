"""Foundation V1 metadata seams; no application, logging or build implementation."""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Literal

from agentmonitor.contracts.common_v1 import OpaqueIdV1, TechnicalValueV1
from agentmonitor.contracts.configuration_v1 import BootstrapConfigurationV1
from agentmonitor.contracts.database_v1 import SchemaCompatibilityV1


@dataclass(frozen=True, slots=True)
class RepositoryLayoutAndOwnershipManifestV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-FND-001"
    manifest_version: str
    exclusive_paths: tuple[tuple[str, str], ...]
    shared_writers: tuple[tuple[str, str], ...]
    contract_producers: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class BuildMetadataV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-FND-007"
    application_version: str
    source_revision: str | None
    built_at: datetime | None
    timestamp_policy: str
    schema_range: SchemaCompatibilityV1
    frontend_hash: str | None
    openapi_hash: str | None
    client_hash: str | None
    component_versions: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class ApplicationFactoryV1(TechnicalValueV1):
    """Factory input declaration; later composition resolves approved factories.

    Settings are validated by their owners. IDs identify approved component and
    hook registrations; they are not arbitrary dynamic import strings.
    """

    CONTRACT_ID: ClassVar[str] = "CTR-FND-002"
    configuration: BootstrapConfigurationV1
    build: BuildMetadataV1
    component_factory_ids: tuple[str, ...]
    startup_hook_ids: tuple[str, ...]
    shutdown_hook_ids: tuple[str, ...]
    shutdown_timeout_ms: int


@dataclass(frozen=True, slots=True)
class CorrelationContextAndSafeLogEventV1(TechnicalValueV1):
    """Closed local record; no free-form message, exception or payload dictionary."""

    CONTRACT_ID: ClassVar[str] = "CTR-FND-004"
    occurred_at: datetime
    severity: Literal["debug", "info", "warning", "error", "critical"]
    component: str
    event_name: str
    component_version: str
    correlation_id: OpaqueIdV1
    causation_id: OpaqueIdV1 | None
    outcome_code: str
    subject_ids: tuple[OpaqueIdV1, ...]


@dataclass(frozen=True, slots=True)
class OpenApiArtifactAndGeneratedClientPipelineV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-FND-005"
    source_hash: str
    openapi_hash: str
    client_hash: str
    generator_name: str
    generator_version: str
    api_major: int
    compatibility: Literal["compatible", "breaking", "not_checked"]


@dataclass(frozen=True, slots=True)
class MigrationMetadataV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-FND-006"
    revision: str
    parent_revision: str | None
    owner: str
    plan_id: str
    requirement_ids: tuple[str, ...]
    schema_range: SchemaCompatibilityV1
    tables: tuple[str, ...]
    portability_notes: tuple[str, ...]
    lock_policy: str
    downtime_policy: str
    expected_data_volume: str
    backup_prerequisite: str
    validation_ids: tuple[str, ...]
    recovery_policy: str
    reviewer: str


@dataclass(frozen=True, slots=True)
class TestEvidenceSummaryV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-FND-008"
    test_id: str
    requirement_ids: tuple[str, ...]
    acceptance_ids: tuple[str, ...]
    boundary_class: str
    command_registry_id: str
    environment_versions: tuple[tuple[str, str], ...]
    red_reference: str | None
    green_reference: str | None
    refactor_reference: str | None
    status: Literal["Passed", "Failed", "Blocked", "Not Run"]
    sanitization_review: str
    recorded_at: datetime
    reviewer: str
    live_owner_countersignature: str | None

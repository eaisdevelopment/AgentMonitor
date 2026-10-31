"""PLAN-DB-owned technical declarations; no ORM, SQL, files or transaction code."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import ClassVar, Literal, Protocol, get_args

from agentmonitor.contracts.common_v1 import OpaqueIdV1, TechnicalValueV1

DatabaseSchemaStateV1 = Literal[
    "missing",
    "empty",
    "upgrade_required",
    "compatible",
    "newer_than_binary",
    "locked",
    "unreadable",
    "corrupt",
    "unknown_revision",
    "multiple_heads",
    "checksum_mismatch",
    "policy_incompatible",
    "migration_failed",
]
DatabaseHealthReasonV1 = Literal[
    "database_health_complete",
    "database_health_unverified",
    "database_missing",
    "database_empty",
    "database_upgrade_required",
    "database_newer_than_binary",
    "database_unknown_revision",
    "database_multiple_heads",
    "database_checksum_mismatch",
    "database_migration_failed",
    "database_schema_changed",
    "database_locked",
    "database_timeout",
    "database_unreadable",
    "database_policy_incompatible",
    "database_identity_changed",
    "database_corrupt",
]


@dataclass(frozen=True, slots=True)
class DatabaseHealthRequestV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-DB-001"
    OWNER: ClassVar[str] = "PLAN-DB"
    as_of: datetime
    deadline: datetime
    correlation_id: OpaqueIdV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not timedelta(0) < self.deadline - self.as_of <= timedelta(seconds=2):
            raise ValueError("database_health_budget_invalid")


@dataclass(frozen=True, slots=True)
class DatabaseHealthV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-DB-001"
    OWNER: ClassVar[str] = "PLAN-DB"
    reachable: bool
    schema_revision: str | None
    compatibility_state: DatabaseSchemaStateV1 | None
    integrity_state: Literal["passed", "failed", "not_checked"]
    integrity_checked_at: datetime | None
    policy_state: Literal["passed", "failed", "not_checked"]
    checked_at: datetime
    reason_codes: tuple[DatabaseHealthReasonV1, ...]

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if type(self.reachable) is not bool or (
            self.compatibility_state is not None
            and self.compatibility_state not in get_args(DatabaseSchemaStateV1)
        ):
            raise ValueError("database_health_state_invalid")
        if (self.integrity_state == "not_checked") != (
            self.integrity_checked_at is None
        ):
            raise ValueError("database_integrity_provenance_required")
        if (
            self.integrity_checked_at is not None
            and self.integrity_checked_at > self.checked_at
        ):
            raise ValueError("database_integrity_timestamp_invalid")
        if self.compatibility_state == "compatible" and (
            not self.reachable
            or self.schema_revision is None
            or self.integrity_state != "passed"
            or self.policy_state != "passed"
        ):
            raise ValueError("database_compatible_receipt_required")
        if (
            not self.reason_codes
            or len(self.reason_codes) > 8
            or any(
                reason not in get_args(DatabaseHealthReasonV1)
                for reason in self.reason_codes
            )
        ):
            raise ValueError("database_health_reasons_invalid")


class GetDatabaseHealthV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-DB-001"
    OWNER: ClassVar[str] = "PLAN-DB"

    async def __call__(self, request: DatabaseHealthRequestV1) -> DatabaseHealthV1: ...


@dataclass(frozen=True, slots=True)
class SchemaCompatibilityV1(TechnicalValueV1):
    """Opaque catalog revisions, never lexically compared or executed here."""

    CONTRACT_ID: ClassVar[str] = "CTR-DB-001"
    OWNER: ClassVar[str] = "PLAN-DB"
    minimum_readable_revision: str
    minimum_writable_revision: str
    maximum_readable_revision: str
    maximum_writable_revision: str
    migration_target_revision: str
    catalog_digest: str


@dataclass(frozen=True, slots=True)
class RepositoryAndUnitOfWorkTechnicalFamilyV1(TechnicalValueV1):
    """Compatibility declaration; business repositories remain module-owned."""

    CONTRACT_ID: ClassVar[str] = "CTR-DB-002"
    OWNER: ClassVar[str] = "PLAN-DB"
    module_owner: str
    repository_port: str
    unit_of_work_port: str
    module_port_major: int
    persistence_major: int
    table_prefixes: tuple[str, ...]
    mode: Literal["read_only", "read_write", "maintenance"]


@dataclass(frozen=True, slots=True)
class DatabaseSnapshotActivationV1(TechnicalValueV1):
    """Opaque preparation identity; does not authorize or perform activation.

    M08 owns operation authority, DEP quiescence, A04 filesystem operations,
    and PLAN-DB validity. Live receipt/port implementations are later work.
    """

    CONTRACT_ID: ClassVar[str] = "CTR-DB-003"
    OWNER: ClassVar[str] = "PLAN-DB"
    operation_id: OpaqueIdV1
    database_ref: OpaqueIdV1
    candidate_generation: OpaqueIdV1
    preserved_generation: OpaqueIdV1
    quiescence_receipt_id: OpaqueIdV1
    integrity_receipt_id: OpaqueIdV1
    compatibility_receipt_id: OpaqueIdV1
    module_validation_receipt_ids: tuple[OpaqueIdV1, ...]

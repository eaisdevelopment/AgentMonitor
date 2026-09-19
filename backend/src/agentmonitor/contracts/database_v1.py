"""PLAN-DB-owned technical declarations; no ORM, SQL, files or transaction code."""

from dataclasses import dataclass
from typing import ClassVar, Literal

from agentmonitor.contracts.common_v1 import OpaqueIdV1, TechnicalValueV1


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

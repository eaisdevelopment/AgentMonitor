"""Immutable PLAN-FND metadata-only anchor; Alembic owns its version marker.

No business or additional technical tables. This anchor has no destructive
downgrade: preserve the database and use a compatible binary/verified recovery
workflow. A fresh empty initialization needs no preexisting-data backup.
"""

from types import MappingProxyType

revision = "v1_0000"
down_revision = None
branch_labels = None
depends_on = None

METADATA = MappingProxyType(
    {
        "revision": "v1_0000",
        "parent_revision": "",
        "owner": "PLAN-FND",
        "plan_id": "PLAN-FND",
        "requirement_ids": ("NFR-DATA-001", "NFR-COMP-001", "NFR-RES-001"),
        "schema_range": ("v1_0000", "v1_0000", "v1_0000", "v1_0000", "v1_0000"),
        "tables": (),
        "portability_notes": ("Alembic metadata only; no SQLite business DDL",),
        "lock_policy": "exclusive_initialization_and_begin_immediate",
        "downtime_policy": "offline_empty_initialization_only",
        "expected_data_volume": "zero_business_rows",
        "backup_prerequisite": "none_empty_bootstrap",
        "validation_ids": ("single_head", "metadata_only_schema", "full_integrity"),
        "recovery_policy": "preserve_failed_database_no_automatic_retry_or_downgrade",
        "reviewer": "PLAN-DB-migration-steward",
    }
)


def upgrade() -> None:
    """Alembic itself creates/updates alembic_version; no other DDL is needed."""


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

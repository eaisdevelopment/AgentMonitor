"""M05 additive exact event acknowledgement proof; no legacy backfill."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0704"
down_revision = "v1_0703"
branch_labels = None
depends_on = None

TABLES = ("capacity_event_delivery",)
METADATA = MappingProxyType(
    {
        "revision": "v1_0704",
        "parent_revision": "v1_0703",
        "owner": "M05",
        "plan_id": "PLAN-M05",
        "requirement_ids": (
            "FR-QUOTA-003",
            "FR-QUOTA-004",
            "FR-ALERT-001",
            "NFR-DATA-001",
        ),
        "schema_range": ("v1_0704", "v1_0704", "v1_0704", "v1_0704", "v1_0704"),
        "tables": ("capacity_event_delivery",),
        "portability_notes": (
            "Nullable legacy acknowledgement proof remains unknown",
            "Exact opaque receipt reference and canonical digest contain no telemetry",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "existing_capacity_delivery_rows_preserved",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m05_event_delivery_proof",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": (
            "preserve_failed_database_and_restore_verified_backup_or_forward_fix"
        ),
        "reviewer": "root-M05-PLAN-DB-security-review",
    }
)


def upgrade() -> None:
    op.add_column("capacity_event_delivery", sa.Column("ack_receipt_id", sa.String(64)))
    op.add_column(
        "capacity_event_delivery",
        sa.Column(
            "ack_payload_digest",
            sa.String(64),
            sa.CheckConstraint(
                "(ack_receipt_id IS NULL AND ack_payload_digest IS NULL) OR "
                "(ack_receipt_id IS NOT NULL AND ack_payload_digest IS NOT NULL AND "
                "length(ack_receipt_id) BETWEEN 1 AND 64 AND "
                "ack_receipt_id NOT GLOB '*[^A-Za-z0-9_-]*' AND "
                "length(ack_payload_digest)=64 AND "
                "ack_payload_digest NOT GLOB '*[^0-9a-f]*')",
                name="ck_capacity_delivery_proof",
            ),
        ),
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

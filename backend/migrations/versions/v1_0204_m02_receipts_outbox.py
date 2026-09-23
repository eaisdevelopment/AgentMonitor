"""M02 command receipts and module-owned transactional event outbox."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0204"
down_revision = "v1_0203"
branch_labels = None
depends_on = None

METADATA = MappingProxyType(
    {
        "revision": "v1_0204",
        "parent_revision": "v1_0203",
        "owner": "M02",
        "plan_id": "PLAN-M02",
        "requirement_ids": (
            "FR-ACC-001",
            "FR-ACC-002",
            "FR-ACC-005",
            "FR-ACC-006",
            "NFR-COMP-001",
            "NFR-DATA-001",
            "NFR-SEC-001",
        ),
        "schema_range": (
            "v1_0204",
            "v1_0204",
            "v1_0204",
            "v1_0204",
            "v1_0204",
        ),
        "tables": ("reg_command_receipt", "reg_event_outbox"),
        "portability_notes": (
            "Module-owned outbox and idempotency receipts use bounded canonical "
            "payloads",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_receipt_outbox_rows_on_initial_install",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m02_receipt_outbox_tables",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": (
            "preserve_failed_database_and_restore_verified_backup_or_forward_fix"
        ),
        "reviewer": "M02-PLAN-DB-security-review",
    }
)


def upgrade() -> None:
    op.create_table(
        "reg_command_receipt",
        sa.Column("receipt_id", sa.String(64), primary_key=True),
        sa.Column("principal_id", sa.String(64), nullable=False),
        sa.Column("operation_key", sa.String(64), nullable=False),
        sa.Column("idempotency_key_digest", sa.String(64), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("outcome_subject_type", sa.String(32), nullable=False),
        sa.Column("outcome_subject_id", sa.String(64), nullable=False),
        sa.Column("outcome_record_version", sa.Integer(), nullable=False),
        sa.Column("registry_revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("expires_at", sa.String(40), nullable=False),
        sa.UniqueConstraint(
            "principal_id",
            "operation_key",
            "idempotency_key_digest",
            name="uq_reg_receipt_operation_key",
        ),
        sa.CheckConstraint("outcome_record_version > 0", name="ck_reg_receipt_version"),
        sa.CheckConstraint("registry_revision > 0", name="ck_reg_receipt_revision"),
    )
    op.create_index(
        "ix_reg_receipt_expiry", "reg_command_receipt", ["expires_at", "receipt_id"]
    )
    op.create_table(
        "reg_event_outbox",
        sa.Column("event_id", sa.String(64), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("subject_type", sa.String(32), nullable=False),
        sa.Column("subject_id", sa.String(64), nullable=False),
        sa.Column("aggregate_version", sa.Integer(), nullable=False),
        sa.Column("registry_revision", sa.Integer(), nullable=False),
        sa.Column("producer_sequence", sa.Integer(), nullable=False),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("causation_id", sa.String(64)),
        sa.Column("occurred_at", sa.String(40), nullable=False),
        sa.Column("recorded_at", sa.String(40), nullable=False),
        sa.Column("payload_schema", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.String(2048), nullable=False),
        sa.Column("delivery_state", sa.String(32), nullable=False),
        sa.Column("available_at", sa.String(40), nullable=False),
        sa.Column("claimed_at", sa.String(40)),
        sa.Column("delivered_at", sa.String(40)),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.UniqueConstraint("producer_sequence", name="uq_reg_outbox_sequence"),
        sa.CheckConstraint("aggregate_version > 0", name="ck_reg_outbox_version"),
        sa.CheckConstraint("registry_revision > 0", name="ck_reg_outbox_revision"),
        sa.CheckConstraint("producer_sequence > 0", name="ck_reg_outbox_sequence"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_reg_outbox_attempts"),
    )
    op.create_index(
        "ix_reg_outbox_delivery",
        "reg_event_outbox",
        ["delivery_state", "available_at", "producer_sequence"],
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

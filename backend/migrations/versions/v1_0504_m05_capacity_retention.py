"""M05 bounded retention audit state and export-oriented measured indexes."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0504"
down_revision = "v1_0503"
branch_labels = None
depends_on = None

TABLES = ("capacity_retention_run",)

METADATA = MappingProxyType(
    {
        "revision": "v1_0504",
        "parent_revision": "v1_0503",
        "owner": "M05",
        "plan_id": "PLAN-M05",
        "requirement_ids": (
            "FR-HIST-001",
            "FR-HIST-002",
            "FR-HIST-003",
            "FR-HIST-004",
            "NFR-DATA-001",
        ),
        "schema_range": (
            "v1_0504",
            "v1_0504",
            "v1_0504",
            "v1_0504",
            "v1_0504",
        ),
        "tables": ("capacity_retention_run",),
        "portability_notes": (
            "Retention audits bounded deletion without synthetic history or cascades",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_capacity_rows_on_initial_install",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m05_retention_table",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": (
            "preserve_failed_database_and_restore_verified_backup_or_forward_fix"
        ),
        "reviewer": "M05-PLAN-DB-security-review",
    }
)


def upgrade() -> None:
    op.create_table(
        "capacity_retention_run",
        sa.Column("retention_run_id", sa.String(64), primary_key=True),
        sa.Column("policy_id", sa.String(64), nullable=False),
        sa.Column("policy_version", sa.String(32), nullable=False),
        sa.Column("cutoff_at", sa.String(40), nullable=False),
        sa.Column("as_of", sa.String(40), nullable=False),
        sa.Column("preview_digest", sa.String(64), nullable=False),
        sa.Column("idempotency_key_digest", sa.String(64), nullable=False, unique=True),
        sa.Column("export_checkpoint_ref", sa.String(128)),
        sa.Column("expected_generation", sa.Integer(), nullable=False),
        sa.Column("actual_generation", sa.Integer(), nullable=False),
        sa.Column("batch_limit", sa.Integer(), nullable=False),
        sa.Column("batch_count", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("deleted_quota_count", sa.Integer(), nullable=False),
        sa.Column("deleted_budget_count", sa.Integer(), nullable=False),
        sa.Column("deleted_usage_count", sa.Integer(), nullable=False),
        sa.Column("preserved_current_count", sa.Integer(), nullable=False),
        sa.Column("cursor_kind", sa.String(32)),
        sa.Column("cursor_value", sa.String(128)),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("started_at", sa.String(40), nullable=False),
        sa.Column("completed_at", sa.String(40)),
        sa.Column("error_code", sa.String(128)),
        sa.CheckConstraint("batch_limit > 0", name="ck_capacity_retention_batch"),
        sa.CheckConstraint(
            "batch_count >= 0", name="ck_capacity_retention_batch_count"
        ),
        sa.CheckConstraint(
            "length(preview_digest) = 64", name="ck_capacity_retention_preview"
        ),
        sa.CheckConstraint(
            "length(idempotency_key_digest) = 64",
            name="ck_capacity_retention_idempotency",
        ),
        sa.CheckConstraint(
            "expected_generation > 0 AND actual_generation > 0 AND "
            "(state NOT IN ('completed','partial') OR "
            "expected_generation=actual_generation)",
            name="ck_capacity_retention_generation",
        ),
        sa.CheckConstraint(
            "deleted_quota_count >= 0 AND deleted_budget_count >= 0 AND "
            "deleted_usage_count >= 0 AND preserved_current_count >= 0",
            name="ck_capacity_retention_counts",
        ),
        sa.CheckConstraint(
            "state IN ('running','completed','partial','failed')",
            name="ck_capacity_retention_state",
        ),
        sa.CheckConstraint(
            "(cursor_kind IS NULL AND cursor_value IS NULL) OR "
            "(cursor_kind IS NOT NULL AND cursor_value IS NOT NULL)",
            name="ck_capacity_retention_cursor_pair",
        ),
    )
    op.create_index(
        "ix_capacity_retention_started",
        "capacity_retention_run",
        ["started_at", "retention_run_id"],
    )
    op.create_index(
        "ix_capacity_quota_export_cursor",
        "capacity_quota_observation",
        ["stored_at", "observation_id"],
    )
    op.create_index(
        "ix_capacity_budget_export_cursor",
        "capacity_budget_observation",
        ["stored_at", "observation_id"],
    )
    op.create_index(
        "ix_capacity_usage_export_cursor",
        "capacity_usage_bucket",
        ["stored_at", "bucket_id"],
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

"""M04 billing target snapshot and report receipt; existing quota runs unchanged."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0733"
down_revision = "v1_0732"
branch_labels = None
depends_on = None
TABLES = ("collection_budget_run",)
METADATA = MappingProxyType(
    {
        "revision": "v1_0733",
        "parent_revision": "v1_0732",
        "owner": "M04",
        "plan_id": "PLAN-M04",
        "requirement_ids": ("FR-BUDGET-001", "FR-BUDGET-004", "M7-A02"),
        "schema_range": ("v1_0733", "v1_0733", "v1_0733", "v1_0733", "v1_0733"),
        "tables": ("collection_budget_run",),
        "portability_notes": (
            "Bounded target JSON contains only typed nonsecret billing authority",
            "Report references permit genuine empty coverage without fake observations",
            "No foreign key or private-table access crosses into M05 report storage",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_initial_rows_then_one_per_billing_run",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m04_budget_run_schema",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": (
            "preserve_failed_database_and_restore_verified_backup_or_forward_fix"
        ),
        "reviewer": "M04-M7-budget-reports-root-review",
    }
)


def upgrade() -> None:
    op.create_table(
        "collection_budget_run",
        sa.Column("run_id", sa.String(64), primary_key=True),
        sa.Column("canonical_target_json", sa.Text(), nullable=False),
        sa.Column("report_id", sa.String(64), nullable=True),
        sa.Column("consumer_key", sa.String(128), nullable=True),
        sa.Column("consumer_version", sa.String(64), nullable=True),
        sa.Column("receipt_version", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["run_id"], ["collection_run.run_id"], ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "length(CAST(canonical_target_json AS BLOB)) BETWEEN 2 AND 8192",
            name="ck_collection_budget_target_size",
        ),
        sa.CheckConstraint(
            "(report_id IS NULL AND consumer_key IS NULL AND consumer_version IS NULL "
            "AND receipt_version IS NULL) OR (report_id IS NOT NULL "
            "AND consumer_key IS NOT NULL AND consumer_version IS NOT NULL "
            "AND receipt_version IS NOT NULL AND length(report_id) BETWEEN 1 AND 64 "
            "AND length(consumer_key) BETWEEN 1 AND 128 "
            "AND length(consumer_version) BETWEEN 1 AND 64 "
            "AND typeof(receipt_version)='integer' AND receipt_version>=1)",
            name="ck_collection_budget_receipt",
        ),
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

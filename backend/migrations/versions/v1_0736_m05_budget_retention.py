"""Preserve immutable financial commit acknowledgements after bounded expiry."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0736"
down_revision = "v1_0735"
branch_labels = None
depends_on = None
TABLES = ("capacity_budget_expired_report",)
METADATA = MappingProxyType(
    {
        "revision": "v1_0736",
        "parent_revision": "v1_0735",
        "owner": "M05",
        "plan_id": "PLAN-M05",
        "requirement_ids": ("FR-HIST-001", "FR-HIST-003", "FR-HIST-004", "M7-A08"),
        "schema_range": ("v1_0736", "v1_0736", "v1_0736", "v1_0736", "v1_0736"),
        "tables": ("capacity_budget_expired_report",),
        "portability_notes": (
            "Expired report markers preserve receipt identity and provenance",
            "No existing financial facts or report bytes change during migration",
            "Old readers refuse the new expiration semantics before service start",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_initial_markers",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m05_budget_retention_marker",
            "retained_financial_hashes",
            "old_reader_refuses",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": (
            "preserve_failed_database_and_restore_verified_backup_or_forward_fix"
        ),
        "reviewer": "M05-M7-budget-retention-root-review",
    }
)


def upgrade() -> None:
    op.create_table(
        "capacity_budget_expired_report",
        sa.Column("receipt_id", sa.String(64), primary_key=True),
        sa.Column("report_id", sa.String(64), nullable=False, unique=True),
        sa.Column("canonical_provenance_json", sa.Text(), nullable=False),
        sa.Column("expired_at", sa.String(40), nullable=False),
        sa.ForeignKeyConstraint(["receipt_id"], ["capacity_commit_receipt.receipt_id"]),
        sa.CheckConstraint(
            "length(CAST(canonical_provenance_json AS BLOB)) BETWEEN 2 AND 65536",
            name="ck_budget_expired_provenance_size",
        ),
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

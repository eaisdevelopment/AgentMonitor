"""M05 nullable source-reported quota period start."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0710"
down_revision = "v1_0709"
branch_labels = None
depends_on = None
TABLES = ("capacity_quota_observation",)
METADATA = MappingProxyType(
    {
        "revision": "v1_0710",
        "parent_revision": "v1_0709",
        "owner": "M05",
        "plan_id": "PLAN-M05",
        "requirement_ids": ("FR-QUOTA-001", "FR-QUOTA-004", "M6-A04"),
        "schema_range": ("v1_0710", "v1_0710", "v1_0710", "v1_0710", "v1_0710"),
        "tables": ("capacity_quota_observation",),
        "portability_notes": (
            "Nullable timestamp preserves only a source-reported start",
        ),
        "lock_policy": "exclusive_migration",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "one_nullable_column_per_existing_observation",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m05_source_period_schema",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": (
            "preserve_failed_database_and_restore_verified_backup_or_forward_fix"
        ),
        "reviewer": "M05-M6-source-period-review",
    }
)


def upgrade() -> None:
    op.add_column(
        "capacity_quota_observation",
        sa.Column("source_period_start", sa.String(40), nullable=True),
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

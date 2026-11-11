"""M02 nullable owner-selected API setup intent, without enrollment effects."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0730"
down_revision = "v1_0720"
branch_labels = None
depends_on = None
TABLES = ("reg_account",)
METADATA = MappingProxyType(
    {
        "revision": "v1_0730",
        "parent_revision": "v1_0720",
        "owner": "M02",
        "plan_id": "PLAN-M02",
        "requirement_ids": ("FR-ACC-001", "FR-BUDGET-001", "M7-A01"),
        "schema_range": ("v1_0730", "v1_0730", "v1_0730", "v1_0730", "v1_0730"),
        "tables": ("reg_account",),
        "portability_notes": (
            "Nullable checked purpose preserves existing accounts as unspecified",
            "Setup intent does not establish provider identity or enable monitoring",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "one_nullable_column_per_existing_account",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m02_billing_intent_schema",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": (
            "preserve_failed_database_and_restore_verified_backup_or_forward_fix"
        ),
        "reviewer": "M02-M7-billing-intent-root-review",
    }
)


def upgrade() -> None:
    op.add_column(
        "reg_account",
        sa.Column(
            "initial_connection_purpose",
            sa.String(16),
            sa.CheckConstraint(
                "initial_connection_purpose IS NULL "
                "OR initial_connection_purpose='api'",
                name="ck_reg_account_initial_connection_purpose",
            ),
            nullable=True,
        ),
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

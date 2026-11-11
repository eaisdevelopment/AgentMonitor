"""M02 independent API billing connection metadata; no credential material."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0731"
down_revision = "v1_0730"
branch_labels = None
depends_on = None
TABLES = ("reg_billing_connection",)
METADATA = MappingProxyType(
    {
        "revision": "v1_0731",
        "parent_revision": "v1_0730",
        "owner": "M02",
        "plan_id": "PLAN-M02",
        "requirement_ids": ("FR-ACC-001", "FR-BUDGET-001", "M7-A01"),
        "schema_range": ("v1_0731", "v1_0731", "v1_0731", "v1_0731", "v1_0731"),
        "tables": ("reg_billing_connection",),
        "portability_notes": (
            "One billing metadata row per account, bound to its normalized resource",
            "Scope identifiers are metadata; credentials never enter this table",
            "Subscription identity and monitoring columns remain untouched",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_initial_rows_at_most_one_per_account",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m02_billing_connection_schema",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": (
            "preserve_failed_database_and_restore_verified_backup_or_forward_fix"
        ),
        "reviewer": "M02-M7-billing-connections-root-review",
    }
)


def upgrade() -> None:
    op.create_table(
        "reg_billing_connection",
        sa.Column("resource_id", sa.String(64), primary_key=True),
        sa.Column("account_id", sa.String(64), nullable=False, unique=True),
        sa.Column("scope_id", sa.String(128)),
        sa.Column("scope_evidence", sa.String(32), nullable=False),
        sa.Column("scope_generation", sa.Integer(), nullable=False),
        sa.Column("monitoring_preference", sa.String(16), nullable=False),
        sa.Column("lifecycle", sa.String(32), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("registry_revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id", "resource_id"],
            ["reg_account_resource.account_id", "reg_account_resource.resource_id"],
        ),
        sa.CheckConstraint(
            "scope_evidence IN ('unresolved','owner_asserted','provider_verified') "
            "AND ((scope_id IS NULL AND scope_evidence='unresolved') "
            "OR (scope_id IS NOT NULL AND scope_evidence<>'unresolved' "
            "AND length(scope_id) BETWEEN 1 AND 128))",
            name="ck_reg_billing_scope",
        ),
        sa.CheckConstraint("scope_generation>0", name="ck_reg_billing_generation"),
        sa.CheckConstraint("record_version>0", name="ck_reg_billing_version"),
        sa.CheckConstraint("registry_revision>0", name="ck_reg_billing_revision"),
        sa.CheckConstraint(
            "lifecycle IN ('pending','active','disconnected')",
            name="ck_reg_billing_lifecycle",
        ),
        sa.CheckConstraint(
            "monitoring_preference IN ('enabled','disabled') "
            "AND (lifecycle='active' OR monitoring_preference='disabled')",
            name="ck_reg_billing_monitoring",
        ),
        sa.CheckConstraint("updated_at>=created_at", name="ck_reg_billing_timestamps"),
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

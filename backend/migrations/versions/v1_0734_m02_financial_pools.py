"""M02 explicit financial pools and retained owner-association epochs."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0734"
down_revision = "v1_0733"
branch_labels = None
depends_on = None
TABLES = ("reg_financial_pool", "reg_financial_pool_membership")
METADATA = MappingProxyType(
    {
        "revision": "v1_0734",
        "parent_revision": "v1_0733",
        "owner": "M02",
        "plan_id": "PLAN-M02",
        "requirement_ids": ("FR-ORG-003", "FR-BUDGET-001", "M7-A01", "M7-A08"),
        "schema_range": ("v1_0734", "v1_0734", "v1_0734", "v1_0734", "v1_0734"),
        "tables": ("reg_financial_pool", "reg_financial_pool_membership"),
        "portability_notes": (
            "Explicit owner metadata only; no inferred pool backfill",
            "Billing and cloud memberships reference their actual source graphs",
            "Unresolved scope retains exact nonsecret credential binding lineage",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_initial_rows;retained_membership_epochs",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m02_financial_pool_schema",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": (
            "preserve_failed_database_and_restore_verified_backup_or_forward_fix"
        ),
        "reviewer": "M02-M7-financial-pools-root-review",
    }
)


def upgrade() -> None:
    for table, name in (
        ("reg_billing_connection", "uq_reg_billing_pool_resource"),
        ("reg_cloud_monitoring_target", "uq_reg_cloud_pool_resource"),
    ):
        op.create_index(name, table, ["account_id", "resource_id"], unique=True)
    op.create_table(
        "reg_financial_pool",
        sa.Column("pool_id", sa.String(64), primary_key=True),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("selector", sa.String(16), nullable=False),
        sa.Column("primary_organization_id", sa.String(64)),
        sa.Column("display_name", sa.String(256), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("registry_revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.ForeignKeyConstraint(
            ["provider_key"], ["reg_provider_definition.provider_key"]
        ),
        sa.ForeignKeyConstraint(
            ["primary_organization_id"], ["reg_organization.organization_id"]
        ),
        sa.UniqueConstraint("pool_id", "provider_key", "selector"),
        sa.CheckConstraint(
            "(provider_key IN ('claude','codex') AND selector='billing') OR "
            "(provider_key='ollama' AND selector IN ('self','team'))",
            name="ck_reg_financial_pool_provider",
        ),
        sa.CheckConstraint(
            "record_version>0 AND registry_revision>0 AND updated_at>=created_at "
            "AND length(trim(display_name)) BETWEEN 1 AND 256",
            name="ck_reg_financial_pool_metadata",
        ),
    )
    op.create_index(
        "ix_reg_financial_pool_provider",
        "reg_financial_pool",
        ["provider_key", "pool_id"],
    )
    op.create_table(
        "reg_financial_pool_membership",
        sa.Column("association_id", sa.String(64), primary_key=True),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=False),
        sa.Column("billing_resource_id", sa.String(64)),
        sa.Column("cloud_resource_id", sa.String(64)),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("selector", sa.String(16), nullable=False),
        sa.Column("scope_generation", sa.Integer(), nullable=False),
        sa.Column("provider_scope_id", sa.String(128)),
        sa.Column("scope_evidence", sa.String(32), nullable=False),
        sa.Column("binding_id", sa.String(64)),
        sa.Column("binding_generation", sa.Integer()),
        sa.Column("pool_id", sa.String(64), nullable=False),
        sa.Column("association_evidence", sa.String(32), nullable=False),
        sa.Column("valid_from", sa.String(40), nullable=False),
        sa.Column("valid_until", sa.String(40)),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("registry_revision", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id", "billing_resource_id"],
            ["reg_billing_connection.account_id", "reg_billing_connection.resource_id"],
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "cloud_resource_id"],
            [
                "reg_cloud_monitoring_target.account_id",
                "reg_cloud_monitoring_target.resource_id",
            ],
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "binding_id"],
            ["reg_credential_binding.account_id", "reg_credential_binding.binding_id"],
        ),
        sa.ForeignKeyConstraint(
            ["pool_id", "provider_key", "selector"],
            [
                "reg_financial_pool.pool_id",
                "reg_financial_pool.provider_key",
                "reg_financial_pool.selector",
            ],
        ),
        sa.CheckConstraint(
            "(selector='billing' AND billing_resource_id IS NOT NULL "
            "AND billing_resource_id=resource_id AND cloud_resource_id IS NULL) OR "
            "(selector IN ('self','team') AND cloud_resource_id IS NOT NULL "
            "AND cloud_resource_id=resource_id AND billing_resource_id IS NULL)",
            name="ck_reg_financial_membership_source",
        ),
        sa.CheckConstraint(
            "(scope_evidence='unresolved' AND provider_scope_id IS NULL "
            "AND binding_id IS NOT NULL AND binding_generation IS NOT NULL "
            "AND binding_generation>0) OR "
            "(scope_evidence IN ('owner_asserted','provider_verified') "
            "AND provider_scope_id IS NOT NULL "
            "AND length(provider_scope_id) BETWEEN 1 AND 128 "
            "AND binding_id IS NULL AND binding_generation IS NULL)",
            name="ck_reg_financial_membership_scope",
        ),
        sa.CheckConstraint(
            "scope_generation>0 AND record_version>0 AND registry_revision>0 "
            "AND (valid_until IS NULL OR valid_until>valid_from) "
            "AND association_evidence IN ('owner_asserted','provider_verified')",
            name="ck_reg_financial_membership_epoch",
        ),
    )
    op.create_index(
        "uq_reg_financial_membership_current",
        "reg_financial_pool_membership",
        ["resource_id", "selector"],
        unique=True,
        sqlite_where=sa.text("valid_until IS NULL"),
    )
    op.create_index(
        "ix_reg_financial_membership_pool",
        "reg_financial_pool_membership",
        ["pool_id", "provider_scope_id"],
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

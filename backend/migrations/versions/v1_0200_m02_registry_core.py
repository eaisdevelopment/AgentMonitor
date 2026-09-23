"""M02 registry core: revisions, organizations, providers, accounts, history."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0200"
down_revision = "v1_0100"
branch_labels = None
depends_on = None

METADATA = MappingProxyType(
    {
        "revision": "v1_0200",
        "parent_revision": "v1_0100",
        "owner": "M02",
        "plan_id": "PLAN-M02",
        "requirement_ids": (
            "FR-ORG-001",
            "FR-ORG-002",
            "FR-ORG-003",
            "FR-ACC-001",
            "FR-ACC-002",
            "FR-ACC-003",
            "NFR-DATA-001",
            "NFR-SEC-001",
        ),
        "schema_range": (
            "v1_0200",
            "v1_0200",
            "v1_0200",
            "v1_0200",
            "v1_0200",
        ),
        "tables": (
            "reg_registry_state",
            "reg_organization",
            "reg_provider_definition",
            "reg_account",
            "reg_registry_change",
        ),
        "portability_notes": (
            "Portable text identifiers and UTC instants; M02-local foreign keys only",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_registry_rows_on_initial_install",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m02_core_tables",
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
        "reg_registry_state",
        sa.Column("singleton_key", sa.Integer(), primary_key=True),
        sa.Column("registry_revision", sa.Integer(), nullable=False),
        sa.Column("domain_policy_version", sa.String(32), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.CheckConstraint("singleton_key = 1", name="ck_reg_state_singleton"),
        sa.CheckConstraint("registry_revision >= 0", name="ck_reg_state_revision"),
    )
    op.create_table(
        "reg_organization",
        sa.Column("organization_id", sa.String(64), primary_key=True),
        sa.Column("normalized_name", sa.String(256), nullable=False),
        sa.Column("display_name", sa.String(256), nullable=False),
        sa.Column("description", sa.String(1024)),
        sa.Column("lifecycle", sa.String(16), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.Column("archived_at", sa.String(40)),
        sa.Column("creation_command_digest", sa.String(64), nullable=False),
        sa.CheckConstraint("length(display_name) > 0", name="ck_reg_org_name"),
        sa.CheckConstraint("display_order >= 0", name="ck_reg_org_order"),
        sa.CheckConstraint("record_version > 0", name="ck_reg_org_version"),
        sa.CheckConstraint(
            "(lifecycle = 'active' AND archived_at IS NULL) OR "
            "(lifecycle = 'archived' AND archived_at IS NOT NULL)",
            name="ck_reg_org_lifecycle",
        ),
    )
    op.create_index(
        "ix_reg_org_lifecycle_order",
        "reg_organization",
        ["lifecycle", "display_order", "organization_id"],
        unique=True,
    )
    op.create_index(
        "ix_reg_org_normalized_name",
        "reg_organization",
        ["normalized_name", "lifecycle"],
    )
    op.create_table(
        "reg_provider_definition",
        sa.Column("provider_key", sa.String(64), primary_key=True),
        sa.Column("manifest_reference", sa.String(128), nullable=False),
        sa.Column("lifecycle", sa.String(16), nullable=False),
        sa.Column("first_admitted_at", sa.String(40), nullable=False),
        sa.Column("last_admitted_at", sa.String(40), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.CheckConstraint("length(provider_key) > 0", name="ck_reg_provider_key"),
        sa.CheckConstraint("record_version > 0", name="ck_reg_provider_version"),
    )
    op.create_table(
        "reg_account",
        sa.Column("account_id", sa.String(64), primary_key=True),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("friendly_name", sa.String(256), nullable=False),
        sa.Column("normalized_name", sa.String(256), nullable=False),
        sa.Column("organization_id", sa.String(64)),
        sa.Column("lifecycle", sa.String(32), nullable=False),
        sa.Column("identity_state", sa.String(40), nullable=False),
        sa.Column("monitoring_preference", sa.String(16), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.Column("archived_at", sa.String(40)),
        sa.Column("creation_command_digest", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(
            ["provider_key"], ["reg_provider_definition.provider_key"]
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["reg_organization.organization_id"]
        ),
        sa.CheckConstraint("length(friendly_name) > 0", name="ck_reg_account_name"),
        sa.CheckConstraint("record_version > 0", name="ck_reg_account_version"),
        sa.CheckConstraint(
            "monitoring_preference IN ('enabled', 'disabled')",
            name="ck_reg_account_monitoring",
        ),
        sa.CheckConstraint(
            "(lifecycle = 'archived' AND archived_at IS NOT NULL) OR "
            "(lifecycle <> 'archived' AND archived_at IS NULL)",
            name="ck_reg_account_lifecycle",
        ),
    )
    op.create_index(
        "ix_reg_account_org_lifecycle_name",
        "reg_account",
        ["organization_id", "lifecycle", "normalized_name", "account_id"],
    )
    op.create_index(
        "ix_reg_account_provider_lifecycle",
        "reg_account",
        ["provider_key", "lifecycle", "account_id"],
    )
    op.create_table(
        "reg_registry_change",
        sa.Column("change_id", sa.String(64), primary_key=True),
        sa.Column("subject_type", sa.String(32), nullable=False),
        sa.Column("subject_id", sa.String(64), nullable=False),
        sa.Column("aggregate_version", sa.Integer(), nullable=False),
        sa.Column("registry_revision", sa.Integer(), nullable=False),
        sa.Column("change_kind", sa.String(64), nullable=False),
        sa.Column("previous_name", sa.String(256)),
        sa.Column("new_name", sa.String(256)),
        sa.Column("previous_organization_id", sa.String(64)),
        sa.Column("new_organization_id", sa.String(64)),
        sa.Column("previous_lifecycle", sa.String(32)),
        sa.Column("new_lifecycle", sa.String(32)),
        sa.Column("actor_class", sa.String(32), nullable=False),
        sa.Column("actor_id", sa.String(64), nullable=False),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("command_digest", sa.String(64), nullable=False),
        sa.Column("occurred_at", sa.String(40), nullable=False),
        sa.Column("recorded_at", sa.String(40), nullable=False),
        sa.Column("expires_at", sa.String(40), nullable=False),
        sa.CheckConstraint("aggregate_version > 0", name="ck_reg_change_version"),
        sa.CheckConstraint("registry_revision > 0", name="ck_reg_change_revision"),
    )
    op.create_index(
        "ix_reg_change_subject_time",
        "reg_registry_change",
        ["subject_type", "subject_id", "occurred_at", "change_id"],
    )
    op.create_index(
        "ix_reg_change_expiry", "reg_registry_change", ["expires_at", "change_id"]
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

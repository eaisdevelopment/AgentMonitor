"""M02 owner-asserted credential binding lifecycle; no credential values."""

# ruff: noqa: E501 -- schema predicates and immutable metadata are explicit.

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0709"
down_revision = "v1_0708"
branch_labels = None
depends_on = None
TABLES = ("reg_credential_binding_state", "reg_credential_binding")
METADATA = MappingProxyType(
    {
        "revision": "v1_0709",
        "parent_revision": "v1_0708",
        "owner": "M02",
        "plan_id": "PLAN-M02",
        "requirement_ids": (
            "FR-ACC-001",
            "FR-SAFE-001",
            "M6-A03",
            "M6-A09",
            "NFR-DATA-001",
        ),
        "schema_range": ("v1_0709", "v1_0709", "v1_0709", "v1_0709", "v1_0709"),
        "tables": ("reg_credential_binding_state", "reg_credential_binding"),
        "portability_notes": (
            "Global binding identifiers are unique and each account has at most one active and one pending item",
            "Credentials and provider profile locations are never stored",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "one_state_per_account_and_one_row_per_binding",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m02_credential_binding_schema",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": "preserve_failed_database_and_restore_verified_backup_or_forward_fix",
        "reviewer": "M02-M6-credential-security-review",
    }
)


def upgrade() -> None:
    op.create_table(
        "reg_credential_binding_state",
        sa.Column("account_id", sa.String(64), primary_key=True),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("binding_generation", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["reg_account.account_id"]),
        sa.CheckConstraint(
            "record_version > 0 AND binding_generation >= 0",
            name="ck_reg_binding_state_versions",
        ),
    )
    op.create_table(
        "reg_credential_binding",
        sa.Column("binding_id", sa.String(64), primary_key=True),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("lifecycle", sa.String(32), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("association_provenance", sa.String(32), nullable=False),
        sa.Column("reason_code", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"], ["reg_credential_binding_state.account_id"]
        ),
        sa.CheckConstraint(
            "length(binding_id) = 37 AND substr(binding_id, 1, 5) = 'amcb_' AND substr(binding_id, 6) NOT GLOB '*[^a-f0-9]*'",
            name="ck_reg_binding_id",
        ),
        sa.CheckConstraint("generation > 0", name="ck_reg_binding_generation"),
        sa.CheckConstraint(
            "association_provenance = 'owner_asserted'",
            name="ck_reg_binding_provenance",
        ),
        sa.CheckConstraint(
            "lifecycle IN ('pending','active','cleanup_pending','cleanup_complete')",
            name="ck_reg_binding_lifecycle",
        ),
        sa.CheckConstraint(
            "reason_code IN ('owner_prepared','owner_activated','rotation_replaced','pending_cleanup_requested','owner_disconnected','account_archived','account_deleted','local_cleanup_completed')",
            name="ck_reg_binding_reason",
        ),
    )
    op.create_index(
        "uq_reg_binding_one_active",
        "reg_credential_binding",
        ["account_id"],
        unique=True,
        sqlite_where=sa.text("lifecycle = 'active'"),
    )
    op.create_index(
        "uq_reg_binding_one_pending",
        "reg_credential_binding",
        ["account_id"],
        unique=True,
        sqlite_where=sa.text("lifecycle = 'pending'"),
    )
    op.create_index(
        "ix_reg_binding_cleanup", "reg_credential_binding", ["account_id", "lifecycle"]
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

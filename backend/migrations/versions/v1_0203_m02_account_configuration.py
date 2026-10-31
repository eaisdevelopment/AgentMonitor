"""M02 opaque account configuration references and registry query indexes."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0203"
down_revision = "v1_0202"
branch_labels = None
depends_on = None

METADATA = MappingProxyType(
    {
        "revision": "v1_0203",
        "parent_revision": "v1_0202",
        "owner": "M02",
        "plan_id": "PLAN-M02",
        "requirement_ids": (
            "FR-ACC-003",
            "FR-ACC-004",
            "NFR-ARCH-002",
            "NFR-DATA-001",
            "NFR-SEC-001",
        ),
        "schema_range": (
            "v1_0203",
            "v1_0203",
            "v1_0203",
            "v1_0203",
            "v1_0203",
        ),
        "tables": ("reg_account_configuration_reference",),
        "portability_notes": (
            "Opaque scalar references only; no cross-module foreign key or "
            "copied setting",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_configuration_reference_rows_on_initial_install",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m02_configuration_reference_table",
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
        "reg_account_configuration_reference",
        sa.Column("configuration_reference_id", sa.String(64), primary_key=True),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("owner_namespace", sa.String(64), nullable=False),
        sa.Column("reference_kind", sa.String(64), nullable=False),
        sa.Column("referenced_record_id", sa.String(64), nullable=False),
        sa.Column("lifecycle", sa.String(32), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.Column("invalidated_at", sa.String(40)),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("command_digest", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["reg_account.account_id"]),
        sa.UniqueConstraint(
            "account_id",
            "owner_namespace",
            "reference_kind",
            "lifecycle",
            name="uq_reg_config_reference_lifecycle",
        ),
        sa.CheckConstraint("record_version > 0", name="ck_reg_config_version"),
    )
    op.create_index(
        "ix_reg_config_account_owner",
        "reg_account_configuration_reference",
        ["account_id", "owner_namespace", "reference_kind", "lifecycle"],
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

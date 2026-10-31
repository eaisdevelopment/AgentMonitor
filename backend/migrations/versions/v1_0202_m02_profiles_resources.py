"""M02 private monitoring profiles and normalized account resource graph."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0202"
down_revision = "v1_0201"
branch_labels = None
depends_on = None

METADATA = MappingProxyType(
    {
        "revision": "v1_0202",
        "parent_revision": "v1_0201",
        "owner": "M02",
        "plan_id": "PLAN-M02",
        "requirement_ids": (
            "FR-ACC-004",
            "FR-ACC-006",
            "FR-AUTH-002",
            "FR-AUTH-005",
            "NFR-DATA-001",
            "NFR-SEC-001",
        ),
        "schema_range": (
            "v1_0202",
            "v1_0202",
            "v1_0202",
            "v1_0202",
            "v1_0202",
        ),
        "tables": (
            "reg_monitoring_profile",
            "reg_account_resource",
            "reg_profile_resource_link",
        ),
        "portability_notes": (
            "Private locator references remain M02-only; resource graph uses "
            "M02-local keys",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_profile_resource_rows_on_initial_install",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m02_profile_resource_tables",
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
        "reg_monitoring_profile",
        sa.Column("profile_id", sa.String(64), primary_key=True),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("provider_installation_id", sa.String(64), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("lifecycle", sa.String(32), nullable=False),
        sa.Column("management_state", sa.String(32), nullable=False),
        sa.Column("compatibility_state", sa.String(32), nullable=False),
        sa.Column("private_locator_ref", sa.String(512), nullable=False),
        sa.Column("locator_scheme", sa.String(64), nullable=False),
        sa.Column("locator_scheme_version", sa.Integer(), nullable=False),
        sa.Column("locator_fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("protected_default_profile", sa.Integer(), nullable=False),
        sa.Column("identity_verification_state", sa.String(40), nullable=False),
        sa.Column("expected_identity_claim_id", sa.String(64)),
        sa.Column("last_verification_reference", sa.String(128)),
        sa.Column("last_verified_at", sa.String(40)),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.Column("archived_at", sa.String(40)),
        sa.ForeignKeyConstraint(["account_id"], ["reg_account.account_id"]),
        sa.ForeignKeyConstraint(
            ["provider_installation_id"],
            ["reg_provider_installation.provider_installation_id"],
        ),
        sa.ForeignKeyConstraint(
            ["expected_identity_claim_id"], ["reg_provider_identity_claim.claim_id"]
        ),
        sa.UniqueConstraint(
            "account_id", "profile_id", name="uq_reg_profile_account_identity"
        ),
        sa.CheckConstraint(
            "management_state IN "
            "('managed', 'provider_default', 'unmanaged', 'unknown')",
            name="ck_reg_profile_management",
        ),
        sa.CheckConstraint(
            "compatibility_state IN "
            "('compatible', 'incompatible', 'unknown', 'unavailable')",
            name="ck_reg_profile_compatibility",
        ),
        sa.CheckConstraint(
            "(protected_default_profile = 1 AND management_state = 'provider_default') "
            "OR (protected_default_profile = 0 "
            "AND management_state <> 'provider_default')",
            name="ck_reg_profile_default_management",
        ),
        sa.CheckConstraint(
            "protected_default_profile IN (0, 1)", name="ck_reg_profile_protected"
        ),
        sa.CheckConstraint("locator_scheme_version > 0", name="ck_reg_profile_locator"),
        sa.CheckConstraint("record_version > 0", name="ck_reg_profile_version"),
    )
    op.create_index(
        "ix_reg_profile_account_lifecycle",
        "reg_monitoring_profile",
        ["account_id", "lifecycle", "profile_id"],
    )
    op.create_index(
        "ix_reg_profile_installation_lifecycle",
        "reg_monitoring_profile",
        ["provider_installation_id", "lifecycle", "profile_id"],
    )
    op.create_table(
        "reg_account_resource",
        sa.Column("resource_id", sa.String(64), primary_key=True),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("provider_specific_kind", sa.String(64)),
        sa.Column("provider_specific_kind_version", sa.Integer()),
        sa.Column("parent_resource_id", sa.String(64)),
        sa.Column("safe_label_state", sa.String(32), nullable=False),
        sa.Column("safe_masked_label", sa.String(64)),
        sa.Column("provider_resource_fingerprint", sa.String(64)),
        sa.Column("identity_scheme", sa.String(64)),
        sa.Column("identity_scheme_version", sa.Integer()),
        sa.Column("lifecycle", sa.String(32), nullable=False),
        sa.Column("first_verified_at", sa.String(40)),
        sa.Column("last_verified_at", sa.String(40)),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["reg_account.account_id"]),
        sa.ForeignKeyConstraint(
            ["account_id", "parent_resource_id"],
            ["reg_account_resource.account_id", "reg_account_resource.resource_id"],
        ),
        sa.UniqueConstraint(
            "account_id", "resource_id", name="uq_reg_resource_account_identity"
        ),
        sa.CheckConstraint(
            "parent_resource_id IS NULL OR parent_resource_id <> resource_id",
            name="ck_reg_resource_not_self_parent",
        ),
        sa.CheckConstraint("record_version > 0", name="ck_reg_resource_version"),
    )
    op.create_index(
        "ix_reg_resource_account_kind",
        "reg_account_resource",
        ["account_id", "lifecycle", "kind", "resource_id"],
    )
    op.create_index(
        "ix_reg_resource_parent", "reg_account_resource", ["parent_resource_id"]
    )
    op.create_table(
        "reg_profile_resource_link",
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("profile_id", sa.String(64), primary_key=True),
        sa.Column("resource_id", sa.String(64), primary_key=True),
        sa.Column("evidence_class", sa.String(40), nullable=False),
        sa.Column("evidence_reference", sa.String(128), nullable=False),
        sa.Column("owner_confirmed", sa.Integer(), nullable=False),
        sa.Column("owner_confirmed_at", sa.String(40)),
        sa.Column("valid_from", sa.String(40), nullable=False),
        sa.Column("invalidated_at", sa.String(40)),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id", "profile_id"],
            ["reg_monitoring_profile.account_id", "reg_monitoring_profile.profile_id"],
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "resource_id"],
            ["reg_account_resource.account_id", "reg_account_resource.resource_id"],
        ),
        sa.CheckConstraint("owner_confirmed IN (0, 1)", name="ck_reg_link_confirmed"),
        sa.CheckConstraint("record_version > 0", name="ck_reg_link_version"),
    )
    op.create_index(
        "ix_reg_link_resource",
        "reg_profile_resource_link",
        ["resource_id", "profile_id"],
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

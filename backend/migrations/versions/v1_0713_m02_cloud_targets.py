"""M02 cloud access targets and generation-bound verification receipts."""

# ruff: noqa: E501 -- immutable metadata and schema predicates remain explicit.

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0713"
down_revision = "v1_0712"
branch_labels = None
depends_on = None
TABLES = (
    "reg_provider_access_target",
    "reg_cloud_monitoring_target",
    "reg_credential_binding_verification",
)
METADATA = MappingProxyType(
    {
        "revision": "v1_0713",
        "parent_revision": "v1_0712",
        "owner": "M02",
        "plan_id": "PLAN-M02",
        "requirement_ids": (
            "FR-ACC-001",
            "FR-COL-004",
            "FR-SAFE-001",
            "M6-A03",
            "M6-A04",
            "NFR-DATA-001",
        ),
        "schema_range": ("v1_0713", "v1_0713", "v1_0713", "v1_0713", "v1_0713"),
        "tables": (
            "reg_provider_access_target",
            "reg_cloud_monitoring_target",
            "reg_credential_binding_verification",
        ),
        "portability_notes": (
            "Cloud service targets remain distinct from locally discovered installations",
            "Verification receipts bind one successful run to an exact credential generation without storing credentials",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "one_cloud_target_per_authority;one_monitoring_target_per_account;one_receipt_per_successful_verification",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m02_cloud_target_verification_schema",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": "preserve_failed_database_and_restore_verified_backup_or_forward_fix",
        "reviewer": "M02-M6-cloud-target-review",
    }
)


def upgrade() -> None:
    op.create_index(
        "uq_reg_binding_account_id",
        "reg_credential_binding",
        ["account_id", "binding_id"],
        unique=True,
    )
    op.create_table(
        "reg_provider_access_target",
        sa.Column("access_target_id", sa.String(64), primary_key=True),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("target_kind", sa.String(32), nullable=False),
        sa.Column("authority_id", sa.String(128), nullable=False),
        sa.Column("manifest_fingerprint", sa.String(64), nullable=False),
        sa.Column("lifecycle", sa.String(16), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.ForeignKeyConstraint(
            ["provider_key"], ["reg_provider_definition.provider_key"]
        ),
        sa.UniqueConstraint(
            "provider_key", "authority_id", name="uq_reg_access_target_authority"
        ),
        sa.CheckConstraint(
            "length(access_target_id)=37 AND substr(access_target_id,1,5)='amat_' AND substr(access_target_id,6) NOT GLOB '*[^a-f0-9]*'",
            name="ck_reg_access_target_id",
        ),
        sa.CheckConstraint(
            "target_kind='cloud_service'", name="ck_reg_access_target_kind"
        ),
        sa.CheckConstraint(
            "lifecycle IN ('active','disabled')", name="ck_reg_access_target_lifecycle"
        ),
        sa.CheckConstraint(
            "length(manifest_fingerprint)=64 AND manifest_fingerprint NOT GLOB '*[^a-f0-9]*'",
            name="ck_reg_access_target_manifest",
        ),
        sa.CheckConstraint("record_version > 0", name="ck_reg_access_target_version"),
    )
    op.create_index(
        "ix_reg_access_target_provider",
        "reg_provider_access_target",
        ["provider_key", "lifecycle", "access_target_id"],
    )
    op.create_table(
        "reg_cloud_monitoring_target",
        sa.Column("profile_id", sa.String(64), primary_key=True),
        sa.Column("resource_id", sa.String(64), nullable=False, unique=True),
        sa.Column("account_id", sa.String(64), nullable=False, unique=True),
        sa.Column("access_target_id", sa.String(64), nullable=False),
        sa.Column("binding_id", sa.String(64), nullable=False),
        sa.Column("binding_generation", sa.Integer(), nullable=False),
        sa.Column("lifecycle", sa.String(16), nullable=False),
        sa.Column("identity_state", sa.String(32), nullable=False),
        sa.Column("owner_principal_id", sa.String(64), nullable=False),
        sa.Column("owner_asserted_at", sa.String(40), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["reg_account.account_id"]),
        sa.ForeignKeyConstraint(
            ["access_target_id"], ["reg_provider_access_target.access_target_id"]
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "binding_id"],
            ["reg_credential_binding.account_id", "reg_credential_binding.binding_id"],
        ),
        sa.CheckConstraint(
            "binding_generation > 0 AND record_version > 0",
            name="ck_reg_cloud_monitoring_versions",
        ),
        sa.CheckConstraint(
            "lifecycle IN ('active','disabled','archived')",
            name="ck_reg_cloud_monitoring_lifecycle",
        ),
        sa.CheckConstraint(
            "identity_state='owner_confirmed'",
            name="ck_reg_cloud_monitoring_identity",
        ),
    )
    op.create_index(
        "ix_reg_cloud_monitoring_target",
        "reg_cloud_monitoring_target",
        ["access_target_id", "lifecycle", "account_id"],
    )
    op.create_table(
        "reg_credential_binding_verification",
        sa.Column("verification_id", sa.String(64), primary_key=True),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("binding_id", sa.String(64), nullable=False),
        sa.Column("binding_generation", sa.Integer(), nullable=False),
        sa.Column("access_target_id", sa.String(64), nullable=False),
        sa.Column("run_id", sa.String(64), nullable=False, unique=True),
        sa.Column("admission_id", sa.String(64), nullable=False, unique=True),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("adapter_version", sa.String(64), nullable=False),
        sa.Column("manifest_fingerprint", sa.String(64), nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("verified_at", sa.String(40), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id", "binding_id"],
            ["reg_credential_binding.account_id", "reg_credential_binding.binding_id"],
        ),
        sa.ForeignKeyConstraint(
            ["access_target_id"], ["reg_provider_access_target.access_target_id"]
        ),
        sa.UniqueConstraint(
            "account_id",
            "binding_id",
            "binding_generation",
            name="uq_reg_binding_verification_generation",
        ),
        sa.CheckConstraint(
            "length(verification_id)=37 AND substr(verification_id,1,5)='amvr_' AND substr(verification_id,6) NOT GLOB '*[^a-f0-9]*'",
            name="ck_reg_binding_verification_id",
        ),
        sa.CheckConstraint(
            "binding_generation > 0 AND record_version=1",
            name="ck_reg_binding_verification_version",
        ),
        sa.CheckConstraint(
            "source_id='ollama.cloud.balance.v1'",
            name="ck_reg_binding_verification_source",
        ),
        sa.CheckConstraint(
            "length(manifest_fingerprint)=64 AND manifest_fingerprint NOT GLOB '*[^a-f0-9]*' AND length(payload_digest)=64 AND payload_digest NOT GLOB '*[^a-f0-9]*'",
            name="ck_reg_binding_verification_digests",
        ),
    )
    op.create_index(
        "ix_reg_binding_verification_current",
        "reg_credential_binding_verification",
        ["account_id", "binding_id", "binding_generation", "verified_at"],
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

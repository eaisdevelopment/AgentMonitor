"""M02 immutable history for superseded credential verification receipts."""

# ruff: noqa: E501 -- immutable metadata and schema predicates remain explicit.

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0718"
down_revision = "v1_0717"
branch_labels = None
depends_on = None
TABLES = ("reg_credential_binding_verification_history",)
METADATA = MappingProxyType(
    {
        "revision": "v1_0718",
        "parent_revision": "v1_0717",
        "owner": "M02",
        "plan_id": "PLAN-M02",
        "requirement_ids": (
            "FR-ACC-001",
            "FR-COL-004",
            "FR-SAFE-001",
            "M6-A03",
            "M6-A04",
            "M6-A07",
            "M6-A09",
            "NFR-DATA-001",
        ),
        "schema_range": ("v1_0718", "v1_0718", "v1_0718", "v1_0718", "v1_0718"),
        "tables": ("reg_credential_binding_verification_history",),
        "portability_notes": (
            "The current receipt remains one row per credential generation",
            "Superseded exact run and admission lineage remains immutable and queryable",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "one historical row per superseded successful verification",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m02_credential_verification_history_schema",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": "preserve_failed_database_and_restore_verified_backup_or_forward_fix",
        "reviewer": "M02-M6-verification-history-independent-review",
    }
)


def upgrade() -> None:
    op.create_table(
        "reg_credential_binding_verification_history",
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
        sa.Column("superseded_at", sa.String(40), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id", "binding_id"],
            ["reg_credential_binding.account_id", "reg_credential_binding.binding_id"],
        ),
        sa.ForeignKeyConstraint(
            ["access_target_id"], ["reg_provider_access_target.access_target_id"]
        ),
        sa.CheckConstraint(
            "length(verification_id)=37 AND substr(verification_id,1,5)='amvr_' AND substr(verification_id,6) NOT GLOB '*[^a-f0-9]*'",
            name="ck_reg_binding_verification_history_id",
        ),
        sa.CheckConstraint(
            "binding_generation > 0 AND record_version=1",
            name="ck_reg_binding_verification_history_version",
        ),
        sa.CheckConstraint(
            "source_id='ollama.cloud.balance.v1'",
            name="ck_reg_binding_verification_history_source",
        ),
        sa.CheckConstraint(
            "length(manifest_fingerprint)=64 AND manifest_fingerprint NOT GLOB '*[^a-f0-9]*' AND length(payload_digest)=64 AND payload_digest NOT GLOB '*[^a-f0-9]*'",
            name="ck_reg_binding_verification_history_digests",
        ),
        sa.CheckConstraint(
            "superseded_at > verified_at",
            name="ck_reg_binding_verification_history_order",
        ),
    )
    op.create_index(
        "ix_reg_binding_verification_history_binding",
        "reg_credential_binding_verification_history",
        [
            "account_id",
            "binding_id",
            "binding_generation",
            "verified_at",
            "verification_id",
        ],
    )
    for table, other in (
        (
            "reg_credential_binding_verification",
            "reg_credential_binding_verification_history",
        ),
        (
            "reg_credential_binding_verification_history",
            "reg_credential_binding_verification",
        ),
    ):
        stem = (
            "current"
            if table == "reg_credential_binding_verification"
            else "history"
        )
        for operation in ("INSERT", "UPDATE"):
            op.execute(
                f"CREATE TRIGGER ck_reg_binding_verification_{stem}_{operation.lower()} "
                f"BEFORE {operation} ON {table} WHEN EXISTS (SELECT 1 FROM {other} "
                "WHERE verification_id=NEW.verification_id OR run_id=NEW.run_id "
                "OR admission_id=NEW.admission_id) BEGIN SELECT "
                "RAISE(ABORT,'credential_binding_verification_lineage_conflict'); END"
            )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

"""M02 provider installation, candidate, identity claim, and decision records."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0201"
down_revision = "v1_0200"
branch_labels = None
depends_on = None

METADATA = MappingProxyType(
    {
        "revision": "v1_0201",
        "parent_revision": "v1_0200",
        "owner": "M02",
        "plan_id": "PLAN-M02",
        "requirement_ids": (
            "FR-ACC-001",
            "FR-ACC-005",
            "FR-ACC-006",
            "NFR-DATA-001",
            "NFR-SEC-001",
        ),
        "schema_range": (
            "v1_0201",
            "v1_0201",
            "v1_0201",
            "v1_0201",
            "v1_0201",
        ),
        "tables": (
            "reg_provider_installation",
            "reg_discovery_candidate",
            "reg_provider_identity_claim",
            "reg_identity_decision",
        ),
        "portability_notes": (
            "Identity digests are bounded text; no provider payload or "
            "cross-module key",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_provider_rows_on_initial_install",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m02_provider_identity_tables",
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
        "reg_provider_installation",
        sa.Column("provider_installation_id", sa.String(64), primary_key=True),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("installation_identity_scheme", sa.String(64), nullable=False),
        sa.Column("installation_identity_fingerprint", sa.String(64), nullable=False),
        sa.Column("platform_key", sa.String(64), nullable=False),
        sa.Column("reported_version", sa.String(128)),
        sa.Column("version_state", sa.String(32), nullable=False),
        sa.Column("presence_state", sa.String(32), nullable=False),
        sa.Column("first_seen_at", sa.String(40), nullable=False),
        sa.Column("last_seen_at", sa.String(40), nullable=False),
        sa.Column("last_discovery_operation_id", sa.String(64), nullable=False),
        sa.Column("compatibility_reference", sa.String(128), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["provider_key"], ["reg_provider_definition.provider_key"]
        ),
        sa.UniqueConstraint(
            "provider_key",
            "platform_key",
            "installation_identity_scheme",
            "installation_identity_fingerprint",
            name="uq_reg_installation_identity",
        ),
        sa.CheckConstraint("record_version > 0", name="ck_reg_installation_version"),
    )
    op.create_index(
        "ix_reg_installation_presence",
        "reg_provider_installation",
        ["provider_key", "presence_state", "last_seen_at"],
    )
    op.create_table(
        "reg_discovery_candidate",
        sa.Column("candidate_id", sa.String(64), primary_key=True),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("provider_installation_id", sa.String(64), nullable=False),
        sa.Column("candidate_kind", sa.String(32), nullable=False),
        sa.Column("source_operation_id", sa.String(64), nullable=False),
        sa.Column("source_schema", sa.String(64), nullable=False),
        sa.Column("source_class", sa.String(64), nullable=False),
        sa.Column("source_identity_fingerprint", sa.String(64), nullable=False),
        sa.Column("evidence_class", sa.String(40), nullable=False),
        sa.Column("evidence_reference", sa.String(128), nullable=False),
        sa.Column("association_state", sa.String(40), nullable=False),
        sa.Column("associated_subject_id", sa.String(64)),
        sa.Column("reason_code", sa.String(128), nullable=False),
        sa.Column("first_seen_at", sa.String(40), nullable=False),
        sa.Column("last_seen_at", sa.String(40), nullable=False),
        sa.Column("reviewed_at", sa.String(40)),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.String(40), nullable=False),
        sa.ForeignKeyConstraint(
            ["provider_installation_id"],
            ["reg_provider_installation.provider_installation_id"],
        ),
        sa.UniqueConstraint(
            "provider_key",
            "source_identity_fingerprint",
            name="uq_reg_candidate_source_identity",
        ),
        sa.CheckConstraint("record_version > 0", name="ck_reg_candidate_version"),
    )
    op.create_index(
        "ix_reg_candidate_state_seen",
        "reg_discovery_candidate",
        ["provider_key", "association_state", "last_seen_at", "candidate_id"],
    )
    op.create_table(
        "reg_provider_identity_claim",
        sa.Column("claim_id", sa.String(64), primary_key=True),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("identity_scheme", sa.String(64), nullable=False),
        sa.Column("identity_scope", sa.String(64), nullable=False),
        sa.Column("identity_scheme_version", sa.Integer(), nullable=False),
        sa.Column("subject_fingerprint", sa.String(64), nullable=False),
        sa.Column("account_id", sa.String(64)),
        sa.Column("evidence_class", sa.String(40), nullable=False),
        sa.Column("decision_state", sa.String(40), nullable=False),
        sa.Column("evidence_reference", sa.String(128), nullable=False),
        sa.Column("valid_from", sa.String(40), nullable=False),
        sa.Column("invalidated_at", sa.String(40)),
        sa.Column("last_verified_at", sa.String(40)),
        sa.Column("owner_principal_id", sa.String(64)),
        sa.Column("owner_confirmed_at", sa.String(40)),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["reg_account.account_id"]),
        sa.UniqueConstraint(
            "provider_key",
            "identity_scheme",
            "identity_scope",
            "subject_fingerprint",
            name="uq_reg_identity_claim_scope",
        ),
        sa.CheckConstraint("identity_scheme_version > 0", name="ck_reg_claim_scheme"),
        sa.CheckConstraint("record_version > 0", name="ck_reg_claim_version"),
    )
    op.create_table(
        "reg_identity_decision",
        sa.Column("decision_id", sa.String(64), primary_key=True),
        sa.Column("candidate_id", sa.String(64)),
        sa.Column("claim_id", sa.String(64)),
        sa.Column("profile_id", sa.String(64)),
        sa.Column("account_id", sa.String(64)),
        sa.Column("decision_state", sa.String(40), nullable=False),
        sa.Column("evidence_class", sa.String(40), nullable=False),
        sa.Column("reason_code", sa.String(128), nullable=False),
        sa.Column("evidence_set_digest", sa.String(64), nullable=False),
        sa.Column("source_contract_version", sa.String(32), nullable=False),
        sa.Column("owner_principal_id", sa.String(64)),
        sa.Column("owner_confirmed_at", sa.String(40)),
        sa.Column("valid_from", sa.String(40), nullable=False),
        sa.Column("invalidated_at", sa.String(40)),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("registry_revision", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["reg_discovery_candidate.candidate_id"]
        ),
        sa.ForeignKeyConstraint(["claim_id"], ["reg_provider_identity_claim.claim_id"]),
        sa.ForeignKeyConstraint(["account_id"], ["reg_account.account_id"]),
        sa.CheckConstraint("record_version > 0", name="ck_reg_decision_version"),
        sa.CheckConstraint("registry_revision > 0", name="ck_reg_decision_revision"),
    )
    op.create_index(
        "ix_reg_decision_account_valid",
        "reg_identity_decision",
        ["account_id", "valid_from", "decision_id"],
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

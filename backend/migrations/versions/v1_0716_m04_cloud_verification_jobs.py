"""M04 durable owner-verification queue and fenced worker claims."""

# ruff: noqa: E501 -- exact migration metadata and CHECK SQL remain explicit.

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0716"
down_revision = "v1_0715"
branch_labels = None
depends_on = None
TABLES = ("collection_cloud_verification_job",)
METADATA = MappingProxyType(
    {
        "revision": "v1_0716",
        "parent_revision": "v1_0715",
        "owner": "M04",
        "plan_id": "PLAN-M04",
        "requirement_ids": (
            "FR-COL-003",
            "FR-COL-005",
            "FR-COL-007",
            "M6-A07",
            "M6-A09",
            "NFR-DATA-001",
        ),
        "schema_range": (
            "v1_0716",
            "v1_0716",
            "v1_0716",
            "v1_0716",
            "v1_0716",
        ),
        "tables": ("collection_cloud_verification_job",),
        "portability_notes": (
            "Owner verification is queued durably and an expired claim is reusable only before rate admission",
            "Ambiguous dispatch remains associated with the authoritative M04 admission and is never reclaimed as queued work",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "one bounded non-secret row per owner verification request",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m04_cloud_verification_job_schema",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": "preserve_failed_database_and_restore_verified_backup_or_forward_fix",
        "reviewer": "M04-M6-cloud-verification-job-review",
    }
)


def upgrade() -> None:
    op.create_table(
        "collection_cloud_verification_job",
        sa.Column("job_id", sa.String(64), primary_key=True),
        sa.Column("principal_id", sa.String(64), nullable=False),
        sa.Column("idempotency_digest", sa.String(64), nullable=False),
        sa.Column("schedule_id", sa.String(64), nullable=False),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("access_target_id", sa.String(64), nullable=False),
        sa.Column("binding_generation", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("requested_at", sa.String(40), nullable=False),
        sa.Column("not_before_at", sa.String(40), nullable=False),
        sa.Column("claim_owner_id", sa.String(64), nullable=True),
        sa.Column("claim_fencing_token", sa.Integer(), nullable=False),
        sa.Column("claimed_at", sa.String(40), nullable=True),
        sa.Column("claim_expires_at", sa.String(40), nullable=True),
        sa.Column("admission_id", sa.String(64), nullable=True),
        sa.Column("run_id", sa.String(64), nullable=True),
        sa.Column("dispatch_certainty", sa.String(24), nullable=True),
        sa.Column("terminal_at", sa.String(40), nullable=True),
        sa.Column("outcome", sa.String(24), nullable=True),
        sa.Column("reason_code", sa.String(128), nullable=True),
        sa.Column("retry_after_seconds", sa.Integer(), nullable=True),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["schedule_id"], ["collection_schedule.schedule_id"]),
        sa.ForeignKeyConstraint(
            ["admission_id"],
            ["collection_ollama_cloud_admission.admission_id"],
        ),
        sa.ForeignKeyConstraint(["run_id"], ["collection_run.run_id"]),
        sa.CheckConstraint(
            "length(job_id)=37 AND substr(job_id,1,5)='amvj_' "
            "AND substr(job_id,6) NOT GLOB '*[^a-f0-9]*'",
            name="ck_collection_cloud_verification_job_id",
        ),
        sa.CheckConstraint(
            "length(access_target_id)=37 AND substr(access_target_id,1,5)='amat_' "
            "AND substr(access_target_id,6) NOT GLOB '*[^a-f0-9]*'",
            name="ck_collection_cloud_verification_target_id",
        ),
        sa.CheckConstraint(
            "length(idempotency_digest)=64 "
            "AND idempotency_digest NOT GLOB '*[^a-f0-9]*'",
            name="ck_collection_cloud_verification_idempotency",
        ),
        sa.CheckConstraint(
            "binding_generation>0 AND claim_fencing_token>=0 AND record_version>0",
            name="ck_collection_cloud_verification_versions",
        ),
        sa.CheckConstraint(
            "requested_at<=not_before_at "
            "AND ((claimed_at IS NULL AND claim_expires_at IS NULL) OR "
            "(claimed_at IS NOT NULL AND claim_expires_at IS NOT NULL "
            "AND claimed_at<claim_expires_at)) "
            "AND (terminal_at IS NULL OR terminal_at>=requested_at)",
            name="ck_collection_cloud_verification_times",
        ),
        sa.CheckConstraint(
            "state IN ('queued','claimed','admitted','terminal')",
            name="ck_collection_cloud_verification_state",
        ),
        sa.CheckConstraint(
            "dispatch_certainty IS NULL OR dispatch_certainty IN "
            "('not_started','may_have_started','response_received')",
            name="ck_collection_cloud_verification_certainty",
        ),
        sa.CheckConstraint(
            "outcome IS NULL OR outcome IN ('succeeded','rate_limited','failed')",
            name="ck_collection_cloud_verification_outcome",
        ),
        sa.CheckConstraint(
            "retry_after_seconds IS NULL OR "
            "(outcome='rate_limited' AND retry_after_seconds>=0)",
            name="ck_collection_cloud_verification_retry",
        ),
        sa.CheckConstraint(
            "(state='queued' AND claim_owner_id IS NULL AND claimed_at IS NULL "
            "AND claim_expires_at IS NULL AND admission_id IS NULL AND run_id IS NULL "
            "AND dispatch_certainty IS NULL AND terminal_at IS NULL "
            "AND outcome IS NULL AND reason_code IS NULL "
            "AND retry_after_seconds IS NULL) OR "
            "(state='claimed' AND claim_owner_id IS NOT NULL AND claimed_at IS NOT NULL "
            "AND claim_expires_at IS NOT NULL AND admission_id IS NULL AND run_id IS NULL "
            "AND claim_fencing_token>0 AND dispatch_certainty IS NULL "
            "AND terminal_at IS NULL AND outcome IS NULL AND reason_code IS NULL "
            "AND retry_after_seconds IS NULL) OR "
            "(state='admitted' AND claim_owner_id IS NOT NULL AND claimed_at IS NOT NULL "
            "AND claim_expires_at IS NOT NULL AND admission_id IS NOT NULL "
            "AND claim_fencing_token>0 AND dispatch_certainty IS NOT NULL "
            "AND terminal_at IS NULL AND outcome IS NULL "
            "AND retry_after_seconds IS NULL) OR "
            "(state='terminal' AND terminal_at IS NOT NULL "
            "AND reason_code IS NOT NULL AND dispatch_certainty IS NOT NULL "
            "AND dispatch_certainty IN "
            "('not_started','response_received') "
            "AND ((dispatch_certainty='not_started' AND outcome IS NULL) OR "
            "(dispatch_certainty='response_received' AND outcome IS NOT NULL)))",
            name="ck_collection_cloud_verification_shape",
        ),
    )
    op.create_index(
        "uq_collection_cloud_verification_idempotency",
        "collection_cloud_verification_job",
        ["principal_id", "idempotency_digest"],
        unique=True,
    )
    op.create_index(
        "uq_collection_cloud_verification_admission",
        "collection_cloud_verification_job",
        ["admission_id"],
        unique=True,
        sqlite_where=sa.text("admission_id IS NOT NULL"),
    )
    op.create_index(
        "uq_collection_cloud_verification_run",
        "collection_cloud_verification_job",
        ["run_id"],
        unique=True,
        sqlite_where=sa.text("run_id IS NOT NULL"),
    )
    op.create_index(
        "uq_collection_cloud_verification_active_binding",
        "collection_cloud_verification_job",
        ["account_id", "binding_generation"],
        unique=True,
        sqlite_where=sa.text("state IN ('queued','claimed','admitted')"),
    )
    op.create_index(
        "ix_collection_cloud_verification_claim",
        "collection_cloud_verification_job",
        ["state", "not_before_at", "requested_at", "job_id"],
    )
    op.create_index(
        "ix_collection_cloud_verification_account",
        "collection_cloud_verification_job",
        ["account_id", "binding_generation", "requested_at", "job_id"],
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

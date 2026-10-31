"""M01 V1 credential metadata; fresh-only initialization after v1_0000.

Owner: M01. Seven IAM tables only. Existing-file upgrades require the separately
approved backup/quiescence/recovery workflow; this revision is never run by
normal service startup. No administrator or credential row is seeded. There is
no safe destructive downgrade of credential/audit history.
"""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0100"
down_revision = "v1_0000"
branch_labels = None
depends_on = None

METADATA = MappingProxyType(
    {
        "revision": "v1_0100",
        "parent_revision": "v1_0000",
        "owner": "M01",
        "plan_id": "PLAN-M01",
        "requirement_ids": (
            "FR-IAM-001",
            "FR-IAM-002",
            "FR-IAM-005",
            "NFR-DATA-001",
            "NFR-SEC-001",
        ),
        "schema_range": (
            "v1_0100",
            "v1_0100",
            "v1_0100",
            "v1_0100",
            "v1_0100",
        ),
        "tables": (
            "iam_administrator",
            "iam_browser_session",
            "iam_api_token",
            "iam_api_token_scope",
            "iam_login_throttle",
            "iam_idempotency_record",
            "iam_security_audit_event",
        ),
        "portability_notes": (
            "UTC RFC3339 text, portable constraints and within-M01 foreign keys",
        ),
        "lock_policy": "exclusive_initialization_and_begin_immediate",
        "downtime_policy": "offline_absent_file_initialization_only",
        "expected_data_volume": "zero_business_rows",
        "backup_prerequisite": "none_empty_bootstrap",
        "validation_ids": (
            "single_head",
            "seven_iam_tables",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": "preserve_failed_database_no_automatic_retry_or_downgrade",
        "reviewer": "M01-PLAN-DB-security-review",
    }
)


def upgrade() -> None:
    op.create_table(
        "iam_administrator",
        sa.Column("singleton_key", sa.Integer(), primary_key=True),
        sa.Column("administrator_id", sa.String(64), nullable=False, unique=True),
        sa.Column("password_phc", sa.String(512), nullable=False),
        sa.Column("hash_policy_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("password_changed_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.CheckConstraint("singleton_key = 1", name="ck_iam_admin_singleton"),
        sa.CheckConstraint("record_version > 0", name="ck_iam_admin_version"),
    )
    op.create_table(
        "iam_browser_session",
        sa.Column("session_id", sa.String(64), primary_key=True),
        sa.Column("administrator_id", sa.String(64), nullable=False),
        sa.Column("credential_selector", sa.String(64), nullable=False, unique=True),
        sa.Column("credential_digest", sa.String(64), unique=True),
        sa.Column("csrf_digest", sa.String(64)),
        sa.Column("issued_at", sa.String(40), nullable=False),
        sa.Column("last_activity_at", sa.String(40), nullable=False),
        sa.Column("idle_expires_at", sa.String(40), nullable=False),
        sa.Column("absolute_expires_at", sa.String(40), nullable=False),
        sa.Column("revoked_at", sa.String(40)),
        sa.Column("revocation_reason", sa.String(64)),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["administrator_id"], ["iam_administrator.administrator_id"]
        ),
        sa.CheckConstraint("record_version > 0", name="ck_iam_session_version"),
        sa.CheckConstraint(
            "revoked_at IS NULL OR credential_digest IS NULL",
            name="ck_iam_session_revoked_digest",
        ),
    )
    op.create_index(
        "ix_iam_session_admin_issued",
        "iam_browser_session",
        ["administrator_id", "issued_at"],
    )
    op.create_index("ix_iam_session_idle", "iam_browser_session", ["idle_expires_at"])
    op.create_index(
        "ix_iam_session_absolute", "iam_browser_session", ["absolute_expires_at"]
    )
    op.create_table(
        "iam_api_token",
        sa.Column("api_token_id", sa.String(64), primary_key=True),
        sa.Column("administrator_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("public_selector", sa.String(64), nullable=False, unique=True),
        sa.Column("safe_prefix", sa.String(32), nullable=False),
        sa.Column("verification_digest", sa.String(64), unique=True),
        sa.Column("issued_at", sa.String(40), nullable=False),
        sa.Column("expires_at", sa.String(40), nullable=False),
        sa.Column("last_used_at", sa.String(40)),
        sa.Column("revoked_at", sa.String(40)),
        sa.Column("revocation_reason", sa.String(64)),
        sa.Column("rotated_from_token_id", sa.String(64)),
        sa.Column("replacement_token_id", sa.String(64)),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["administrator_id"], ["iam_administrator.administrator_id"]
        ),
        sa.ForeignKeyConstraint(
            ["rotated_from_token_id"], ["iam_api_token.api_token_id"]
        ),
        sa.ForeignKeyConstraint(
            ["replacement_token_id"], ["iam_api_token.api_token_id"]
        ),
        sa.CheckConstraint("length(name) > 0", name="ck_iam_token_name"),
        sa.CheckConstraint("record_version > 0", name="ck_iam_token_version"),
        sa.CheckConstraint(
            "revoked_at IS NULL OR verification_digest IS NULL",
            name="ck_iam_token_revoked_digest",
        ),
    )
    op.create_index(
        "ix_iam_token_admin_issued", "iam_api_token", ["administrator_id", "issued_at"]
    )
    op.create_index("ix_iam_token_expiry", "iam_api_token", ["expires_at"])
    op.create_index("ix_iam_token_revoked", "iam_api_token", ["revoked_at"])
    op.create_table(
        "iam_api_token_scope",
        sa.Column("api_token_id", sa.String(64), primary_key=True),
        sa.Column("scope_key", sa.String(64), primary_key=True),
        sa.ForeignKeyConstraint(["api_token_id"], ["iam_api_token.api_token_id"]),
    )
    op.create_table(
        "iam_login_throttle",
        sa.Column("bucket_id", sa.String(64), primary_key=True),
        sa.Column("window_started_at", sa.String(40), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("consecutive_lock_count", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.String(40)),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.CheckConstraint("failure_count >= 0", name="ck_iam_throttle_failure"),
        sa.CheckConstraint("consecutive_lock_count >= 0", name="ck_iam_throttle_locks"),
        sa.CheckConstraint("record_version > 0", name="ck_iam_throttle_version"),
    )
    op.create_table(
        "iam_idempotency_record",
        sa.Column("idempotency_id", sa.String(64), primary_key=True),
        sa.Column("principal_id", sa.String(64), nullable=False),
        sa.Column("operation_key", sa.String(64), nullable=False),
        sa.Column("idempotency_key_digest", sa.String(64), nullable=False),
        sa.Column("request_fingerprint", sa.String(64)),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("resource_id", sa.String(64)),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("expires_at", sa.String(40), nullable=False),
        sa.UniqueConstraint(
            "principal_id",
            "operation_key",
            "idempotency_key_digest",
            name="uq_iam_idempotency_operation_key",
        ),
    )
    op.create_index(
        "ix_iam_idempotency_expiry", "iam_idempotency_record", ["expires_at"]
    )
    op.create_table(
        "iam_security_audit_event",
        sa.Column("event_id", sa.String(64), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("occurred_at", sa.String(40), nullable=False),
        sa.Column("recorded_at", sa.String(40), nullable=False),
        sa.Column("actor_principal_id", sa.String(64)),
        sa.Column("authentication_method", sa.String(32)),
        sa.Column("target_type", sa.String(32)),
        sa.Column("target_id", sa.String(64)),
        sa.Column("outcome_code", sa.String(64), nullable=False),
        sa.Column("reason_code", sa.String(64)),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("aggregate_count", sa.Integer()),
        sa.CheckConstraint("schema_version = 1", name="ck_iam_audit_schema"),
        sa.CheckConstraint(
            "aggregate_count IS NULL OR aggregate_count >= 0",
            name="ck_iam_audit_count",
        ),
    )
    op.create_index(
        "ix_iam_audit_occurred", "iam_security_audit_event", ["occurred_at", "event_id"]
    )
    op.create_index(
        "ix_iam_audit_actor",
        "iam_security_audit_event",
        ["actor_principal_id", "occurred_at"],
    )
    op.create_index(
        "ix_iam_audit_type", "iam_security_audit_event", ["event_type", "occurred_at"]
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

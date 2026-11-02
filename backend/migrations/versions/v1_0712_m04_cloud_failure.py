"""M04 retain a sanitized cloud failure code for crash recovery."""

# ruff: noqa: E501 -- immutable metadata remains explicit.

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0712"
down_revision = "v1_0711"
branch_labels = None
depends_on = None
TABLES = ("collection_cloud_attempt_journal", "collection_cloud_no_response_terminal")
METADATA = MappingProxyType(
    {
        "revision": "v1_0712",
        "parent_revision": "v1_0711",
        "owner": "M04",
        "plan_id": "PLAN-M04",
        "requirement_ids": ("FR-COL-003", "FR-COL-007", "M6-A09"),
        "schema_range": ("v1_0712", "v1_0712", "v1_0712", "v1_0712", "v1_0712"),
        "tables": (
            "collection_cloud_attempt_journal",
            "collection_cloud_no_response_terminal",
        ),
        "portability_notes": (
            "Nullable safe failure code preserves interrupted-run classification",
            "V2 no-response overlay is authoritative over its legacy admission shadow",
            "Credential-update lock contention remains a retryable no-request terminal",
        ),
        "lock_policy": "exclusive_migration",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "one_nullable_column_per_attempt",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m04_cloud_failure_schema",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": "preserve_failed_database_and_restore_verified_backup_or_forward_fix",
        "reviewer": "M04-M6-cloud-journal-review",
    }
)


def upgrade() -> None:
    op.add_column(
        "collection_cloud_attempt_journal",
        sa.Column(
            "failure_code",
            sa.String(128),
            sa.CheckConstraint(
                "COALESCE(failure_code IS NULL OR (phase='outcome' AND outcome IN ('failed','rate_limited') "
                "AND failure_code IN ('authorization_unavailable','unauthorized','access_denied','rate_limited',"
                "'provider_unavailable','unexpected_response','invalid_provider_data','deadline_exceeded',"
                "'internal_adapter_error','source_not_admitted') AND "
                "((outcome='rate_limited' AND failure_code='rate_limited') OR "
                "(outcome='failed' AND failure_code<>'rate_limited'))),0)=1",
                name="ck_cloud_journal_failure_code",
            ),
            nullable=True,
        ),
    )
    op.execute(
        "UPDATE collection_cloud_attempt_journal SET failure_code='rate_limited' WHERE phase='outcome' AND outcome='rate_limited'"
    )
    op.create_index(
        "uq_collection_cloud_attempt_run",
        "collection_cloud_attempt_journal",
        ["run_id"],
        unique=True,
    )
    op.create_table(
        "collection_cloud_no_response_terminal",
        sa.Column("admission_id", sa.String(64), primary_key=True),
        sa.Column("terminal_at", sa.String(40), nullable=False),
        sa.Column("gate_record_version", sa.Integer(), nullable=False),
        sa.Column("next_allowed_at", sa.String(40), nullable=False),
        sa.Column("reason_code", sa.String(64), nullable=False),
        sa.Column("source_state", sa.String(64)),
        sa.Column("dispatch_certainty", sa.String(32), nullable=False),
        sa.ForeignKeyConstraint(
            ["admission_id"], ["collection_ollama_cloud_admission.admission_id"]
        ),
        sa.CheckConstraint(
            "dispatch_certainty = 'not_started'", name="ck_cloud_no_response_certainty"
        ),
        sa.CheckConstraint(
            "source_state IS NULL OR source_state IN ('authorization_unavailable','deadline_exceeded',"
            "'provider_unavailable','internal_adapter_error','source_not_admitted')",
            name="ck_cloud_no_response_source_state",
        ),
        sa.CheckConstraint(
            "reason_code IN ('pre_dispatch_failed','source_not_started','store_unavailable',"
            "'credential_update_in_progress')",
            name="ck_cloud_no_response_reason",
        ),
        sa.CheckConstraint(
            "next_allowed_at >= terminal_at", name="ck_cloud_no_response_terminal_order"
        ),
        sa.CheckConstraint(
            "gate_record_version > 0", name="ck_cloud_no_response_gate_version"
        ),
        sa.CheckConstraint(
            "COALESCE((reason_code='pre_dispatch_failed' AND source_state IS NULL) OR "
            "(reason_code IN ('store_unavailable','credential_update_in_progress') "
            "AND source_state='authorization_unavailable') OR "
            "(reason_code='source_not_started' AND source_state IN ('deadline_exceeded',"
            "'provider_unavailable','internal_adapter_error','source_not_admitted')),0)=1",
            name="ck_cloud_no_response_reason_state",
        ),
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

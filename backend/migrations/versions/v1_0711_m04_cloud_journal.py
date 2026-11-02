"""M04 source-lane registration and non-secret cloud outcome journal."""

# ruff: noqa: E501 -- immutable schema predicates remain explicit.

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0711"
down_revision = "v1_0710"
branch_labels = None
depends_on = None
TABLES = ("collection_cloud_schedule_lane", "collection_cloud_attempt_journal")
METADATA = MappingProxyType(
    {
        "revision": "v1_0711",
        "parent_revision": "v1_0710",
        "owner": "M04",
        "plan_id": "PLAN-M04",
        "requirement_ids": ("FR-COL-003", "FR-COL-007", "M6-A09"),
        "schema_range": ("v1_0711", "v1_0711", "v1_0711", "v1_0711", "v1_0711"),
        "tables": (
            "collection_cloud_schedule_lane",
            "collection_cloud_attempt_journal",
        ),
        "portability_notes": (
            "Cloud source lane and sanitized attempt outcome are durable",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "one_row_per_schedule_and_one_per_attempt",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m04_cloud_journal_schema",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": "preserve_failed_database_and_restore_verified_backup_or_forward_fix",
        "reviewer": "M04-M6-cloud-journal-review",
    }
)


def upgrade() -> None:
    op.create_table(
        "collection_cloud_schedule_lane",
        sa.Column("schedule_id", sa.String(64), primary_key=True),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.ForeignKeyConstraint(["schedule_id"], ["collection_schedule.schedule_id"]),
    )
    op.create_table(
        "collection_cloud_attempt_journal",
        sa.Column("admission_id", sa.String(64), primary_key=True),
        sa.Column("phase", sa.String(24), nullable=False),
        sa.Column("run_id", sa.String(64)),
        sa.Column("outcome", sa.String(32)),
        sa.Column("response_received_at", sa.String(40)),
        sa.Column("retry_after_seconds", sa.Integer()),
        sa.Column("completion_jitter_seconds", sa.Integer()),
        sa.ForeignKeyConstraint(
            ["admission_id"], ["collection_ollama_cloud_admission.admission_id"]
        ),
        sa.ForeignKeyConstraint(["run_id"], ["collection_run.run_id"]),
        sa.CheckConstraint(
            "phase IN ('reserved','dispatched','outcome','legacy_unresolved')",
            name="ck_cloud_journal_phase",
        ),
        sa.CheckConstraint(
            "phase <> 'dispatched' OR run_id IS NOT NULL",
            name="ck_cloud_journal_dispatch_run",
        ),
        sa.CheckConstraint(
            "outcome IS NULL OR outcome IN ('succeeded','rate_limited','failed')",
            name="ck_cloud_journal_outcome",
        ),
        sa.CheckConstraint(
            "completion_jitter_seconds IS NULL OR completion_jitter_seconds BETWEEN 0 AND 10",
            name="ck_cloud_journal_jitter",
        ),
        sa.CheckConstraint(
            "retry_after_seconds IS NULL OR (retry_after_seconds >= 0 AND outcome='rate_limited')",
            name="ck_cloud_journal_retry",
        ),
        sa.CheckConstraint(
            "(phase='outcome' AND outcome IS NOT NULL AND response_received_at IS NOT NULL AND completion_jitter_seconds IS NOT NULL) OR (phase IN ('reserved','dispatched','legacy_unresolved') AND outcome IS NULL AND response_received_at IS NULL AND retry_after_seconds IS NULL AND completion_jitter_seconds IS NULL)",
            name="ck_cloud_journal_fields",
        ),
    )
    # Completed attempts can be replayed exactly. Older active/expired
    # attempts have unknown dispatch status and must not be guessed safe.
    op.execute(
        "INSERT INTO collection_cloud_attempt_journal "
        "(admission_id,phase,outcome,response_received_at,retry_after_seconds,completion_jitter_seconds) "
        "SELECT admission_id,'outcome',outcome,response_received_at,retry_after_seconds,completion_jitter_seconds "
        "FROM collection_ollama_cloud_admission WHERE state='completed'"
    )
    op.execute(
        "INSERT INTO collection_cloud_attempt_journal (admission_id,phase) "
        "SELECT admission_id,'legacy_unresolved' FROM collection_ollama_cloud_admission "
        "WHERE state IN ('active','expired')"
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

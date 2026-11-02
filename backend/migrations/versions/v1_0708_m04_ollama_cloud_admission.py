"""M04 durable global Ollama cloud admission and fair cursor."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0708"
down_revision = "v1_0707"
branch_labels = None
depends_on = None
TABLES = (
    "collection_ollama_cloud_gate",
    "collection_ollama_cloud_admission",
)
METADATA = MappingProxyType(
    {
        "revision": "v1_0708",
        "parent_revision": "v1_0707",
        "owner": "M04",
        "plan_id": "PLAN-M04",
        "requirement_ids": (
            "FR-COL-003",
            "FR-COL-005",
            "FR-COL-006",
            "FR-COL-008",
            "M6-A07",
            "M6-A09",
            "NFR-DATA-001",
        ),
        "schema_range": (
            "v1_0708",
            "v1_0708",
            "v1_0708",
            "v1_0708",
            "v1_0708",
        ),
        "tables": (
            "collection_ollama_cloud_gate",
            "collection_ollama_cloud_admission",
        ),
        "portability_notes": (
            "One provider-global row serializes request starts per deployed "
            "SQLite instance",
            "Create-once admission rows retain fencing and fair scheduling evidence",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "one_gate_row;one_admission_row_per_attempt",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m04_ollama_cloud_global_admission",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": (
            "preserve_failed_database_and_restore_verified_backup_or_forward_fix"
        ),
        "reviewer": "M04-M6-cloud-security-review",
    }
)


def upgrade() -> None:
    op.create_table(
        "collection_ollama_cloud_gate",
        sa.Column("gate_id", sa.String(64), primary_key=True),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("capability_id", sa.String(128), nullable=False),
        sa.Column("next_allowed_at", sa.String(40), nullable=False),
        sa.Column("fair_cursor_schedule_id", sa.String(64)),
        sa.Column("active_admission_id", sa.String(64)),
        sa.Column("consecutive_rate_limits", sa.Integer(), nullable=False),
        sa.Column("fencing_token", sa.Integer(), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.ForeignKeyConstraint(
            ["fair_cursor_schedule_id"], ["collection_schedule.schedule_id"]
        ),
        sa.UniqueConstraint(
            "provider_key",
            "capability_id",
            name="uq_collection_ollama_cloud_gate_scope",
        ),
        sa.CheckConstraint(
            "provider_key='ollama' AND capability_id='subscription.quota'",
            name="ck_collection_ollama_cloud_gate_scope",
        ),
        sa.CheckConstraint(
            "consecutive_rate_limits BETWEEN 0 AND 100 AND fencing_token >= 0 "
            "AND record_version > 0",
            name="ck_collection_ollama_cloud_gate_versions",
        ),
    )
    op.create_table(
        "collection_ollama_cloud_admission",
        sa.Column("admission_id", sa.String(64), primary_key=True),
        sa.Column("gate_id", sa.String(64), nullable=False),
        sa.Column("scheduler_instance_id", sa.String(64), nullable=False),
        sa.Column("schedule_id", sa.String(64), nullable=False),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("fencing_token", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("started_at", sa.String(40), nullable=False),
        sa.Column("lease_expires_at", sa.String(40), nullable=False),
        sa.Column("admission_jitter_seconds", sa.Integer(), nullable=False),
        sa.Column("response_received_at", sa.String(40)),
        sa.Column("outcome", sa.String(16)),
        sa.Column("retry_after_seconds", sa.Integer()),
        sa.Column("completion_jitter_seconds", sa.Integer()),
        sa.Column("next_allowed_at", sa.String(40), nullable=False),
        sa.ForeignKeyConstraint(["gate_id"], ["collection_ollama_cloud_gate.gate_id"]),
        sa.ForeignKeyConstraint(["schedule_id"], ["collection_schedule.schedule_id"]),
        sa.UniqueConstraint(
            "gate_id", "fencing_token", name="uq_collection_ollama_cloud_fence"
        ),
        sa.CheckConstraint(
            "fencing_token > 0 AND admission_jitter_seconds BETWEEN 0 AND 10",
            name="ck_collection_ollama_cloud_admission_fence",
        ),
        sa.CheckConstraint(
            "state IN ('active','completed','expired')",
            name="ck_collection_ollama_cloud_admission_state",
        ),
        sa.CheckConstraint(
            "COALESCE(CASE WHEN state='active' THEN response_received_at IS NULL "
            "AND outcome IS NULL AND retry_after_seconds IS NULL "
            "AND completion_jitter_seconds IS NULL ELSE "
            "response_received_at IS NOT NULL "
            "AND outcome IN ('succeeded','rate_limited','failed','expired') "
            "AND completion_jitter_seconds IS NOT NULL "
            "AND completion_jitter_seconds BETWEEN 0 AND 10 "
            "AND ((outcome='rate_limited' AND (retry_after_seconds IS NULL "
            "OR retry_after_seconds >= 0)) OR "
            "(outcome<>'rate_limited' AND retry_after_seconds IS NULL)) END,0)=1",
            name="ck_collection_ollama_cloud_admission_terminal",
        ),
    )
    op.create_index(
        "ix_collection_ollama_cloud_admission_state",
        "collection_ollama_cloud_admission",
        ["gate_id", "state", "lease_expires_at", "admission_id"],
    )
    op.create_index(
        "ix_collection_ollama_cloud_admission_schedule",
        "collection_ollama_cloud_admission",
        ["schedule_id", "started_at", "admission_id"],
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

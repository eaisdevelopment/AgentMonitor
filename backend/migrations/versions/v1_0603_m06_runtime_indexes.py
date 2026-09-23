"""M06 bounded current/history/receipt/outbox query indexes."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0603"
down_revision = "v1_0602"
branch_labels = None
depends_on = None

INDEXES = (
    "ix_runtime_process_current",
    "ix_runtime_process_provider",
    "ix_runtime_process_history",
    "ix_runtime_session_current",
    "ix_runtime_session_account",
    "ix_runtime_session_history",
    "ix_runtime_metric_history",
    "ix_runtime_metric_process_history",
    "ix_runtime_link_session_current",
    "uq_runtime_link_one_current_pair",
    "ix_runtime_relationship_child_current",
    "uq_runtime_relationship_one_current_parent",
    "ix_runtime_evidence_session_time",
    "ix_runtime_decision_session_current",
    "uq_runtime_decision_one_current",
    "ix_runtime_policy_scope_current",
    "uq_runtime_policy_one_current",
    "ix_runtime_transition_session",
    "ix_runtime_receipt_run",
    "ix_runtime_outbox_available",
)

METADATA = MappingProxyType(
    {
        "revision": "v1_0603",
        "parent_revision": "v1_0602",
        "owner": "M06",
        "plan_id": "PLAN-M06",
        "requirement_ids": (
            "FR-HIST-001",
            "FR-HIST-002",
            "NFR-DATA-001",
            "NFR-PERF-001",
        ),
        "schema_range": (
            "v1_0603",
            "v1_0603",
            "v1_0603",
            "v1_0603",
            "v1_0603",
        ),
        "tables": (),
        "portability_notes": (
            "SQLite partial indexes remain persistence-adapter details",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": (
            "initial empty schema; later index build is measured before release"
        ),
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m06_indexes",
            "query_plan",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": (
            "preserve_failed_database_and_restore_verified_backup_or_forward_fix"
        ),
        "reviewer": "M06-PLAN-DB-performance-review",
    }
)


def upgrade() -> None:
    op.create_index(
        "ix_runtime_process_current",
        "runtime_process_instance",
        ["presence_state", "last_observed_at", "process_id"],
    )
    op.create_index(
        "ix_runtime_process_provider",
        "runtime_process_instance",
        ["provider_key", "last_observed_at", "process_id"],
    )
    op.create_index(
        "ix_runtime_process_history",
        "runtime_process_snapshot",
        ["process_id", "observed_at", "snapshot_id"],
    )
    op.create_index(
        "ix_runtime_session_current",
        "runtime_session",
        ["last_observed_at", "session_id"],
    )
    op.create_index(
        "ix_runtime_session_account",
        "runtime_session",
        ["account_id", "last_observed_at", "session_id"],
    )
    op.create_index(
        "ix_runtime_session_history",
        "runtime_session_observation",
        ["session_id", "observed_at", "observation_id"],
    )
    op.create_index(
        "ix_runtime_metric_history",
        "runtime_metric_observation",
        ["session_id", "metric_kind", "observed_at", "metric_id"],
    )
    op.create_index(
        "ix_runtime_metric_process_history",
        "runtime_metric_observation",
        ["process_id", "metric_kind", "observed_at", "metric_id"],
    )
    op.create_index(
        "ix_runtime_link_session_current",
        "runtime_session_process_link",
        ["session_id", "is_current", "link_id"],
    )
    op.create_index(
        "uq_runtime_link_one_current_pair",
        "runtime_session_process_link",
        ["session_id", "process_id"],
        unique=True,
        sqlite_where=sa.text("is_current=1 AND conflict_state='clear'"),
    )
    op.create_index(
        "ix_runtime_relationship_child_current",
        "runtime_session_relationship",
        ["child_session_id", "is_current", "relationship_id"],
    )
    op.create_index(
        "uq_runtime_relationship_one_current_parent",
        "runtime_session_relationship",
        ["child_session_id"],
        unique=True,
        sqlite_where=sa.text("is_current=1 AND conflict_state='clear'"),
    )
    op.create_index(
        "ix_runtime_evidence_session_time",
        "runtime_correlation_evidence",
        ["session_id", "observed_at", "evidence_id"],
    )
    op.create_index(
        "ix_runtime_decision_session_current",
        "runtime_session_correlation_decision",
        ["session_id", "is_current", "decision_version"],
    )
    op.create_index(
        "uq_runtime_decision_one_current",
        "runtime_session_correlation_decision",
        ["session_id"],
        unique=True,
        sqlite_where=sa.text("is_current=1"),
    )
    op.create_index(
        "ix_runtime_policy_scope_current",
        "runtime_stall_policy",
        ["scope_kind", "scope_id", "is_current", "policy_version"],
    )
    op.create_index(
        "uq_runtime_policy_one_current",
        "runtime_stall_policy",
        ["scope_kind", "scope_id"],
        unique=True,
        sqlite_where=sa.text("is_current=1"),
    )
    op.create_index(
        "ix_runtime_transition_session",
        "runtime_state_transition",
        ["session_id", "stream_sequence"],
    )
    op.create_index(
        "ix_runtime_receipt_run",
        "runtime_ingest_receipt",
        ["collection_run_id", "capability_id"],
    )
    op.create_index(
        "ix_runtime_outbox_available",
        "runtime_event_outbox",
        ["delivery_state", "available_at", "producer_sequence"],
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

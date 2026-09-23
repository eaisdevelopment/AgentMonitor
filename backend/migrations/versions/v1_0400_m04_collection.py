"""M04 durable collection admission, fencing, runs, and owned outbox."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0400"
down_revision = "v1_0300"
branch_labels = None
depends_on = None

TABLES = (
    "collection_schedule",
    "collection_request",
    "collection_lease",
    "collection_run",
    "collection_run_warning",
    "collection_run_observation_ref",
    "collection_budget_reservation",
    "collection_scheduler_instance",
    "collection_event_outbox",
    "collection_event_delivery",
)

METADATA = MappingProxyType(
    {
        "revision": "v1_0400",
        "parent_revision": "v1_0300",
        "owner": "M04",
        "plan_id": "PLAN-M04",
        "requirement_ids": (
            "FR-COL-001",
            "FR-COL-002",
            "FR-COL-003",
            "FR-COL-004",
            "FR-COL-005",
            "FR-COL-006",
            "FR-COL-007",
            "FR-COL-008",
            "NFR-DATA-001",
        ),
        "schema_range": (
            "v1_0400",
            "v1_0400",
            "v1_0400",
            "v1_0400",
            "v1_0400",
        ),
        "tables": (
            "collection_schedule",
            "collection_request",
            "collection_lease",
            "collection_run",
            "collection_run_warning",
            "collection_run_observation_ref",
            "collection_budget_reservation",
            "collection_scheduler_instance",
            "collection_event_outbox",
            "collection_event_delivery",
        ),
        "portability_notes": (
            "Scalar IDs only; fencing and partial indexes are adapter-local",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_collection_rows_on_initial_install",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m04_collection_tables",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": (
            "preserve_failed_database_and_restore_verified_backup_or_forward_fix"
        ),
        "reviewer": "M04-PLAN-DB-security-review",
    }
)


def upgrade() -> None:
    op.create_table(
        "collection_schedule",
        sa.Column("schedule_id", sa.String(64), primary_key=True),
        sa.Column("target_key_digest", sa.String(64), nullable=False, unique=True),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("installation_id", sa.String(64), nullable=False),
        sa.Column("account_id", sa.String(64)),
        sa.Column("profile_id", sa.String(64)),
        sa.Column("resource_id", sa.String(64)),
        sa.Column("capability_id", sa.String(128), nullable=False),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("activity_class", sa.String(16), nullable=False),
        sa.Column("base_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("effective_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("target_generation", sa.Integer(), nullable=False),
        sa.Column("next_due_at", sa.String(40), nullable=False),
        sa.Column("not_before_at", sa.String(40)),
        sa.Column("backoff_kind", sa.String(40)),
        sa.Column("backoff_generation", sa.Integer(), nullable=False),
        sa.Column("consecutive_failure_count", sa.Integer(), nullable=False),
        sa.Column("last_attempted_run_id", sa.String(64)),
        sa.Column("last_successful_run_id", sa.String(64)),
        sa.Column("last_terminal_outcome_code", sa.String(128)),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.CheckConstraint(
            "state IN ('enabled','paused_monitoring_disabled','blocked_authentication',"
            "'blocked_user_action','blocked_compatibility',"
            "'blocked_unknown_constraints','unsupported','retired')",
            name="ck_collection_schedule_state",
        ),
        sa.CheckConstraint(
            "activity_class IN ('active','idle','unknown')",
            name="ck_collection_schedule_activity",
        ),
        sa.CheckConstraint(
            "base_interval_seconds > 0 AND effective_interval_seconds > 0",
            name="ck_collection_schedule_intervals",
        ),
        sa.CheckConstraint(
            "target_generation > 0 AND record_version > 0",
            name="ck_collection_schedule_versions",
        ),
        sa.CheckConstraint(
            "backoff_generation >= 0 AND consecutive_failure_count >= 0",
            name="ck_collection_schedule_failures",
        ),
    )
    op.create_index(
        "ix_collection_schedule_due",
        "collection_schedule",
        ["state", "next_due_at", "schedule_id"],
    )
    op.create_index(
        "ix_collection_schedule_target",
        "collection_schedule",
        ["provider_key", "account_id", "capability_id", "schedule_id"],
    )

    op.create_table(
        "collection_request",
        sa.Column("request_id", sa.String(64), primary_key=True),
        sa.Column("schedule_id", sa.String(64), nullable=False),
        sa.Column("trigger_kind", sa.String(40), nullable=False),
        sa.Column("operation_family", sa.String(64), nullable=False),
        sa.Column("requested_capabilities_json", sa.String(2048), nullable=False),
        sa.Column("capability_set_version", sa.String(32), nullable=False),
        sa.Column("request_auth_method", sa.String(32), nullable=False),
        sa.Column("principal_id", sa.String(64)),
        sa.Column("producer_key", sa.String(64)),
        sa.Column("producer_event_id", sa.String(64)),
        sa.Column("idempotency_key_digest", sa.String(64)),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("requested_at", sa.String(40), nullable=False),
        sa.Column("expires_at", sa.String(40)),
        sa.Column("completed_at", sa.String(40)),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("linked_run_id", sa.String(64)),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("causation_id", sa.String(64)),
        sa.Column("safe_code", sa.String(128)),
        sa.ForeignKeyConstraint(
            ["schedule_id"], ["collection_schedule.schedule_id"]
        ),
        sa.UniqueConstraint(
            "principal_id",
            "operation_family",
            "idempotency_key_digest",
            name="uq_collection_request_manual_idempotency",
        ),
        sa.UniqueConstraint(
            "producer_key",
            "producer_event_id",
            name="uq_collection_request_event_idempotency",
        ),
        sa.CheckConstraint(
            "state IN ('accepted','coalesced','running','completed','expired',"
            "'blocked')",
            name="ck_collection_request_state",
        ),
    )
    op.create_index(
        "ix_collection_request_state_time",
        "collection_request",
        ["state", "requested_at", "request_id"],
    )

    op.create_table(
        "collection_lease",
        sa.Column("schedule_id", sa.String(64), primary_key=True),
        sa.Column("owner_instance_id", sa.String(64), nullable=False),
        sa.Column("fencing_token", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.String(64), nullable=False, unique=True),
        sa.Column("acquired_at", sa.String(40), nullable=False),
        sa.Column("heartbeat_at", sa.String(40), nullable=False),
        sa.Column("expires_at", sa.String(40), nullable=False),
        sa.Column("lease_policy_version", sa.String(32), nullable=False),
        sa.ForeignKeyConstraint(
            ["schedule_id"], ["collection_schedule.schedule_id"]
        ),
        sa.CheckConstraint("fencing_token > 0", name="ck_collection_lease_fence"),
    )
    op.create_index(
        "ix_collection_lease_expiry",
        "collection_lease",
        ["expires_at", "schedule_id"],
    )

    op.create_table(
        "collection_run",
        sa.Column("run_id", sa.String(64), primary_key=True),
        sa.Column("schedule_id", sa.String(64), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("installation_id", sa.String(64), nullable=False),
        sa.Column("account_id", sa.String(64)),
        sa.Column("profile_id", sa.String(64)),
        sa.Column("resource_id", sa.String(64)),
        sa.Column("capability_id", sa.String(128), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("adapter_version", sa.String(64), nullable=False),
        sa.Column("adapter_protocol_version", sa.String(32), nullable=False),
        sa.Column("manifest_fingerprint", sa.String(64), nullable=False),
        sa.Column("collection_policy_version", sa.String(32), nullable=False),
        sa.Column("registry_revision", sa.Integer(), nullable=False),
        sa.Column("provider_version", sa.String(128)),
        sa.Column("trigger_kind", sa.String(40), nullable=False),
        sa.Column("primary_request_id", sa.String(64), nullable=False),
        sa.Column("retry_chain_id", sa.String(64), nullable=False),
        sa.Column("attempt_ordinal", sa.Integer(), nullable=False),
        sa.Column("target_generation", sa.Integer(), nullable=False),
        sa.Column("fencing_token", sa.Integer(), nullable=False),
        sa.Column("budget_reservation_id", sa.String(64), nullable=False),
        sa.Column("payload_schema", sa.String(128), nullable=False),
        sa.Column("payload_digest", sa.String(64)),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("outcome_code", sa.String(128)),
        sa.Column("error_code", sa.String(128)),
        sa.Column("requested_at", sa.String(40), nullable=False),
        sa.Column("queued_at", sa.String(40), nullable=False),
        sa.Column("started_at", sa.String(40)),
        sa.Column("completed_at", sa.String(40)),
        sa.Column("deadline_at", sa.String(40), nullable=False),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("retry_disposition", sa.String(32)),
        sa.Column("retry_eligible", sa.Integer()),
        sa.Column("retry_after", sa.String(40)),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("causation_id", sa.String(64)),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["schedule_id"], ["collection_schedule.schedule_id"]
        ),
        sa.CheckConstraint(
            "state IN ('requested','queued','running','committing','succeeded',"
            "'partial','failed','blocked','cancelled','unsupported')",
            name="ck_collection_run_state",
        ),
        sa.CheckConstraint(
            "attempt_ordinal > 0 AND registry_revision > 0 AND "
            "target_generation > 0 AND fencing_token > 0 AND record_version > 0",
            name="ck_collection_run_versions",
        ),
        sa.CheckConstraint(
            "retry_eligible IS NULL OR retry_eligible IN (0,1)",
            name="ck_collection_run_retry_bool",
        ),
        sa.CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_collection_run_duration",
        ),
    )
    op.create_index(
        "ix_collection_run_schedule_time",
        "collection_run",
        ["schedule_id", "requested_at", "run_id"],
    )
    op.create_index(
        "ix_collection_run_state_time",
        "collection_run",
        ["state", "requested_at", "run_id"],
    )
    op.create_index(
        "uq_collection_run_active_schedule",
        "collection_run",
        ["schedule_id"],
        unique=True,
        sqlite_where=sa.text(
            "state IN ('requested','queued','running','committing')"
        ),
    )

    op.create_table(
        "collection_run_warning",
        sa.Column("run_id", sa.String(64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("warning_code", sa.String(128), nullable=False),
        sa.Column("affected_capability_id", sa.String(128), nullable=False),
        sa.Column("schema_version", sa.String(32), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["collection_run.run_id"]),
        sa.PrimaryKeyConstraint("run_id", "ordinal"),
        sa.CheckConstraint("ordinal >= 0", name="ck_collection_warning_ordinal"),
    )
    op.create_table(
        "collection_run_observation_ref",
        sa.Column("run_id", sa.String(64), nullable=False),
        sa.Column("consumer_key", sa.String(64), nullable=False),
        sa.Column("consumer_version", sa.String(32), nullable=False),
        sa.Column("observation_id", sa.String(64), nullable=False),
        sa.Column("receipt_version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["collection_run.run_id"]),
        sa.PrimaryKeyConstraint("run_id", "consumer_key", "observation_id"),
        sa.CheckConstraint("receipt_version > 0", name="ck_collection_ref_receipt"),
    )
    op.create_table(
        "collection_budget_reservation",
        sa.Column("reservation_id", sa.String(64), primary_key=True),
        sa.Column("run_id", sa.String(64), nullable=False),
        sa.Column("constraint_policy_id", sa.String(64), nullable=False),
        sa.Column("constraint_policy_version", sa.String(32), nullable=False),
        sa.Column("scope_key_digest", sa.String(64), nullable=False),
        sa.Column("dimension", sa.String(64), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("window_start", sa.String(40), nullable=False),
        sa.Column("window_end", sa.String(40), nullable=False),
        sa.Column("units", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["collection_run.run_id"]),
        sa.UniqueConstraint(
            "run_id",
            "constraint_policy_id",
            "dimension",
            name="uq_collection_budget_dimension",
        ),
        sa.CheckConstraint("units >= 0", name="ck_collection_budget_units"),
        sa.CheckConstraint(
            "state IN ('reserved','dispatched','released','expired_conservative')",
            name="ck_collection_budget_state",
        ),
    )
    op.create_index(
        "ix_collection_budget_scope_window",
        "collection_budget_reservation",
        ["scope_key_digest", "dimension", "window_end", "state"],
    )

    op.create_table(
        "collection_scheduler_instance",
        sa.Column("instance_id", sa.String(64), primary_key=True),
        sa.Column("service_version", sa.String(64), nullable=False),
        sa.Column("started_at", sa.String(40), nullable=False),
        sa.Column("heartbeat_at", sa.String(40), nullable=False),
        sa.Column("stopping_at", sa.String(40)),
        sa.Column("completed_at", sa.String(40)),
        sa.Column("lifecycle_state", sa.String(24), nullable=False),
        sa.Column("last_health_code", sa.String(128)),
        sa.CheckConstraint(
            "lifecycle_state IN ('starting','reconciling','running','degraded',"
            "'stopping','stopped')",
            name="ck_collection_scheduler_state",
        ),
    )

    op.create_table(
        "collection_event_outbox",
        sa.Column("event_id", sa.String(64), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("event_schema", sa.String(64), nullable=False),
        sa.Column("stream_id", sa.String(64), nullable=False),
        sa.Column("stream_sequence", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.String(64), nullable=False),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("causation_id", sa.String(64)),
        sa.Column("payload_json", sa.String(4096), nullable=False),
        sa.Column("occurred_at", sa.String(40), nullable=False),
        sa.Column("recorded_at", sa.String(40), nullable=False),
        sa.Column("available_at", sa.String(40), nullable=False),
        sa.UniqueConstraint(
            "stream_id", "stream_sequence", name="uq_collection_outbox_stream"
        ),
        sa.CheckConstraint(
            "stream_sequence > 0", name="ck_collection_outbox_sequence"
        ),
    )
    op.create_index(
        "ix_collection_outbox_available",
        "collection_event_outbox",
        ["available_at", "recorded_at", "event_id"],
    )
    op.create_table(
        "collection_event_delivery",
        sa.Column("event_id", sa.String(64), nullable=False),
        sa.Column("consumer_key", sa.String(64), nullable=False),
        sa.Column("consumer_version", sa.String(32), nullable=False),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.String(40)),
        sa.Column("last_error_code", sa.String(128)),
        sa.Column("delivered_at", sa.String(40)),
        sa.Column("acknowledged_at", sa.String(40)),
        sa.ForeignKeyConstraint(
            ["event_id"], ["collection_event_outbox.event_id"]
        ),
        sa.PrimaryKeyConstraint("event_id", "consumer_key"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_collection_delivery_count"),
    )
    op.create_index(
        "ix_collection_delivery_due",
        "collection_event_delivery",
        ["consumer_key", "state", "next_attempt_at"],
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

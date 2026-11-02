"""M04 cloud-only verification targets, distinct from provider installations."""

# ruff: noqa: E501 -- deterministic SQLite rebuild SQL is intentionally explicit.

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0714"
down_revision = "v1_0713"
branch_labels = None
depends_on = None
TABLES = (
    "collection_schedule",
    "collection_run",
)
METADATA = MappingProxyType(
    {
        "revision": "v1_0714",
        "parent_revision": "v1_0713",
        "owner": "M04",
        "plan_id": "PLAN-M04",
        "requirement_ids": (
            "FR-COL-003",
            "FR-COL-005",
            "FR-COL-006",
            "M6-A07",
            "NFR-DATA-001",
        ),
        "schema_range": ("v1_0714", "v1_0714", "v1_0714", "v1_0714", "v1_0714"),
        "tables": (
            "collection_schedule",
            "collection_run",
        ),
        "portability_notes": (
            "V2 cloud rows leave the legacy installation identity null and store an explicit discriminated target",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "existing_collection_rows_preserved_during_offline_table_rebuild",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m04_cloud_verification_target_schema",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": "preserve_failed_database_and_restore_verified_backup_or_forward_fix",
        "reviewer": "M04-M6-cloud-target-review",
    }
)


def upgrade() -> None:
    # The explicit rebuild is intentionally deterministic. Alembic's reflected
    # batch constraint ordering varies with Python hash randomization, which is
    # incompatible with the repository's exact schema digest.
    op.execute("PRAGMA defer_foreign_keys=ON")
    op.execute(
        "CREATE TABLE _am_v1_0714_collection_schedule ("
        "schedule_id VARCHAR(64) NOT NULL PRIMARY KEY,"
        "target_key_digest VARCHAR(64) NOT NULL UNIQUE,"
        "provider_key VARCHAR(64) NOT NULL,installation_id VARCHAR(64),"
        "provider_target_kind VARCHAR(32),provider_target_id VARCHAR(64),"
        "account_id VARCHAR(64),profile_id VARCHAR(64),resource_id VARCHAR(64),"
        "capability_id VARCHAR(128) NOT NULL,state VARCHAR(40) NOT NULL,"
        "activity_class VARCHAR(16) NOT NULL,base_interval_seconds INTEGER NOT NULL,"
        "effective_interval_seconds INTEGER NOT NULL,target_generation INTEGER NOT NULL,"
        "next_due_at VARCHAR(40) NOT NULL,not_before_at VARCHAR(40),"
        "backoff_kind VARCHAR(40),backoff_generation INTEGER NOT NULL,"
        "consecutive_failure_count INTEGER NOT NULL,last_attempted_run_id VARCHAR(64),"
        "last_successful_run_id VARCHAR(64),last_terminal_outcome_code VARCHAR(128),"
        "record_version INTEGER NOT NULL,created_at VARCHAR(40) NOT NULL,"
        "updated_at VARCHAR(40) NOT NULL,"
        "CONSTRAINT ck_collection_schedule_state CHECK (state IN "
        "('enabled','paused_monitoring_disabled','blocked_authentication',"
        "'blocked_user_action','blocked_compatibility','blocked_unknown_constraints',"
        "'unsupported','retired')),"
        "CONSTRAINT ck_collection_schedule_activity CHECK "
        "(activity_class IN ('active','idle','unknown')),"
        "CONSTRAINT ck_collection_schedule_intervals CHECK "
        "(base_interval_seconds > 0 AND effective_interval_seconds > 0),"
        "CONSTRAINT ck_collection_schedule_versions CHECK "
        "(target_generation > 0 AND record_version > 0),"
        "CONSTRAINT ck_collection_schedule_failures CHECK "
        "(backoff_generation >= 0 AND consecutive_failure_count >= 0),"
        "CONSTRAINT ck_collection_schedule_provider_target CHECK "
        "((installation_id IS NOT NULL AND provider_target_kind IS NULL "
        "AND provider_target_id IS NULL) OR "
        "(installation_id IS NULL AND provider_target_kind='cloud_service' "
        "AND length(provider_target_id)=37 "
        "AND substr(provider_target_id,1,5)='amat_' "
        "AND substr(provider_target_id,6) NOT GLOB '*[^a-f0-9]*')))"
    )
    op.execute(
        "INSERT INTO _am_v1_0714_collection_schedule "
        "(schedule_id,target_key_digest,provider_key,installation_id,account_id,"
        "profile_id,resource_id,capability_id,state,activity_class,"
        "base_interval_seconds,effective_interval_seconds,target_generation,"
        "next_due_at,not_before_at,backoff_kind,backoff_generation,"
        "consecutive_failure_count,last_attempted_run_id,last_successful_run_id,"
        "last_terminal_outcome_code,record_version,created_at,updated_at) SELECT "
        "schedule_id,target_key_digest,provider_key,installation_id,account_id,"
        "profile_id,resource_id,capability_id,state,activity_class,"
        "base_interval_seconds,effective_interval_seconds,target_generation,"
        "next_due_at,not_before_at,backoff_kind,backoff_generation,"
        "consecutive_failure_count,last_attempted_run_id,last_successful_run_id,"
        "last_terminal_outcome_code,record_version,created_at,updated_at "
        "FROM collection_schedule"
    )
    op.drop_table("collection_schedule")
    op.rename_table("_am_v1_0714_collection_schedule", "collection_schedule")
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
    op.create_index(
        "ix_collection_schedule_provider_target",
        "collection_schedule",
        ["provider_target_kind", "provider_target_id", "schedule_id"],
    )
    op.execute(
        "CREATE TABLE _am_v1_0714_collection_run ("
        "run_id VARCHAR(64) NOT NULL PRIMARY KEY,schedule_id VARCHAR(64) NOT NULL,"
        "request_digest VARCHAR(64) NOT NULL,provider_key VARCHAR(64) NOT NULL,"
        "installation_id VARCHAR(64),provider_target_kind VARCHAR(32),"
        "provider_target_id VARCHAR(64),account_id VARCHAR(64),profile_id VARCHAR(64),"
        "resource_id VARCHAR(64),capability_id VARCHAR(128) NOT NULL,"
        "source_id VARCHAR(128) NOT NULL,adapter_version VARCHAR(64) NOT NULL,"
        "adapter_protocol_version VARCHAR(32) NOT NULL,"
        "manifest_fingerprint VARCHAR(64) NOT NULL,"
        "collection_policy_version VARCHAR(32) NOT NULL,registry_revision INTEGER NOT NULL,"
        "provider_version VARCHAR(128),trigger_kind VARCHAR(40) NOT NULL,"
        "primary_request_id VARCHAR(64) NOT NULL,retry_chain_id VARCHAR(64) NOT NULL,"
        "attempt_ordinal INTEGER NOT NULL,target_generation INTEGER NOT NULL,"
        "fencing_token INTEGER NOT NULL,budget_reservation_id VARCHAR(64) NOT NULL,"
        "payload_schema VARCHAR(128) NOT NULL,payload_digest VARCHAR(64),"
        "state VARCHAR(24) NOT NULL,outcome_code VARCHAR(128),error_code VARCHAR(128),"
        "requested_at VARCHAR(40) NOT NULL,queued_at VARCHAR(40) NOT NULL,"
        "started_at VARCHAR(40),completed_at VARCHAR(40),deadline_at VARCHAR(40) NOT NULL,"
        "duration_ms INTEGER,retry_disposition VARCHAR(32),retry_eligible INTEGER,"
        "retry_after VARCHAR(40),correlation_id VARCHAR(64) NOT NULL,"
        "causation_id VARCHAR(64),record_version INTEGER NOT NULL,"
        "provider_outcome_state VARCHAR(40),"
        "FOREIGN KEY(schedule_id) REFERENCES collection_schedule(schedule_id),"
        "CONSTRAINT ck_collection_run_state CHECK (state IN "
        "('requested','queued','running','committing','succeeded','partial','failed',"
        "'blocked','cancelled','unsupported')),"
        "CONSTRAINT ck_collection_run_versions CHECK "
        "(attempt_ordinal > 0 AND registry_revision > 0 AND target_generation > 0 "
        "AND fencing_token > 0 AND record_version > 0),"
        "CONSTRAINT ck_collection_run_retry_bool CHECK "
        "(retry_eligible IS NULL OR retry_eligible IN (0,1)),"
        "CONSTRAINT ck_collection_run_duration CHECK "
        "(duration_ms IS NULL OR duration_ms >= 0),"
        "CONSTRAINT ck_collection_run_provider_target CHECK "
        "((installation_id IS NOT NULL AND provider_target_kind IS NULL "
        "AND provider_target_id IS NULL) OR "
        "(installation_id IS NULL AND provider_target_kind='cloud_service' "
        "AND length(provider_target_id)=37 "
        "AND substr(provider_target_id,1,5)='amat_' "
        "AND substr(provider_target_id,6) NOT GLOB '*[^a-f0-9]*')))"
    )
    op.execute(
        "INSERT INTO _am_v1_0714_collection_run "
        "(run_id,schedule_id,request_digest,provider_key,installation_id,account_id,"
        "profile_id,resource_id,capability_id,source_id,adapter_version,"
        "adapter_protocol_version,manifest_fingerprint,collection_policy_version,"
        "registry_revision,provider_version,trigger_kind,primary_request_id,"
        "retry_chain_id,attempt_ordinal,target_generation,fencing_token,"
        "budget_reservation_id,payload_schema,payload_digest,state,outcome_code,"
        "error_code,requested_at,queued_at,started_at,completed_at,deadline_at,"
        "duration_ms,retry_disposition,retry_eligible,retry_after,correlation_id,"
        "causation_id,record_version,provider_outcome_state) SELECT "
        "run_id,schedule_id,request_digest,provider_key,installation_id,account_id,"
        "profile_id,resource_id,capability_id,source_id,adapter_version,"
        "adapter_protocol_version,manifest_fingerprint,collection_policy_version,"
        "registry_revision,provider_version,trigger_kind,primary_request_id,"
        "retry_chain_id,attempt_ordinal,target_generation,fencing_token,"
        "budget_reservation_id,payload_schema,payload_digest,state,outcome_code,"
        "error_code,requested_at,queued_at,started_at,completed_at,deadline_at,"
        "duration_ms,retry_disposition,retry_eligible,retry_after,correlation_id,"
        "causation_id,record_version,provider_outcome_state FROM collection_run"
    )
    op.drop_table("collection_run")
    op.rename_table("_am_v1_0714_collection_run", "collection_run")
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
    op.create_index(
        "ix_collection_run_provider_target",
        "collection_run",
        ["provider_target_kind", "provider_target_id", "run_id"],
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

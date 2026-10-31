"""M06 process/session identities and immutable core observations."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0600"
down_revision = "v1_0504"
branch_labels = None
depends_on = None

TABLES = (
    "runtime_session",
    "runtime_process_instance",
    "runtime_process_snapshot",
    "runtime_session_observation",
)

_FIELD_STATES = (
    "'present','not_requested','not_found','unsupported','permission_denied',"
    "'process_exited','identity_conflict','unverified_source','deadline_exceeded',"
    "'changed_during_read','unsafe_layout','redacted_by_policy'"
)
_UTC_GLOB = (
    "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T"
    "[0-9][0-9]:[0-9][0-9]:[0-9][0-9]."
    "[0-9][0-9][0-9][0-9][0-9][0-9]Z"
)

METADATA = MappingProxyType(
    {
        "revision": "v1_0600",
        "parent_revision": "v1_0504",
        "owner": "M06",
        "plan_id": "PLAN-M06",
        "requirement_ids": (
            "FR-DISC-001",
            "FR-DISC-002",
            "FR-DISC-003",
            "FR-DISC-006",
            "FR-DISC-008",
            "NFR-DATA-001",
        ),
        "schema_range": (
            "v1_0600",
            "v1_0600",
            "v1_0600",
            "v1_0600",
            "v1_0600",
        ),
        "tables": (
            "runtime_session",
            "runtime_process_instance",
            "runtime_process_snapshot",
            "runtime_session_observation",
        ),
        "portability_notes": (
            "process identity includes a portable platform boot/namespace scope",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_runtime_rows_on_initial_install",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m06_core_tables",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": (
            "preserve_failed_database_and_restore_verified_backup_or_forward_fix"
        ),
        "reviewer": "M06-PLAN-DB-security-review",
    }
)


def _utc(column: str) -> str:
    """Return a SQLite check for canonical six-digit RFC3339 UTC text."""
    return (
        f"length({column})=27 AND {column} GLOB '{_UTC_GLOB}' "
        f"AND julianday({column}) IS NOT NULL "
        f"AND date(substr({column},1,10),'+0 days')=substr({column},1,10)"
    )


def _field_pair(prefix: str, value_column: str) -> str:
    state = f"{prefix}_state"
    unit = f"{prefix}_unit"
    reason = f"{prefix}_reason_code"
    return (
        f"{state} IN ({_FIELD_STATES}) AND (({state}='present' AND "
        f"{value_column} IS NOT NULL AND {unit} IS NOT NULL AND length({unit})>0 "
        f"AND {reason} IS NULL) "
        f"OR ({state}<>'present' AND {value_column} IS NULL AND {unit} IS NULL "
        f"AND {reason} IS NOT NULL AND length({reason})>0))"
    )


def _code_pair(prefix: str, value_column: str) -> str:
    state = f"{prefix}_state"
    reason = f"{prefix}_reason_code"
    return (
        f"{state} IN ({_FIELD_STATES}) AND (({state}='present' AND "
        f"{value_column} IS NOT NULL AND length({value_column})>0 "
        f"AND {reason} IS NULL) OR "
        f"({state}<>'present' AND {value_column} IS NULL "
        f"AND {reason} IS NOT NULL AND length({reason})>0))"
    )


def upgrade() -> None:
    op.create_table(
        "runtime_process_instance",
        sa.Column("process_id", sa.String(64), primary_key=True),
        sa.Column("platform_source", sa.String(128), nullable=False),
        sa.Column("platform_scope_id", sa.String(128), nullable=False),
        sa.Column("pid", sa.Integer(), nullable=False),
        sa.Column("start_time_ticks", sa.BigInteger(), nullable=False),
        sa.Column("executable_identity", sa.String(128)),
        sa.Column("executable_label", sa.String(128)),
        sa.Column("provider_key", sa.String(64)),
        sa.Column("installation_id", sa.String(64)),
        sa.Column("first_observed_at", sa.String(40), nullable=False),
        sa.Column("last_observed_at", sa.String(40), nullable=False),
        sa.Column("presence_state", sa.String(16), nullable=False),
        sa.Column("current_snapshot_id", sa.String(64)),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "platform_source",
            "platform_scope_id",
            "pid",
            "start_time_ticks",
            name="uq_runtime_process_identity",
        ),
        sa.CheckConstraint(
            "pid > 0 AND start_time_ticks > 0",
            name="ck_runtime_process_identity_positive",
        ),
        sa.CheckConstraint(
            "length(platform_source)>0 AND length(platform_scope_id)>0 AND "
            "(executable_identity IS NULL OR length(executable_identity)>0) AND "
            "(executable_label IS NULL OR length(executable_label)>0) AND "
            "(executable_identity IS NOT NULL OR executable_label IS NOT NULL)",
            name="ck_runtime_process_identity_complete",
        ),
        sa.CheckConstraint(
            "(installation_id IS NULL OR provider_key IS NOT NULL) AND "
            "((provider_key IS NULL AND installation_id IS NULL) OR "
            "executable_identity IS NOT NULL)",
            name="ck_runtime_process_attribution_pair",
        ),
        sa.CheckConstraint(
            "presence_state IN ('running','exited','unknown')",
            name="ck_runtime_process_presence",
        ),
        sa.CheckConstraint("record_version > 0", name="ck_runtime_process_version"),
        sa.CheckConstraint(
            f"({_utc('first_observed_at')}) AND ({_utc('last_observed_at')})",
            name="ck_runtime_process_utc",
        ),
        sa.CheckConstraint(
            "last_observed_at >= first_observed_at",
            name="ck_runtime_process_time",
        ),
    )
    op.create_table(
        "runtime_session",
        sa.Column("session_id", sa.String(64), primary_key=True),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("installation_id", sa.String(64), nullable=False),
        sa.Column("identity_kind", sa.String(64), nullable=False),
        sa.Column("identity_value", sa.String(128), nullable=False),
        sa.Column("first_observed_at", sa.String(40), nullable=False),
        sa.Column("last_observed_at", sa.String(40), nullable=False),
        sa.Column("current_observation_id", sa.String(64)),
        sa.Column("correlation_state", sa.String(32), nullable=False),
        sa.Column("account_id", sa.String(64)),
        sa.Column("current_decision_id", sa.String(64)),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "provider_key",
            "installation_id",
            "identity_kind",
            "identity_value",
            name="uq_runtime_session_identity",
        ),
        sa.CheckConstraint(
            "correlation_state IN ('unresolved','automatic_matched',"
            "'confirmation_required','conflict','unsupported','owner_confirmed',"
            "'invalidated')",
            name="ck_runtime_session_correlation_state",
        ),
        sa.CheckConstraint(
            "(correlation_state IN ('automatic_matched','owner_confirmed') "
            "AND account_id IS NOT NULL) OR "
            "(correlation_state NOT IN ('automatic_matched','owner_confirmed') "
            "AND account_id IS NULL)",
            name="ck_runtime_session_account_pair",
        ),
        sa.CheckConstraint("record_version > 0", name="ck_runtime_session_version"),
        sa.CheckConstraint(
            f"({_utc('first_observed_at')}) AND ({_utc('last_observed_at')})",
            name="ck_runtime_session_utc",
        ),
        sa.CheckConstraint(
            "last_observed_at >= first_observed_at",
            name="ck_runtime_session_time",
        ),
    )
    op.create_table(
        "runtime_process_snapshot",
        sa.Column("snapshot_id", sa.String(64), primary_key=True),
        sa.Column("process_id", sa.String(64), nullable=False),
        sa.Column("collection_run_id", sa.String(64), nullable=False),
        sa.Column("source_observation_id", sa.String(128), nullable=False),
        sa.Column("observed_at", sa.String(40), nullable=False),
        sa.Column("collected_at", sa.String(40), nullable=False),
        sa.Column("stored_at", sa.String(40), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("source_version", sa.String(64), nullable=False),
        sa.Column("adapter_version", sa.String(64), nullable=False),
        sa.Column("presence_state", sa.String(16), nullable=False),
        sa.Column("executable_label_state", sa.String(32), nullable=False),
        sa.Column("executable_label", sa.String(128)),
        sa.Column("executable_label_reason_code", sa.String(128)),
        sa.Column("parent_pid_state", sa.String(32), nullable=False),
        sa.Column("parent_pid", sa.Integer()),
        sa.Column("parent_pid_unit", sa.String(32)),
        sa.Column("parent_pid_reason_code", sa.String(128)),
        sa.Column("user_cpu_state", sa.String(32), nullable=False),
        sa.Column("user_cpu_ticks", sa.BigInteger()),
        sa.Column("user_cpu_unit", sa.String(32)),
        sa.Column("user_cpu_reason_code", sa.String(128)),
        sa.Column("system_cpu_state", sa.String(32), nullable=False),
        sa.Column("system_cpu_ticks", sa.BigInteger()),
        sa.Column("system_cpu_unit", sa.String(32)),
        sa.Column("system_cpu_reason_code", sa.String(128)),
        sa.Column("resident_state", sa.String(32), nullable=False),
        sa.Column("resident_pages", sa.BigInteger()),
        sa.Column("resident_unit", sa.String(32)),
        sa.Column("resident_reason_code", sa.String(128)),
        sa.Column("thread_state", sa.String(32), nullable=False),
        sa.Column("thread_count", sa.Integer()),
        sa.Column("thread_unit", sa.String(32)),
        sa.Column("thread_reason_code", sa.String(128)),
        sa.Column("kernel_state_state", sa.String(32), nullable=False),
        sa.Column("kernel_state", sa.String(1)),
        sa.Column("kernel_state_unit", sa.String(32)),
        sa.Column("kernel_state_reason_code", sa.String(128)),
        sa.Column("clock_ticks_per_second", sa.Integer(), nullable=False),
        sa.Column("page_size_bytes", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["process_id"], ["runtime_process_instance.process_id"]
        ),
        sa.UniqueConstraint(
            "source_id",
            "source_observation_id",
            name="uq_runtime_process_source_observation",
        ),
        sa.CheckConstraint(
            "presence_state IN ('running','exited','unknown')",
            name="ck_runtime_snapshot_presence",
        ),
        sa.CheckConstraint(
            _code_pair("executable_label", "executable_label"),
            name="ck_runtime_snapshot_executable_label_pair",
        ),
        sa.CheckConstraint(
            _field_pair("parent_pid", "parent_pid"),
            name="ck_runtime_snapshot_parent_pair",
        ),
        sa.CheckConstraint(
            _field_pair("user_cpu", "user_cpu_ticks"),
            name="ck_runtime_snapshot_user_cpu_pair",
        ),
        sa.CheckConstraint(
            _field_pair("system_cpu", "system_cpu_ticks"),
            name="ck_runtime_snapshot_system_cpu_pair",
        ),
        sa.CheckConstraint(
            _field_pair("resident", "resident_pages"),
            name="ck_runtime_snapshot_resident_pair",
        ),
        sa.CheckConstraint(
            _field_pair("thread", "thread_count"),
            name="ck_runtime_snapshot_thread_pair",
        ),
        sa.CheckConstraint(
            _field_pair("kernel_state", "kernel_state"),
            name="ck_runtime_snapshot_kernel_pair",
        ),
        sa.CheckConstraint(
            "parent_pid IS NULL OR parent_pid >= 0",
            name="ck_runtime_snapshot_parent_value",
        ),
        sa.CheckConstraint(
            "user_cpu_ticks IS NULL OR user_cpu_ticks >= 0",
            name="ck_runtime_snapshot_user_cpu_value",
        ),
        sa.CheckConstraint(
            "system_cpu_ticks IS NULL OR system_cpu_ticks >= 0",
            name="ck_runtime_snapshot_system_cpu_value",
        ),
        sa.CheckConstraint(
            "resident_pages IS NULL OR resident_pages >= 0",
            name="ck_runtime_snapshot_resident_value",
        ),
        sa.CheckConstraint(
            "thread_count IS NULL OR thread_count >= 0",
            name="ck_runtime_snapshot_thread_value",
        ),
        sa.CheckConstraint(
            "kernel_state IS NULL OR length(kernel_state)=1",
            name="ck_runtime_snapshot_kernel_value",
        ),
        sa.CheckConstraint(
            "clock_ticks_per_second > 0 AND page_size_bytes > 0",
            name="ck_runtime_snapshot_units",
        ),
        sa.CheckConstraint(
            f"({_utc('observed_at')}) AND ({_utc('collected_at')}) "
            f"AND ({_utc('stored_at')})",
            name="ck_runtime_snapshot_utc",
        ),
        sa.CheckConstraint(
            "stored_at >= collected_at",
            name="ck_runtime_snapshot_storage_time",
        ),
    )
    op.create_table(
        "runtime_session_observation",
        sa.Column("observation_id", sa.String(64), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("collection_run_id", sa.String(64), nullable=False),
        sa.Column("source_observation_id", sa.String(128), nullable=False),
        sa.Column("observed_at", sa.String(40), nullable=False),
        sa.Column("collected_at", sa.String(40), nullable=False),
        sa.Column("stored_at", sa.String(40), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("source_version", sa.String(64), nullable=False),
        sa.Column("parser_version", sa.String(64), nullable=False),
        sa.Column("provider_version", sa.String(64), nullable=False),
        sa.Column("activity_state", sa.String(32), nullable=False),
        sa.Column("activity_code", sa.String(128)),
        sa.Column("activity_reason_code", sa.String(128)),
        sa.ForeignKeyConstraint(["session_id"], ["runtime_session.session_id"]),
        sa.UniqueConstraint(
            "source_id",
            "source_observation_id",
            name="uq_runtime_session_source_observation",
        ),
        sa.CheckConstraint(
            f"activity_state IN ({_FIELD_STATES}) AND "
            "((activity_state='present' AND activity_code IS NOT NULL "
            "AND length(activity_code)>0 AND activity_reason_code IS NULL) OR "
            "(activity_state<>'present' AND activity_code IS NULL "
            "AND activity_reason_code IS NOT NULL "
            "AND length(activity_reason_code)>0))",
            name="ck_runtime_session_activity_pair",
        ),
        sa.CheckConstraint(
            f"({_utc('observed_at')}) AND ({_utc('collected_at')}) "
            f"AND ({_utc('stored_at')})",
            name="ck_runtime_session_observation_utc",
        ),
        sa.CheckConstraint(
            "stored_at >= collected_at",
            name="ck_runtime_session_observation_storage_time",
        ),
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

"""M06 state policy, transitions, durable commit receipt, and outbox."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0602"
down_revision = "v1_0601"
branch_labels = None
depends_on = None

TABLES = (
    "runtime_stall_policy",
    "runtime_state_transition",
    "runtime_ingest_receipt",
    "runtime_event_outbox",
)

_AVAILABILITY_STATES = (
    "'available','missing','null','unknown','unsupported','unavailable',"
    "'not_applicable','withheld_or_denied','stale','unresolved'"
)
_RUNTIME_STATES = (
    "'working','waiting_for_input','waiting_for_permission','idle',"
    "'quota_or_rate_limited','reauthentication_required',"
    "'provider_or_network_error','possibly_stuck','exited_successfully',"
    "'crashed','unknown'"
)
_UTC_GLOB = (
    "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T"
    "[0-9][0-9]:[0-9][0-9]:[0-9][0-9]."
    "[0-9][0-9][0-9][0-9][0-9][0-9]Z"
)

METADATA = MappingProxyType(
    {
        "revision": "v1_0602",
        "parent_revision": "v1_0601",
        "owner": "M06",
        "plan_id": "PLAN-M06",
        "requirement_ids": (
            "FR-STATE-001",
            "FR-STATE-002",
            "FR-HIST-001",
            "FR-HIST-002",
            "NFR-DATA-001",
        ),
        "schema_range": (
            "v1_0602",
            "v1_0602",
            "v1_0602",
            "v1_0602",
            "v1_0602",
        ),
        "tables": (
            "runtime_stall_policy",
            "runtime_state_transition",
            "runtime_ingest_receipt",
            "runtime_event_outbox",
        ),
        "portability_notes": (
            "JSON text columns contain only closed safe ID/code arrays",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_runtime_rows_on_initial_install",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m06_state_outbox_tables",
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
    return (
        f"length({column})=27 AND {column} GLOB '{_UTC_GLOB}' "
        f"AND julianday({column}) IS NOT NULL "
        f"AND date(substr({column},1,10),'+0 days')=substr({column},1,10)"
    )


def _nullable_utc(column: str) -> str:
    return f"{column} IS NULL OR ({_utc(column)})"


def _available_pair(value: str, availability: str) -> str:
    return (
        f"{availability} IN ({_AVAILABILITY_STATES}) AND "
        f"(({availability} IN ('available','stale') AND {value} IS NOT NULL) OR "
        f"({availability} NOT IN ('available','stale') AND {value} IS NULL))"
    )


def _json_array(column: str) -> str:
    return f"json_valid({column})=1 AND json_type({column})='array'"


def upgrade() -> None:
    op.create_table(
        "runtime_stall_policy",
        sa.Column("policy_id", sa.String(64), primary_key=True),
        sa.Column("scope_kind", sa.String(24), nullable=False),
        sa.Column("scope_id", sa.String(64), nullable=False),
        sa.Column("threshold_seconds", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Integer(), nullable=False),
        sa.Column("is_current", sa.Integer(), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.CheckConstraint(
            "scope_kind IN ('global','organization','provider','account')",
            name="ck_runtime_policy_scope",
        ),
        sa.CheckConstraint(
            "(scope_kind='global' AND scope_id='global') OR "
            "(scope_kind<>'global' AND scope_id<>'global' AND length(scope_id)>0)",
            name="ck_runtime_policy_scope_pair",
        ),
        sa.CheckConstraint(
            "threshold_seconds > 0",
            name="ck_runtime_policy_threshold",
        ),
        sa.CheckConstraint(
            "enabled IN (0,1) AND is_current IN (0,1)",
            name="ck_runtime_policy_flags",
        ),
        sa.CheckConstraint("policy_version > 0", name="ck_runtime_policy_version"),
        sa.CheckConstraint(
            f"({_utc('created_at')}) AND ({_utc('updated_at')})",
            name="ck_runtime_policy_utc",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_runtime_policy_time_order",
        ),
    )
    op.create_table(
        "runtime_state_transition",
        sa.Column("transition_id", sa.String(64), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("stream_sequence", sa.Integer(), nullable=False),
        sa.Column("prior_state", sa.String(40)),
        sa.Column("current_state", sa.String(40), nullable=False),
        sa.Column("certainty", sa.String(16), nullable=False),
        sa.Column("reason_code", sa.String(128), nullable=False),
        sa.Column("observed_at", sa.String(40), nullable=False),
        sa.Column("evaluated_at", sa.String(40), nullable=False),
        sa.Column("runtime_revision", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["runtime_session.session_id"]),
        sa.UniqueConstraint(
            "session_id", "stream_sequence", name="uq_runtime_state_stream"
        ),
        sa.CheckConstraint(
            "stream_sequence > 0 AND runtime_revision > 0",
            name="ck_runtime_state_versions",
        ),
        sa.CheckConstraint(
            "certainty IN ('definitive','inferred','unknown')",
            name="ck_runtime_state_certainty",
        ),
        sa.CheckConstraint(
            f"prior_state IS NULL OR prior_state IN ({_RUNTIME_STATES})",
            name="ck_runtime_state_prior",
        ),
        sa.CheckConstraint(
            f"current_state IN ({_RUNTIME_STATES})",
            name="ck_runtime_state_current",
        ),
        sa.CheckConstraint(
            f"({_utc('observed_at')}) AND ({_utc('evaluated_at')})",
            name="ck_runtime_state_utc",
        ),
        sa.CheckConstraint(
            "evaluated_at >= observed_at",
            name="ck_runtime_state_time_order",
        ),
    )
    op.create_table(
        "runtime_ingest_receipt",
        sa.Column("receipt_id", sa.String(64), primary_key=True),
        sa.Column("collection_run_id", sa.String(64), nullable=False),
        sa.Column("target_generation", sa.Integer(), nullable=False),
        sa.Column("capability_id", sa.String(128), nullable=False),
        sa.Column("capability_schema_version", sa.String(64), nullable=False),
        sa.Column("payload_schema", sa.String(128), nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("consumer_key", sa.String(64), nullable=False),
        sa.Column("consumer_version", sa.String(32), nullable=False),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("adapter_id", sa.String(128), nullable=False),
        sa.Column("adapter_version", sa.String(64), nullable=False),
        sa.Column("provider_protocol_version", sa.String(64), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("source_class", sa.String(40), nullable=False),
        sa.Column("mechanism_version", sa.String(64), nullable=False),
        sa.Column("parser_version", sa.String(64)),
        sa.Column("provider_version", sa.String(64)),
        sa.Column("provider_version_availability", sa.String(24), nullable=False),
        sa.Column("observed_at", sa.String(40)),
        sa.Column("observed_at_availability", sa.String(24), nullable=False),
        sa.Column("collected_at", sa.String(40), nullable=False),
        sa.Column("freshness_deadline", sa.String(40)),
        sa.Column("freshness_availability", sa.String(24), nullable=False),
        sa.Column("freshness_policy_id", sa.String(128), nullable=False),
        sa.Column("precision", sa.String(16), nullable=False),
        sa.Column("confidence", sa.String(16), nullable=False),
        sa.Column("confidence_reason_code", sa.String(128), nullable=False),
        sa.Column("value_kind", sa.String(24), nullable=False),
        sa.Column("is_experimental", sa.Integer(), nullable=False),
        sa.Column("operation_id", sa.String(64), nullable=False),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("decision_reference", sa.String(128), nullable=False),
        sa.Column("derivation_method", sa.String(128)),
        sa.Column("fallback_lineage_json", sa.Text(), nullable=False),
        sa.Column("warnings_json", sa.Text(), nullable=False),
        sa.Column("input_observation_ids_json", sa.Text(), nullable=False),
        sa.Column("observation_set_digest", sa.String(64), nullable=False),
        sa.Column("observation_ids_json", sa.Text(), nullable=False),
        sa.Column("affected_projection_ids_json", sa.Text(), nullable=False),
        sa.Column("projection_versions_json", sa.Text(), nullable=False),
        sa.Column("event_ids_json", sa.Text(), nullable=False),
        sa.Column("stored_at_start", sa.String(40), nullable=False),
        sa.Column("stored_at_end", sa.String(40), nullable=False),
        sa.Column("stored_at", sa.String(40), nullable=False),
        sa.Column("receipt_version", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "collection_run_id",
            "capability_id",
            name="uq_runtime_receipt_run_capability",
        ),
        sa.CheckConstraint(
            "target_generation > 0 AND receipt_version > 0",
            name="ck_runtime_receipt_versions",
        ),
        sa.CheckConstraint(
            "length(payload_digest)=64 AND length(observation_set_digest)=64",
            name="ck_runtime_receipt_digests",
        ),
        sa.CheckConstraint(
            "source_class IN ('documented_api','supported_cli',"
            "'approved_local_metadata','experimental_private_or_browser')",
            name="ck_runtime_receipt_source_class",
        ),
        sa.CheckConstraint(
            _available_pair("provider_version", "provider_version_availability"),
            name="ck_runtime_receipt_provider_version_pair",
        ),
        sa.CheckConstraint(
            _available_pair("observed_at", "observed_at_availability"),
            name="ck_runtime_receipt_observed_at_pair",
        ),
        sa.CheckConstraint(
            _available_pair("freshness_deadline", "freshness_availability"),
            name="ck_runtime_receipt_freshness_pair",
        ),
        sa.CheckConstraint(
            "precision IN ('exact','rounded','range','estimated','unknown')",
            name="ck_runtime_receipt_precision",
        ),
        sa.CheckConstraint(
            "confidence IN ('confirmed','high','medium','low','unknown')",
            name="ck_runtime_receipt_confidence",
        ),
        sa.CheckConstraint(
            "value_kind IN ('authoritative','provider_reported','derived',"
            "'heuristic','unknown')",
            name="ck_runtime_receipt_value_kind",
        ),
        sa.CheckConstraint(
            "is_experimental IN (0,1)",
            name="ck_runtime_receipt_experimental",
        ),
        sa.CheckConstraint(
            f"({_json_array('fallback_lineage_json')}) AND "
            f"({_json_array('warnings_json')}) AND "
            f"({_json_array('input_observation_ids_json')}) AND "
            f"({_json_array('observation_ids_json')}) AND "
            f"({_json_array('affected_projection_ids_json')}) AND "
            f"({_json_array('projection_versions_json')}) AND "
            f"({_json_array('event_ids_json')})",
            name="ck_runtime_receipt_json_arrays",
        ),
        sa.CheckConstraint(
            "(value_kind='derived' AND derivation_method IS NOT NULL "
            "AND json_array_length(input_observation_ids_json)>0) OR "
            "(value_kind<>'derived' AND derivation_method IS NULL "
            "AND json_array_length(input_observation_ids_json)=0)",
            name="ck_runtime_receipt_derivation_pair",
        ),
        sa.CheckConstraint(
            f"({_nullable_utc('observed_at')}) AND ({_utc('collected_at')}) "
            f"AND ({_nullable_utc('freshness_deadline')}) "
            f"AND ({_utc('stored_at_start')}) AND ({_utc('stored_at_end')}) "
            f"AND ({_utc('stored_at')})",
            name="ck_runtime_receipt_utc",
        ),
        sa.CheckConstraint(
            "(observed_at IS NULL OR collected_at >= observed_at) AND "
            "(freshness_deadline IS NULL OR observed_at IS NULL OR "
            "freshness_deadline >= observed_at) AND "
            "(freshness_availability<>'stale' OR "
            "freshness_deadline <= collected_at) AND "
            "stored_at_end >= stored_at_start AND stored_at >= stored_at_end",
            name="ck_runtime_receipt_time_order",
        ),
    )
    op.create_table(
        "runtime_event_outbox",
        sa.Column("event_id", sa.String(64), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("event_schema", sa.String(64), nullable=False),
        sa.Column("subject_id", sa.String(64), nullable=False),
        sa.Column("stream_sequence", sa.Integer(), nullable=False),
        sa.Column("producer_sequence", sa.Integer(), nullable=False),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("causation_id", sa.String(64)),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.String(40), nullable=False),
        sa.Column("recorded_at", sa.String(40), nullable=False),
        sa.Column("available_at", sa.String(40), nullable=False),
        sa.Column(
            "delivery_state", sa.String(16), nullable=False, server_default="pending"
        ),
        sa.Column("claimed_at", sa.String(40)),
        sa.Column("delivered_at", sa.String(40)),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint(
            "subject_id", "stream_sequence", name="uq_runtime_event_stream"
        ),
        sa.UniqueConstraint(
            "producer_sequence", name="uq_runtime_event_producer_sequence"
        ),
        sa.CheckConstraint(
            "stream_sequence > 0 AND producer_sequence > 0",
            name="ck_runtime_event_sequences",
        ),
        sa.CheckConstraint(
            "delivery_state IN ('pending','claimed','delivered')",
            name="ck_runtime_event_delivery_state",
        ),
        sa.CheckConstraint("attempt_count >= 0", name="ck_runtime_event_attempts"),
        sa.CheckConstraint(
            "causation_id IS NULL OR length(causation_id)>0",
            name="ck_runtime_event_causation",
        ),
        sa.CheckConstraint(
            "json_valid(payload_json)=1 AND json_type(payload_json)='object'",
            name="ck_runtime_event_payload",
        ),
        sa.CheckConstraint(
            f"({_utc('occurred_at')}) AND ({_utc('recorded_at')}) "
            f"AND ({_utc('available_at')}) AND ({_nullable_utc('claimed_at')}) "
            f"AND ({_nullable_utc('delivered_at')})",
            name="ck_runtime_event_utc",
        ),
        sa.CheckConstraint(
            "recorded_at >= occurred_at AND available_at >= recorded_at AND "
            "(claimed_at IS NULL OR claimed_at >= available_at) AND "
            "(delivered_at IS NULL OR "
            "(claimed_at IS NOT NULL AND delivered_at >= claimed_at))",
            name="ck_runtime_event_time_order",
        ),
        sa.CheckConstraint(
            "(delivery_state='pending' AND claimed_at IS NULL "
            "AND delivered_at IS NULL) OR "
            "(delivery_state='claimed' AND claimed_at IS NOT NULL "
            "AND delivered_at IS NULL AND attempt_count>0) OR "
            "(delivery_state='delivered' AND claimed_at IS NOT NULL "
            "AND delivered_at IS NOT NULL AND attempt_count>0)",
            name="ck_runtime_event_lifecycle",
        ),
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

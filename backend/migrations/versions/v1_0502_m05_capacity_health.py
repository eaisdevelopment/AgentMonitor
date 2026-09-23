"""M05 health, aggregate, availability, and module-owned event projections."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0502"
down_revision = "v1_0501"
branch_labels = None
depends_on = None

TABLES = (
    "capacity_health_projection",
    "capacity_aggregate_projection",
    "capacity_aggregate_value",
    "capacity_availability_signal",
    "capacity_event_outbox",
    "capacity_event_delivery",
)

METADATA = MappingProxyType(
    {
        "revision": "v1_0502",
        "parent_revision": "v1_0501",
        "owner": "M05",
        "plan_id": "PLAN-M05",
        "requirement_ids": (
            "FR-QUOTA-003",
            "FR-QUOTA-004",
            "FR-COL-006",
            "FR-ORG-003",
            "NFR-DATA-001",
        ),
        "schema_range": (
            "v1_0502",
            "v1_0502",
            "v1_0502",
            "v1_0502",
            "v1_0502",
        ),
        "tables": (
            "capacity_health_projection",
            "capacity_aggregate_projection",
            "capacity_aggregate_value",
            "capacity_availability_signal",
            "capacity_event_outbox",
            "capacity_event_delivery",
        ),
        "portability_notes": (
            "Health and aggregates retain policy versions and completeness",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_capacity_rows_on_initial_install",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m05_health_event_tables",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": (
            "preserve_failed_database_and_restore_verified_backup_or_forward_fix"
        ),
        "reviewer": "M05-PLAN-DB-security-review",
    }
)


def upgrade() -> None:
    op.create_table(
        "capacity_health_projection",
        sa.Column("health_projection_id", sa.String(64), primary_key=True),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=False),
        sa.Column("capability_id", sa.String(128), nullable=False),
        sa.Column("subject_scope_kind", sa.String(32), nullable=False),
        sa.Column("subject_scope_id", sa.String(64), nullable=False),
        sa.Column("health_state", sa.String(40), nullable=False),
        sa.Column("completeness", sa.String(24), nullable=False),
        sa.Column("freshness_state", sa.String(32), nullable=False),
        sa.Column("constraining_window_definition_id", sa.String(64)),
        sa.Column("constraining_resource_id", sa.String(64)),
        sa.Column("policy_id", sa.String(64), nullable=False),
        sa.Column("policy_version", sa.String(32), nullable=False),
        sa.Column("constrained_coefficient", sa.String(80)),
        sa.Column("constrained_scale", sa.Integer()),
        sa.Column("critical_coefficient", sa.String(80)),
        sa.Column("critical_scale", sa.Integer()),
        sa.Column("availability_signal_id", sa.String(64)),
        sa.Column("availability_signal_generation", sa.Integer()),
        sa.Column("input_set_digest", sa.String(64), nullable=False),
        sa.Column("derivation_id", sa.String(64)),
        sa.Column("explanation_codes_json", sa.String(2048), nullable=False),
        sa.Column("evaluated_at", sa.String(40), nullable=False),
        sa.Column("valid_until", sa.String(40)),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.Column("projected_at", sa.String(40), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["constraining_window_definition_id"],
            ["capacity_quota_window_definition.window_definition_id"],
        ),
        sa.UniqueConstraint(
            "provider_key",
            "account_id",
            "resource_id",
            "capability_id",
            name="uq_capacity_health_scope",
        ),
        sa.CheckConstraint(
            "health_state IN ('available','constrained','critical','exhausted',"
            "'reauthentication_required','unknown')",
            name="ck_capacity_health_state",
        ),
        sa.CheckConstraint(
            "completeness IN ('complete','partial','unknown')",
            name="ck_capacity_health_completeness",
        ),
        sa.CheckConstraint(
            "freshness_state IN ('fresh','stale','freshness_unknown','conflicted')",
            name="ck_capacity_health_freshness",
        ),
        sa.CheckConstraint("record_version > 0", name="ck_capacity_health_version"),
        sa.CheckConstraint(
            "(constrained_scale IS NULL OR constrained_scale BETWEEN 0 AND 18) AND "
            "(critical_scale IS NULL OR critical_scale BETWEEN 0 AND 18)",
            name="ck_capacity_health_boundary_scales",
        ),
        sa.CheckConstraint(
            "length(input_set_digest) = 64", name="ck_capacity_health_input_digest"
        ),
        sa.CheckConstraint(
            "(availability_signal_id IS NULL AND "
            "availability_signal_generation IS NULL) OR "
            "(availability_signal_id IS NOT NULL AND "
            "availability_signal_generation > 0)",
            name="ck_capacity_health_availability_pair",
        ),
    )
    op.create_index(
        "ix_capacity_health_account",
        "capacity_health_projection",
        ["account_id", "health_state", "resource_id"],
    )
    op.create_table(
        "capacity_aggregate_projection",
        sa.Column("aggregate_projection_id", sa.String(64), primary_key=True),
        sa.Column("scope_kind", sa.String(32), nullable=False),
        sa.Column("scope_id", sa.String(64), nullable=False),
        sa.Column("provider_key", sa.String(64)),
        sa.Column("as_of_bucket", sa.String(40), nullable=False),
        sa.Column("health_state", sa.String(40), nullable=False),
        sa.Column("completeness", sa.String(24), nullable=False),
        sa.Column("subject_count", sa.Integer(), nullable=False),
        sa.Column("included_count", sa.Integer(), nullable=False),
        sa.Column("omitted_count", sa.Integer(), nullable=False),
        sa.Column("available_count", sa.Integer(), nullable=False),
        sa.Column("constrained_count", sa.Integer(), nullable=False),
        sa.Column("critical_count", sa.Integer(), nullable=False),
        sa.Column("exhausted_count", sa.Integer(), nullable=False),
        sa.Column("reauthentication_required_count", sa.Integer(), nullable=False),
        sa.Column("unknown_count", sa.Integer(), nullable=False),
        sa.Column("fresh_count", sa.Integer(), nullable=False),
        sa.Column("stale_count", sa.Integer(), nullable=False),
        sa.Column("freshness_unknown_count", sa.Integer(), nullable=False),
        sa.Column("conflicted_count", sa.Integer(), nullable=False),
        sa.Column("source_coverage_state", sa.String(24), nullable=False),
        sa.Column("pool_inventory_json", sa.String(4096), nullable=False),
        sa.Column("omitted_reason_codes_json", sa.String(2048), nullable=False),
        sa.Column("input_projection_set_digest", sa.String(64), nullable=False),
        sa.Column("policy_id", sa.String(64), nullable=False),
        sa.Column("policy_version", sa.String(32), nullable=False),
        sa.Column("registry_revision", sa.Integer(), nullable=False),
        sa.Column("projected_at", sa.String(40), nullable=False),
        sa.Column("generated_at", sa.String(40), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "scope_kind",
            "scope_id",
            "provider_key",
            "registry_revision",
            "as_of_bucket",
            name="uq_capacity_aggregate_scope",
        ),
        sa.CheckConstraint(
            "scope_kind IN ('global','organization','provider','account','resource')",
            name="ck_capacity_aggregate_scope",
        ),
        sa.CheckConstraint(
            "subject_count >= 0 AND included_count >= 0 AND omitted_count >= 0 "
            "AND available_count >= 0 AND constrained_count >= 0 AND "
            "critical_count >= 0 AND exhausted_count >= 0 AND "
            "reauthentication_required_count >= 0 AND unknown_count >= 0 AND "
            "fresh_count >= 0 AND stale_count >= 0 AND "
            "freshness_unknown_count >= 0 AND conflicted_count >= 0 AND "
            "included_count + omitted_count = subject_count AND "
            "available_count + constrained_count + critical_count + "
            "exhausted_count + reauthentication_required_count + unknown_count = "
            "included_count AND fresh_count + stale_count + "
            "freshness_unknown_count + conflicted_count = included_count",
            name="ck_capacity_aggregate_counts",
        ),
        sa.CheckConstraint(
            "source_coverage_state IN ('complete','partial','unknown')",
            name="ck_capacity_aggregate_source_coverage",
        ),
        sa.CheckConstraint(
            "length(input_projection_set_digest) = 64",
            name="ck_capacity_aggregate_input_digest",
        ),
        sa.CheckConstraint(
            "registry_revision > 0 AND record_version > 0",
            name="ck_capacity_aggregate_versions",
        ),
    )
    op.create_table(
        "capacity_aggregate_value",
        sa.Column("aggregate_projection_id", sa.String(64), nullable=False),
        sa.Column("metric_key", sa.String(64), nullable=False),
        sa.Column("coefficient", sa.String(80), nullable=False),
        sa.Column("scale", sa.Integer(), nullable=False),
        sa.Column("unit", sa.String(64), nullable=False),
        sa.Column("currency", sa.String(3)),
        sa.Column("interval_start", sa.String(40)),
        sa.Column("interval_end", sa.String(40)),
        sa.Column("semantic_role", sa.String(64), nullable=False),
        sa.Column("input_count", sa.Integer(), nullable=False),
        sa.Column("omitted_count", sa.Integer(), nullable=False),
        sa.Column("omitted_reason_code", sa.String(128)),
        sa.ForeignKeyConstraint(
            ["aggregate_projection_id"],
            ["capacity_aggregate_projection.aggregate_projection_id"],
        ),
        sa.PrimaryKeyConstraint("aggregate_projection_id", "metric_key"),
        sa.CheckConstraint(
            "scale BETWEEN 0 AND 18", name="ck_capacity_aggregate_scale"
        ),
        sa.CheckConstraint(
            "input_count > 0 AND omitted_count >= 0",
            name="ck_capacity_aggregate_inputs",
        ),
        sa.CheckConstraint(
            "(omitted_count=0 AND omitted_reason_code IS NULL) OR "
            "(omitted_count>0 AND omitted_reason_code IS NOT NULL)",
            name="ck_capacity_aggregate_omission",
        ),
    )
    op.create_table(
        "capacity_availability_signal",
        sa.Column("signal_id", sa.String(64), primary_key=True),
        sa.Column("event_id", sa.String(64), nullable=False, unique=True),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=False),
        sa.Column("capability_id", sa.String(128), nullable=False),
        sa.Column("signal_kind", sa.String(40), nullable=False),
        sa.Column("signal_state", sa.String(32), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("stream_sequence", sa.Integer(), nullable=False),
        sa.Column("reason_code", sa.String(128), nullable=False),
        sa.Column("source_contract", sa.String(64), nullable=False),
        sa.Column("source_version", sa.String(32), nullable=False),
        sa.Column("source_record_id", sa.String(64), nullable=False),
        sa.Column("source_record_version", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.String(40), nullable=False),
        sa.Column("recorded_at", sa.String(40), nullable=False),
        sa.Column("observed_at", sa.String(40), nullable=False),
        sa.Column("expires_at", sa.String(40)),
        sa.Column("invalidated_at", sa.String(40)),
        sa.Column("cleared_by_event_id", sa.String(64)),
        sa.Column("is_current", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "signal_kind IN ('authentication','collector','capability')",
            name="ck_capacity_signal_kind",
        ),
        sa.CheckConstraint("is_current IN (0,1)", name="ck_capacity_signal_current"),
        sa.CheckConstraint(
            "source_record_version > 0 AND generation > 0 AND stream_sequence > 0",
            name="ck_capacity_signal_version",
        ),
        sa.CheckConstraint(
            "signal_state IN ('reauthentication_required','unavailable','blocked',"
            "'recovered')",
            name="ck_capacity_signal_state",
        ),
        sa.UniqueConstraint(
            "provider_key",
            "account_id",
            "resource_id",
            "capability_id",
            "stream_sequence",
            name="uq_capacity_signal_stream",
        ),
    )
    op.create_index(
        "ix_capacity_signal_current",
        "capacity_availability_signal",
        ["account_id", "resource_id", "capability_id", "is_current"],
    )
    op.create_index(
        "uq_capacity_signal_one_current",
        "capacity_availability_signal",
        ["provider_key", "account_id", "resource_id", "capability_id"],
        unique=True,
        sqlite_where=sa.text("is_current=1"),
    )
    op.create_table(
        "capacity_event_outbox",
        sa.Column("event_id", sa.String(64), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("event_schema", sa.String(64), nullable=False),
        sa.Column("projection_stream_key", sa.String(128), nullable=False),
        sa.Column("stream_sequence", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.String(64), nullable=False),
        sa.Column("subject_version", sa.Integer(), nullable=False),
        sa.Column("producer_sequence", sa.Integer(), nullable=False, unique=True),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("causation_id", sa.String(64)),
        sa.Column("payload_json", sa.String(4096), nullable=False),
        sa.Column("occurred_at", sa.String(40), nullable=False),
        sa.Column("recorded_at", sa.String(40), nullable=False),
        sa.Column("available_at", sa.String(40), nullable=False),
        sa.UniqueConstraint(
            "projection_stream_key",
            "stream_sequence",
            name="uq_capacity_event_stream",
        ),
        sa.CheckConstraint("subject_version > 0", name="ck_capacity_event_version"),
        sa.CheckConstraint(
            "producer_sequence > 0 AND stream_sequence > 0",
            name="ck_capacity_event_sequence",
        ),
    )
    op.create_index(
        "ix_capacity_event_available",
        "capacity_event_outbox",
        ["available_at", "producer_sequence", "event_id"],
    )
    op.create_table(
        "capacity_event_delivery",
        sa.Column("event_id", sa.String(64), nullable=False),
        sa.Column("consumer_key", sa.String(64), nullable=False),
        sa.Column("consumer_version", sa.String(32), nullable=False),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.String(40)),
        sa.Column("last_error_code", sa.String(128)),
        sa.Column("delivered_at", sa.String(40)),
        sa.Column("acknowledged_at", sa.String(40)),
        sa.ForeignKeyConstraint(["event_id"], ["capacity_event_outbox.event_id"]),
        sa.PrimaryKeyConstraint("event_id", "consumer_key"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_capacity_delivery_count"),
        sa.CheckConstraint(
            "state IN ('pending','claimed','delivered','acknowledged','failed')",
            name="ck_capacity_delivery_state",
        ),
    )
    op.create_index(
        "ix_capacity_delivery_due",
        "capacity_event_delivery",
        ["consumer_key", "state", "next_attempt_at"],
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

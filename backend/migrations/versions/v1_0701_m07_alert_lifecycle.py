"""M07 additive v1_0701; no telemetry or builtin policy rows."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0701"
down_revision = "v1_0700"
branch_labels = None
depends_on = None

TABLES = (
    "alert_alert",
    "alert_event",
    "alert_evidence_reference",
    "alert_event_receipt",
    "alert_stream_checkpoint",
    "alert_command_receipt",
)

METADATA = MappingProxyType(
    {
        "revision": "v1_0701",
        "parent_revision": "v1_0700",
        "owner": "M07",
        "plan_id": "PLAN-M07",
        "requirement_ids": (
            "FR-ALERT-001",
            "FR-ALERT-002",
            "FR-ALERT-003",
            "FR-ALERT-004",
            "FR-ALERT-005",
            "FR-HIST-001",
            "FR-HIST-002",
            "FR-HIST-003",
            "NFR-DATA-001",
        ),
        "portability_notes": (
            "Portable scalar identifiers, UTC instants and closed "
            "canonical JSON; M07-local foreign keys only",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_alert_rows_on_initial_install",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m07_owned_tables",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": "preserve_failed_database_and_restore_verified_backup_or_forward_fix",
        "reviewer": "M07-PLAN-DB-security-review",
        "schema_range": ("v1_0701", "v1_0701", "v1_0701", "v1_0701", "v1_0701"),
        "tables": (
            "alert_alert",
            "alert_event",
            "alert_evidence_reference",
            "alert_event_receipt",
            "alert_stream_checkpoint",
            "alert_command_receipt",
        ),
    }
)


def _text(name: str, *, nullable: bool = False, size: int = 128):
    return sa.Column(name, sa.String(size), nullable=nullable)


def _integer(name: str, *, nullable: bool = False):
    return sa.Column(name, sa.Integer(), nullable=nullable)


def _json(name: str):
    return sa.Column(name, sa.Text(), nullable=False)


def _utc(name: str, *, nullable: bool = False):
    condition = (
        f"length({name})=27 AND substr({name},27,1)='Z' "
        f"AND julianday({name}) IS NOT NULL "
        f"AND date(substr({name},1,10),'+0 days')=substr({name},1,10)"
    )
    if nullable:
        condition = f"{name} IS NULL OR ({condition})"
    return sa.CheckConstraint(condition, name=f"ck_{name}_utc")


def _object(name: str):
    return sa.CheckConstraint(
        f"json_valid({name})=1 AND json_type({name})='object'",
        name=f"ck_{name}_object",
    )


def upgrade() -> None:
    op.create_table(
        "alert_alert",
        sa.Column("alert_id", sa.String(64), primary_key=True),
        _integer("fingerprint_version"),
        _text("fingerprint_digest", size=64),
        _json("fingerprint_material_json"),
        _text("condition_type", size=40),
        _text("subject_kind", size=24),
        _text("subject_id", size=64),
        _text("dimension_kind", size=64),
        _text("dimension_id"),
        _text("account_id", nullable=True, size=64),
        _text("provider_key", nullable=True, size=64),
        _text("organization_id", nullable=True, size=64),
        _integer("registry_revision"),
        _json("rule_snapshot_json"),
        _text("severity", size=16),
        _text("lifecycle", size=32),
        _integer("occurrence_generation"),
        _integer("occurrence_count"),
        _integer("record_version"),
        _integer("notification_revision"),
        _integer("aggregate_sequence"),
        _text("opened_at", size=40),
        _text("last_seen_at", size=40),
        _text("recovered_at", nullable=True, size=40),
        _text("closed_at", nullable=True, size=40),
        _text("latest_notification_at", size=40),
        _integer("unread"),
        _text("acknowledged_at", nullable=True, size=40),
        _text("acknowledged_by", nullable=True, size=64),
        _text("snoozed_until", nullable=True, size=40),
        _integer("deadline_generation"),
        _json("decision_json"),
        sa.UniqueConstraint(
            "fingerprint_version", "fingerprint_digest", name="uq_alert_fingerprint"
        ),
        sa.CheckConstraint(
            "fingerprint_version=1 AND length(fingerprint_digest)=64 AND registry_revision>=0 AND occurrence_generation>0 AND occurrence_count>0 AND record_version>0 AND notification_revision>0 AND aggregate_sequence>0 AND deadline_generation>=0 AND unread IN (0,1)",
            name="ck_alert_versions",
        ),
        sa.CheckConstraint(
            "severity IN ('information','warning','critical') AND lifecycle IN ('open','recovered','closed_by_configuration')",
            name="ck_alert_state",
        ),
        sa.CheckConstraint(
            "condition_type IN ('capacity_remaining','capacity_exhausted','capacity_unavailable','forecasted_exhaustion','authentication_attention','data_stale','collector_failure','possible_stall')",
            name="ck_alert_condition",
        ),
        sa.CheckConstraint(
            "subject_kind IN ('account','resource','profile','collector','session')",
            name="ck_alert_subject",
        ),
        sa.CheckConstraint(
            "(acknowledged_at IS NULL)=(acknowledged_by IS NULL) AND (snoozed_until IS NULL OR lifecycle='open')",
            name="ck_alert_user_state",
        ),
        sa.CheckConstraint(
            "(lifecycle='open' AND recovered_at IS NULL AND closed_at IS NULL) OR (lifecycle='recovered' AND recovered_at IS NOT NULL AND closed_at IS NULL) OR (lifecycle='closed_by_configuration' AND recovered_at IS NULL AND closed_at IS NOT NULL)",
            name="ck_alert_terminal",
        ),
        _object("fingerprint_material_json"),
        _object("rule_snapshot_json"),
        _object("decision_json"),
        *[
            _utc(name)
            for name in ("opened_at", "last_seen_at", "latest_notification_at")
        ],
        *[
            _utc(name, nullable=True)
            for name in (
                "recovered_at",
                "closed_at",
                "acknowledged_at",
                "snoozed_until",
            )
        ],
        sa.CheckConstraint(
            "last_seen_at>=opened_at AND latest_notification_at>=opened_at AND (recovered_at IS NULL OR recovered_at>=opened_at) AND (closed_at IS NULL OR closed_at>=opened_at)",
            name="ck_alert_time_order",
        ),
    )
    op.create_index(
        "ix_alert_notifications",
        "alert_alert",
        ["lifecycle", "severity", "latest_notification_at", "alert_id"],
    )
    op.create_index(
        "ix_alert_subject", "alert_alert", ["subject_kind", "subject_id", "lifecycle"]
    )
    op.create_index(
        "ix_alert_scope",
        "alert_alert",
        ["account_id", "provider_key", "organization_id", "lifecycle"],
    )
    op.create_index(
        "ix_alert_unread_snooze", "alert_alert", ["unread", "snoozed_until"]
    )
    op.create_index(
        "ix_alert_terminal_retention",
        "alert_alert",
        ["lifecycle", "recovered_at", "closed_at"],
    )
    op.create_table(
        "alert_event",
        sa.Column("event_id", sa.String(64), primary_key=True),
        _text("alert_id", size=64),
        _integer("aggregate_sequence"),
        _text("transition", size=32),
        _text("previous_lifecycle", nullable=True, size=32),
        _text("current_lifecycle", size=32),
        _text("previous_severity", nullable=True, size=16),
        _text("current_severity", size=16),
        _text("actor_id", nullable=True, size=64),
        _text("reason_code"),
        _text("source_event_id", nullable=True, size=128),
        _text("command_id", nullable=True, size=128),
        _text("occurred_at", size=40),
        sa.ForeignKeyConstraint(["alert_id"], ["alert_alert.alert_id"]),
        sa.UniqueConstraint(
            "alert_id", "aggregate_sequence", name="uq_alert_event_sequence"
        ),
        sa.CheckConstraint("aggregate_sequence>0", name="ck_alert_event_sequence"),
        sa.CheckConstraint(
            "transition IN ('opened','repeated','escalated','deescalated','recovered','reopened','closed_by_configuration','marked_read','acknowledged','snoozed','unsnoozed','snooze_expired')",
            name="ck_alert_event_transition",
        ),
        _utc("occurred_at"),
    )
    op.create_index(
        "ix_alert_event_history", "alert_event", ["alert_id", "aggregate_sequence"]
    )
    op.create_table(
        "alert_evidence_reference",
        sa.Column("reference_id", sa.String(64), primary_key=True),
        _text("alert_id", size=64),
        _integer("aggregate_sequence"),
        _text("producer_key", size=64),
        _text("event_id", size=128),
        _text("reference_kind", size=24),
        _text("source_reference_id"),
        _text("condition_stream_key"),
        _integer("source_generation"),
        _text("reason_code"),
        _text("recorded_at", size=40),
        sa.ForeignKeyConstraint(
            ["alert_id", "aggregate_sequence"],
            ["alert_event.alert_id", "alert_event.aggregate_sequence"],
        ),
        sa.CheckConstraint(
            "source_generation>0 AND aggregate_sequence>0 AND reference_kind IN ('event','observation','evidence')",
            name="ck_alert_evidence_reference",
        ),
        _utc("recorded_at"),
    )
    op.create_index(
        "ix_alert_evidence_alert",
        "alert_evidence_reference",
        ["alert_id", "aggregate_sequence"],
    )
    op.create_table(
        "alert_event_receipt",
        sa.Column("receipt_id", sa.String(64), primary_key=True),
        _text("producer_key", size=64),
        _text("event_id", size=128),
        _text("payload_digest", size=64),
        _text("condition_stream_key"),
        _integer("source_generation"),
        _text("disposition", size=24),
        _json("alert_ids_json"),
        _text("processed_at", size=40),
        sa.UniqueConstraint("producer_key", "event_id", name="uq_alert_event_receipt"),
        sa.CheckConstraint(
            "length(payload_digest)=64 AND source_generation>0 AND disposition IN ('applied','duplicate','stale_ignored','not_evaluable','rejected') AND json_valid(alert_ids_json)=1 AND json_type(alert_ids_json)='array'",
            name="ck_alert_event_receipt",
        ),
        _utc("processed_at"),
    )
    op.create_index(
        "ix_alert_receipt_stream",
        "alert_event_receipt",
        ["producer_key", "condition_stream_key", "source_generation"],
    )
    op.create_table(
        "alert_stream_checkpoint",
        _text("producer_key", size=64),
        _text("condition_stream_key"),
        _integer("source_generation"),
        _integer("evaluable_generation", nullable=True),
        _text("current_event_id", nullable=True, size=128),
        _text("last_event_id", size=128),
        _text("last_payload_digest", size=64),
        _integer("registry_revision"),
        _json("rule_evaluation_json"),
        _text("updated_at", size=40),
        sa.PrimaryKeyConstraint("producer_key", "condition_stream_key"),
        sa.CheckConstraint(
            "source_generation>0 AND registry_revision>=0 AND length(last_payload_digest)=64 AND (evaluable_generation IS NULL OR (evaluable_generation>0 AND evaluable_generation<=source_generation))",
            name="ck_alert_checkpoint",
        ),
        _object("rule_evaluation_json"),
        _utc("updated_at"),
    )
    op.create_table(
        "alert_command_receipt",
        sa.Column("receipt_id", sa.String(64), primary_key=True),
        _text("principal_id", size=128),
        _text("command_id", size=128),
        _text("request_digest", size=64),
        _text("command_kind", size=40),
        _text("subject_id", size=64),
        _integer("result_record_version"),
        _json("result_json"),
        _text("created_at", size=40),
        _text("expires_at", size=40),
        sa.UniqueConstraint(
            "principal_id", "command_id", name="uq_alert_command_receipt"
        ),
        sa.CheckConstraint(
            "length(request_digest)=64 AND result_record_version>0",
            name="ck_alert_command_receipt",
        ),
        _object("result_json"),
        _utc("created_at"),
        _utc("expires_at"),
        sa.CheckConstraint(
            "expires_at>created_at", name="ck_alert_command_receipt_time"
        ),
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

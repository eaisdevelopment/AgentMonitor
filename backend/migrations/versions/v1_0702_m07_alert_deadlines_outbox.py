"""M07 additive v1_0702; no telemetry or builtin policy rows."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0702"
down_revision = "v1_0701"
branch_labels = None
depends_on = None

TABLES = (
    "alert_deadline",
    "alert_reevaluation_job",
    "alert_event_outbox",
    "alert_retention_run",
)

METADATA = MappingProxyType(
    {
        "revision": "v1_0702",
        "parent_revision": "v1_0701",
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
        "schema_range": ("v1_0702", "v1_0702", "v1_0702", "v1_0702", "v1_0702"),
        "tables": (
            "alert_deadline",
            "alert_reevaluation_job",
            "alert_event_outbox",
            "alert_retention_run",
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
        "alert_deadline",
        sa.Column("deadline_id", sa.String(64), primary_key=True),
        _text("alert_id", size=64),
        _text("kind", size=24),
        _integer("deadline_generation"),
        _text("due_at", size=40),
        _text("state", size=24),
        _text("lease_owner", nullable=True, size=64),
        _integer("fence"),
        _text("lease_until", nullable=True, size=40),
        _text("completed_at", nullable=True, size=40),
        _text("receipt_id", nullable=True, size=64),
        sa.ForeignKeyConstraint(["alert_id"], ["alert_alert.alert_id"]),
        sa.UniqueConstraint(
            "alert_id",
            "kind",
            "deadline_generation",
            name="uq_alert_deadline_generation",
        ),
        sa.CheckConstraint(
            "kind='snooze_expiry' AND deadline_generation>0 AND fence>=0 AND state IN ('pending','claimed','completed','cancelled') AND (lease_owner IS NULL)=(lease_until IS NULL)",
            name="ck_alert_deadline",
        ),
        _utc("due_at"),
        _utc("lease_until", nullable=True),
        _utc("completed_at", nullable=True),
    )
    op.create_index(
        "ix_alert_deadline_due", "alert_deadline", ["state", "due_at", "deadline_id"]
    )
    op.create_table(
        "alert_reevaluation_job",
        sa.Column("job_id", sa.String(64), primary_key=True),
        _text("cause_kind", size=24),
        _text("cause_id", size=128),
        _integer("cause_revision"),
        _text("scope_kind", size=24),
        _text("scope_key"),
        _text("cursor", nullable=True, size=128),
        _json("checkpoint_json"),
        _text("state", size=24),
        _text("lease_owner", nullable=True, size=64),
        _integer("fence"),
        _integer("attempt_count"),
        _text("lease_until", nullable=True, size=40),
        _text("next_due_at", size=40),
        _text("safe_code", nullable=True, size=128),
        _text("created_at", size=40),
        _text("completed_at", nullable=True, size=40),
        sa.UniqueConstraint(
            "cause_kind",
            "cause_id",
            "cause_revision",
            "scope_kind",
            "scope_key",
            name="uq_alert_reevaluation_cause",
        ),
        sa.CheckConstraint(
            "cause_revision>0 AND fence>=0 AND attempt_count>=0 AND cause_kind IN ('rule','registry') AND state IN ('pending','claimed','completed','failed') AND (lease_owner IS NULL)=(lease_until IS NULL)",
            name="ck_alert_reevaluation",
        ),
        _object("checkpoint_json"),
        _utc("next_due_at"),
        _utc("created_at"),
        _utc("lease_until", nullable=True),
        _utc("completed_at", nullable=True),
    )
    op.create_index(
        "ix_alert_reevaluation_due",
        "alert_reevaluation_job",
        ["state", "next_due_at", "job_id"],
    )
    op.create_table(
        "alert_event_outbox",
        sa.Column("event_id", sa.String(64), primary_key=True),
        _text("event_type", size=64),
        _integer("event_schema_major"),
        _text("stream_key", size=128),
        _integer("stream_sequence"),
        _text("subject_id", size=64),
        _json("envelope_json"),
        _json("payload_json"),
        _text("payload_digest", size=64),
        _text("occurred_at", size=40),
        _text("recorded_at", size=40),
        _text("available_at", size=40),
        _text("delivery_state", size=24),
        _integer("attempt_count"),
        _integer("fence"),
        _text("lease_owner", nullable=True, size=64),
        _text("lease_until", nullable=True, size=40),
        _text("delivered_at", nullable=True, size=40),
        sa.UniqueConstraint(
            "stream_key", "stream_sequence", name="uq_alert_outbox_stream"
        ),
        sa.CheckConstraint(
            "event_schema_major=1 AND stream_sequence>0 AND length(payload_digest)=64 AND attempt_count>=0 AND fence>=0 AND delivery_state IN ('pending','claimed','delivered') AND (lease_owner IS NULL)=(lease_until IS NULL)",
            name="ck_alert_outbox",
        ),
        _object("envelope_json"),
        _object("payload_json"),
        _utc("occurred_at"),
        _utc("recorded_at"),
        _utc("available_at"),
        _utc("lease_until", nullable=True),
        _utc("delivered_at", nullable=True),
        sa.CheckConstraint(
            "recorded_at>=occurred_at AND available_at>=recorded_at",
            name="ck_alert_outbox_times",
        ),
    )
    op.create_index(
        "ix_alert_outbox_available",
        "alert_event_outbox",
        ["delivery_state", "available_at", "stream_key", "stream_sequence"],
    )
    op.create_table(
        "alert_retention_run",
        sa.Column("job_id", sa.String(64), primary_key=True),
        _text("as_of", size=40),
        _text("cutoff_at", size=40),
        _integer("examined_count"),
        _integer("deleted_alert_count"),
        _integer("deleted_history_count"),
        _integer("has_more"),
        _text("state", size=24),
        _text("safe_code", nullable=True),
        _text("started_at", size=40),
        _text("completed_at", nullable=True, size=40),
        sa.CheckConstraint(
            "examined_count>=0 AND deleted_alert_count>=0 AND deleted_history_count>=0 AND has_more IN (0,1) AND state IN ('running','completed','failed')",
            name="ck_alert_retention",
        ),
        _utc("as_of"),
        _utc("cutoff_at"),
        _utc("started_at"),
        _utc("completed_at", nullable=True),
        sa.CheckConstraint("cutoff_at<as_of", name="ck_alert_retention_cutoff"),
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

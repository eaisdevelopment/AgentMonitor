"""M04 ordered current collector conditions; staged for root publication."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0706"
down_revision = "v1_0705"
branch_labels = None
depends_on = None
TABLES = ("collection_alert_condition", "collection_run", "collection_event_delivery")
TRIGGERS = (
    "tr_collection_delivery_proof_insert",
    "tr_collection_delivery_proof_update",
)
METADATA = MappingProxyType(
    {
        "revision": "v1_0706",
        "parent_revision": "v1_0705",
        "owner": "M04",
        "plan_id": "PLAN-M04",
        "requirement_ids": (
            "FR-COL-003",
            "FR-COL-005",
            "FR-COL-006",
            "FR-COL-008",
            "FR-ALERT-003",
            "FR-ALERT-004",
            "NFR-DATA-001",
        ),
        "schema_range": ("v1_0706", "v1_0706", "v1_0706", "v1_0706", "v1_0706"),
        "tables": (
            "collection_alert_condition",
            "collection_run",
            "collection_event_delivery",
        ),
        "portability_notes": (
            "Positive target-scoped health versions; M04-local foreign keys only",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_condition_rows_on_initial_install",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m04_collection_alert_conditions",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": "preserve_failed_database_and_restore_verified_backup_or_forward_fix",
        "reviewer": "M04-PLAN-DB-security-review",
    }
)


def upgrade() -> None:
    op.add_column("collection_run", sa.Column("provider_outcome_state", sa.String(40)))
    op.add_column(
        "collection_event_delivery", sa.Column("consumer_receipt_id", sa.String(64))
    )
    op.add_column(
        "collection_event_delivery", sa.Column("ack_payload_digest", sa.String(64))
    )
    connection = op.get_bind()
    invalid = connection.exec_driver_sql(
        "SELECT 1 FROM collection_event_delivery WHERE NOT ("
        "COALESCE(CASE WHEN consumer_receipt_id IS NULL "
        "THEN ack_payload_digest IS NULL "
        "ELSE ack_payload_digest IS NOT NULL "
        "AND length(consumer_receipt_id) BETWEEN 1 AND 64 "
        "AND consumer_receipt_id NOT GLOB '*[^A-Za-z0-9_.:-]*' "
        "AND length(ack_payload_digest)=64 "
        "AND ack_payload_digest NOT GLOB '*[^0-9a-f]*' "
        "END,0)=1) LIMIT 1"
    ).scalar_one_or_none()
    if invalid is not None:
        raise ValueError("collection_delivery_proof_preflight_failed")
    proof_valid = (
        "COALESCE(CASE WHEN NEW.consumer_receipt_id IS NULL "
        "THEN NEW.ack_payload_digest IS NULL "
        "ELSE NEW.ack_payload_digest IS NOT NULL "
        "AND length(NEW.consumer_receipt_id) BETWEEN 1 AND 64 "
        "AND NEW.consumer_receipt_id NOT GLOB '*[^A-Za-z0-9_.:-]*' "
        "AND length(NEW.ack_payload_digest)=64 "
        "AND NEW.ack_payload_digest NOT GLOB '*[^0-9a-f]*' "
        "END,0)=1"
    )
    for operation in ("INSERT", "UPDATE"):
        connection.exec_driver_sql(
            "CREATE TRIGGER tr_collection_delivery_proof_"
            + operation.lower()
            + " BEFORE "
            + operation
            + " ON collection_event_delivery WHEN NOT ("
            + proof_valid
            + ") BEGIN SELECT RAISE(ABORT,'collection_delivery_proof_invalid'); END"
        )
    op.create_table(
        "collection_alert_condition",
        sa.Column("schedule_id", sa.String(64), primary_key=True),
        sa.Column("account_id", sa.String(64)),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("capability_id", sa.String(128), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("source_schedule_record_version", sa.Integer(), nullable=False),
        sa.Column("source_latest_run_record_version", sa.Integer()),
        sa.Column("health_state", sa.String(24), nullable=False),
        sa.Column("freshness_state", sa.String(24), nullable=False),
        sa.Column("retry_category", sa.String(32), nullable=False),
        sa.Column("latest_run_id", sa.String(64)),
        sa.Column("last_successful_at", sa.String(40)),
        sa.Column("freshness_deadline", sa.String(40)),
        sa.Column("not_before_at", sa.String(40)),
        sa.Column("evaluated_at", sa.String(40), nullable=False),
        sa.Column("reason_code", sa.String(64), nullable=False),
        sa.Column("condition_digest", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(["schedule_id"], ["collection_schedule.schedule_id"]),
        sa.ForeignKeyConstraint(["latest_run_id"], ["collection_run.run_id"]),
        sa.CheckConstraint(
            "record_version > 0 AND source_schedule_record_version > 0 AND (source_latest_run_record_version IS NULL OR source_latest_run_record_version > 0)",
            name="ck_collection_alert_versions",
        ),
        sa.CheckConstraint(
            "health_state IN ('healthy','degraded','failed','blocked','backoff','unsupported','paused','unknown')",
            name="ck_collection_alert_health",
        ),
        sa.CheckConstraint(
            "freshness_state IN ('current','stale','unknown','unsupported','not_applicable')",
            name="ck_collection_alert_freshness",
        ),
        sa.CheckConstraint(
            "retry_category IN ('none','rate_backoff','transient_backoff','authentication','authorization','user_action','compatibility','unknown_constraints','unsupported','cancelled','unclassified')",
            name="ck_collection_alert_retry",
        ),
        sa.CheckConstraint(
            "(last_successful_at IS NULL) = (freshness_deadline IS NULL)",
            name="ck_collection_alert_success_pair",
        ),
    )
    op.create_index(
        "ix_collection_alert_subject",
        "collection_alert_condition",
        ["provider_key", "account_id", "schedule_id"],
    )
    op.create_index(
        "ix_collection_alert_freshness",
        "collection_alert_condition",
        ["freshness_deadline", "schedule_id"],
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

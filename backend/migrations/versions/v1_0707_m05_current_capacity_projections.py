"""M05 durable current forecasts and independent availability; staged for root pin."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0707"
down_revision = "v1_0706"
branch_labels = None
depends_on = None
TABLES = (
    "capacity_forecast_projection",
    "capacity_event_outbox",
    "capacity_availability_current",
)
TRIGGERS = (
    "tr_capacity_forecast_snapshot_insert",
    "tr_capacity_forecast_snapshot_update",
    "tr_capacity_projection_event_insert",
    "tr_capacity_projection_event_update",
)
METADATA = MappingProxyType(
    {
        "revision": "v1_0707",
        "parent_revision": "v1_0706",
        "owner": "M05",
        "plan_id": "PLAN-M05",
        "requirement_ids": (
            "FR-QUOTA-005",
            "FR-QUOTA-006",
            "FR-COL-008",
            "FR-ALERT-001",
            "FR-ALERT-004",
            "NFR-DATA-001",
        ),
        "schema_range": ("v1_0707", "v1_0707", "v1_0707", "v1_0707", "v1_0707"),
        "tables": (
            "capacity_forecast_projection",
            "capacity_event_outbox",
            "capacity_availability_current",
        ),
        "portability_notes": (
            "Additive nullable current forecast fields preserve legacy unknown rows",
            "Independent source stream key preserves capability/auth/collector truth",
            "SQLite guards new pairs without rebuilding old tables",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "preserve_existing;zero_availability_rows",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m05_durable_current_forecast_availability",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": (
            "preserve_failed_database_and_restore_verified_backup_or_forward_fix"
        ),
        "reviewer": "root-M05-PLAN-DB-security-review",
    }
)


def _guard(name: str, table: str, validity: str, operation: str) -> None:
    op.get_bind().exec_driver_sql(
        "CREATE TRIGGER "
        + name
        + " BEFORE "
        + operation
        + " ON "
        + table
        + " WHEN NOT ("
        + validity
        + ") BEGIN SELECT RAISE(ABORT,'"
        + name
        + "_invalid'); END"
    )


def upgrade() -> None:
    # Legacy forecast rows remain unqualified for the new current-read port.
    op.add_column(
        "capacity_forecast_projection", sa.Column("window_projection_id", sa.String(64))
    )
    op.add_column(
        "capacity_forecast_projection",
        sa.Column("source_projection_version", sa.Integer()),
    )
    op.add_column("capacity_forecast_projection", sa.Column("snapshot_json", sa.Text()))
    op.add_column("capacity_event_outbox", sa.Column("producer_version", sa.String(32)))

    forecast_valid = (
        "COALESCE(CASE WHEN NEW.window_projection_id IS NULL THEN "
        "NEW.source_projection_version IS NULL AND NEW.snapshot_json IS NULL "
        "ELSE length(NEW.window_projection_id) BETWEEN 1 AND 64 "
        "AND NEW.window_projection_id NOT GLOB '*[^A-Za-z0-9_-]*' "
        "AND NEW.source_projection_version > 0 "
        "AND length(NEW.snapshot_json) BETWEEN 2 AND 65536 END,0)=1"
    )
    event_valid = (
        "COALESCE(CASE WHEN NEW.event_type IN ('capacity.forecast.changed.v1',"
        "'capacity.availability.changed.v1') THEN "
        "NEW.event_schema=NEW.event_type AND "
        "length(NEW.producer_version) BETWEEN 1 AND 32 AND "
        "NEW.producer_version NOT GLOB '*[^A-Za-z0-9_.-]*' "
        "ELSE NEW.producer_version IS NULL END,0)=1"
    )
    for operation in ("INSERT", "UPDATE"):
        _guard(
            "tr_capacity_forecast_snapshot_" + operation.lower(),
            "capacity_forecast_projection",
            forecast_valid,
            operation,
        )
        _guard(
            "tr_capacity_projection_event_" + operation.lower(),
            "capacity_event_outbox",
            event_valid,
            operation,
        )

    op.create_table(
        "capacity_availability_current",
        sa.Column("stream_id", sa.String(64), primary_key=True),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=False),
        sa.Column("capability_id", sa.String(128), nullable=False),
        sa.Column("signal_kind", sa.String(24), nullable=False),
        sa.Column("source_subject_id", sa.String(64), nullable=False),
        sa.Column("source_record_id", sa.String(64), nullable=False),
        sa.Column("source_generation", sa.Integer(), nullable=False),
        sa.Column("source_contract_id", sa.String(64), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("reason_code", sa.String(128), nullable=False),
        sa.Column("observation_ids_json", sa.String(14000), nullable=False),
        sa.Column("input_digest", sa.String(64), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("source_observed_at", sa.String(40)),
        sa.Column("source_recorded_at", sa.String(40), nullable=False),
        sa.Column("evaluated_at", sa.String(40), nullable=False),
        sa.Column("freshness_deadline", sa.String(40)),
        sa.Column("active_failure_generation", sa.Integer()),
        sa.Column("recovery_of_generation", sa.Integer()),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.UniqueConstraint(
            "provider_key",
            "account_id",
            "resource_id",
            "capability_id",
            "signal_kind",
            "source_subject_id",
            name="uq_capacity_availability_stream",
        ),
        sa.CheckConstraint(
            "signal_kind IN ('authentication','collector','capability')",
            name="ck_capacity_availability_kind",
        ),
        sa.CheckConstraint(
            "state IN ('available','unavailable','blocked','reauthentication_required',"
            "'unknown','unsupported','stale','withheld_or_denied')",
            name="ck_capacity_availability_state",
        ),
        sa.CheckConstraint(
            "source_generation > 0 AND record_version > 0 AND "
            "(active_failure_generation IS NULL OR active_failure_generation > 0) AND "
            "(recovery_of_generation IS NULL OR "
            "(state='available' AND recovery_of_generation > 0 AND "
            "recovery_of_generation < record_version))",
            name="ck_capacity_availability_versions",
        ),
        sa.CheckConstraint(
            "length(input_digest)=64 AND input_digest NOT GLOB '*[^0-9a-f]*'",
            name="ck_capacity_availability_digest",
        ),
        sa.CheckConstraint(
            "length(stream_id)=64 AND stream_id NOT GLOB '*[^0-9a-f]*' AND "
            "length(observation_ids_json) BETWEEN 2 AND 14000 AND "
            "json_valid(observation_ids_json)=1",
            name="ck_capacity_availability_lineage",
        ),
        sa.CheckConstraint(
            "length(reason_code) BETWEEN 1 AND 128 AND "
            "substr(reason_code,1,1) GLOB '[a-z]' AND "
            "reason_code NOT GLOB '*[^a-z0-9_]*'",
            name="ck_capacity_availability_reason",
        ),
    )
    op.create_index(
        "ix_capacity_availability_account",
        "capacity_availability_current",
        ["account_id", "resource_id", "capability_id", "signal_kind", "stream_id"],
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

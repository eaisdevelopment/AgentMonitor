"""M05 derivation lineage and bounded forecast projections."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0503"
down_revision = "v1_0502"
branch_labels = None
depends_on = None

TABLES = (
    "capacity_derivation",
    "capacity_derivation_input",
    "capacity_forecast_projection",
)

METADATA = MappingProxyType(
    {
        "revision": "v1_0503",
        "parent_revision": "v1_0502",
        "owner": "M05",
        "plan_id": "PLAN-M05",
        "requirement_ids": (
            "FR-QUOTA-004",
            "FR-QUOTA-005",
            "FR-HIST-002",
            "NFR-DATA-001",
        ),
        "schema_range": (
            "v1_0503",
            "v1_0503",
            "v1_0503",
            "v1_0503",
            "v1_0503",
        ),
        "tables": (
            "capacity_derivation",
            "capacity_derivation_input",
            "capacity_forecast_projection",
        ),
        "portability_notes": (
            "Forecasts reference immutable measured inputs and never backfill facts",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_capacity_rows_on_initial_install",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m05_forecast_tables",
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
        "capacity_derivation",
        sa.Column("derivation_id", sa.String(64), primary_key=True),
        sa.Column("derivation_kind", sa.String(40), nullable=False),
        sa.Column("method_id", sa.String(64), nullable=False),
        sa.Column("method_version", sa.String(32), nullable=False),
        sa.Column("input_set_digest", sa.String(64), nullable=False),
        sa.Column("result_type", sa.String(32), nullable=False),
        sa.Column("result_coefficient", sa.String(80)),
        sa.Column("result_scale", sa.Integer()),
        sa.Column("result_unit", sa.String(64)),
        sa.Column("time_basis", sa.String(64)),
        sa.Column("precision", sa.String(24), nullable=False),
        sa.Column("confidence", sa.String(24), nullable=False),
        sa.Column("uncertainty", sa.String(32), nullable=False),
        sa.Column("reason_code", sa.String(128)),
        sa.Column("policy_generation", sa.Integer(), nullable=False),
        sa.Column("schema_generation", sa.Integer(), nullable=False),
        sa.Column("source_generation", sa.Integer(), nullable=False),
        sa.Column("explanation_codes_json", sa.String(2048), nullable=False),
        sa.Column("derived_at", sa.String(40), nullable=False),
        sa.Column("valid_until", sa.String(40)),
        sa.Column("invalidated_at", sa.String(40)),
        sa.Column("invalidation_reason", sa.String(128)),
        sa.UniqueConstraint(
            "derivation_kind",
            "method_id",
            "method_version",
            "input_set_digest",
            name="uq_capacity_derivation_input_set",
        ),
        sa.CheckConstraint(
            "length(input_set_digest) = 64", name="ck_capacity_derivation_digest"
        ),
        sa.CheckConstraint(
            "policy_generation > 0 AND schema_generation > 0 AND "
            "source_generation > 0",
            name="ck_capacity_derivation_generations",
        ),
        sa.CheckConstraint(
            "derivation_kind IN ('remaining_ratio','available_spend',"
            "'health_classification','capacity_aggregate','burn_rate',"
            "'exhaustion_forecast','freshness_classification')",
            name="ck_capacity_derivation_kind",
        ),
    )
    op.create_table(
        "capacity_derivation_input",
        sa.Column("derivation_id", sa.String(64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("input_kind", sa.String(32), nullable=False),
        sa.Column("input_role", sa.String(64), nullable=False),
        sa.Column("input_id", sa.String(64), nullable=False),
        sa.Column("input_version", sa.Integer(), nullable=False),
        sa.Column("input_digest", sa.String(64), nullable=False),
        sa.Column("semantic_time", sa.String(40)),
        sa.ForeignKeyConstraint(
            ["derivation_id"], ["capacity_derivation.derivation_id"]
        ),
        sa.PrimaryKeyConstraint("derivation_id", "ordinal"),
        sa.UniqueConstraint(
            "derivation_id", "input_id", name="uq_capacity_derivation_input"
        ),
        sa.CheckConstraint("ordinal >= 0", name="ck_capacity_derivation_ordinal"),
        sa.CheckConstraint(
            "input_kind IN ('quota_observation','budget_observation','usage_bucket',"
            "'projection','availability_event')",
            name="ck_capacity_derivation_input_kind",
        ),
        sa.CheckConstraint(
            "length(input_digest) = 64", name="ck_capacity_derivation_input_digest"
        ),
        sa.CheckConstraint(
            "input_version > 0", name="ck_capacity_derivation_input_version"
        ),
    )
    op.create_table(
        "capacity_forecast_projection",
        sa.Column("forecast_id", sa.String(64), primary_key=True),
        sa.Column("forecast_key", sa.String(64), nullable=False, unique=True),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=False),
        sa.Column("window_definition_id", sa.String(64)),
        sa.Column("metric_key", sa.String(64), nullable=False),
        sa.Column("forecast_state", sa.String(32), nullable=False),
        sa.Column("exhaustion_at", sa.String(40)),
        sa.Column("burn_coefficient", sa.String(80)),
        sa.Column("burn_scale", sa.Integer()),
        sa.Column("burn_unit", sa.String(64)),
        sa.Column("confidence", sa.String(24), nullable=False),
        sa.Column("reason_code", sa.String(128), nullable=False),
        sa.Column("derivation_id", sa.String(64)),
        sa.Column("previous_derivation_id", sa.String(64)),
        sa.Column("projected_at", sa.String(40), nullable=False),
        sa.Column("valid_until", sa.String(40)),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["window_definition_id"],
            ["capacity_quota_window_definition.window_definition_id"],
        ),
        sa.ForeignKeyConstraint(
            ["derivation_id"], ["capacity_derivation.derivation_id"]
        ),
        sa.ForeignKeyConstraint(
            ["previous_derivation_id"], ["capacity_derivation.derivation_id"]
        ),
        sa.CheckConstraint(
            "forecast_state IN ('available','insufficient_input','not_applicable',"
            "'stale','conflicted')",
            name="ck_capacity_forecast_state",
        ),
        sa.CheckConstraint(
            "((forecast_state = 'available' AND exhaustion_at IS NOT NULL AND "
            "burn_coefficient IS NOT NULL AND burn_scale IS NOT NULL AND "
            "burn_unit IS NOT NULL AND derivation_id IS NOT NULL) OR "
            "(forecast_state <> 'available' AND exhaustion_at IS NULL AND "
            "burn_coefficient IS NULL AND burn_scale IS NULL AND burn_unit IS NULL))",
            name="ck_capacity_forecast_value_pair",
        ),
        sa.CheckConstraint(
            "burn_scale IS NULL OR burn_scale BETWEEN 0 AND 18",
            name="ck_capacity_forecast_scale",
        ),
        sa.CheckConstraint("record_version > 0", name="ck_capacity_forecast_version"),
    )
    op.create_index(
        "ix_capacity_forecast_account",
        "capacity_forecast_projection",
        ["account_id", "forecast_state", "resource_id"],
    )
    op.create_index(
        "ix_capacity_quota_history_measured",
        "capacity_quota_observation",
        ["window_definition_id", "collected_at", "stored_at", "observation_id"],
    )
    op.create_index(
        "ix_capacity_usage_history_measured",
        "capacity_usage_bucket",
        ["resource_id", "data_through_end", "stored_at", "bucket_id"],
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

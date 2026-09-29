"""M05 additive constraint evidence and forecast precision bounds; no backfill."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0703"
down_revision = "v1_0702"
branch_labels = None
depends_on = None

TABLES = ("capacity_quota_window_definition", "capacity_forecast_projection")
METADATA = MappingProxyType(
    {
        "revision": "v1_0703",
        "parent_revision": "v1_0702",
        "owner": "M05",
        "plan_id": "PLAN-M05",
        "requirement_ids": (
            "FR-QUOTA-003",
            "FR-QUOTA-004",
            "FR-QUOTA-005",
            "NFR-DATA-001",
        ),
        "schema_range": ("v1_0703", "v1_0703", "v1_0703", "v1_0703", "v1_0703"),
        "tables": ("capacity_quota_window_definition", "capacity_forecast_projection"),
        "portability_notes": (
            "Nullable constraint evidence remains unknown for legacy observations",
            "Forecast bounds retain canonical coefficients/scales and UTC text",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "existing_capacity_definitions_and_forecasts_preserved",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m05_constraint_forecast_bounds",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": "preserve_failed_database_and_restore_verified_backup_or_forward_fix",
        "reviewer": "root-M05-PLAN-DB-security-review",
    }
)


def upgrade() -> None:
    op.add_column(
        "capacity_quota_window_definition",
        sa.Column(
            "is_constraining",
            sa.Integer(),
            sa.CheckConstraint(
                "is_constraining IS NULL OR is_constraining IN (0,1)",
                name="ck_capacity_constraint_evidence",
            ),
        ),
    )
    for name in ("earliest_exhaustion_at", "latest_exhaustion_at"):
        op.add_column("capacity_forecast_projection", sa.Column(name, sa.String(40)))
    for prefix in ("burn_lower", "burn_upper"):
        op.add_column(
            "capacity_forecast_projection",
            sa.Column(prefix + "_coefficient", sa.String(80)),
        )
        op.add_column(
            "capacity_forecast_projection",
            sa.Column(
                prefix + "_scale",
                sa.Integer(),
                sa.CheckConstraint(
                    f"({prefix}_coefficient IS NULL AND {prefix}_scale IS NULL) OR "
                    f"({prefix}_coefficient IS NOT NULL AND {prefix}_scale BETWEEN 0 AND 18)",
                    name=f"ck_capacity_{prefix}_pair",
                ),
            ),
        )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

"""M05 immutable billing coverage and signed costs; no seeded provider facts."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0732"
down_revision = "v1_0731"
branch_labels = None
depends_on = None
TABLES = ("capacity_budget_report", "capacity_budget_signed_cost_measure")
METADATA = MappingProxyType(
    {
        "revision": "v1_0732",
        "parent_revision": "v1_0731",
        "owner": "M05",
        "plan_id": "PLAN-M05",
        "requirement_ids": ("FR-BUDGET-002", "FR-BUDGET-004", "M7-A02"),
        "schema_range": ("v1_0732", "v1_0732", "v1_0732", "v1_0732", "v1_0732"),
        "tables": ("capacity_budget_report", "capacity_budget_signed_cost_measure"),
        "portability_notes": (
            "Normalized immutable report JSON contains only typed allowlisted fields",
            "Signed exact cost extends observations without changing old checks",
            "SQLite report sequence pins bounded history snapshots and is never reused",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_initial_rows_then_bounded_real_reports",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m05_budget_report_schema",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": (
            "preserve_failed_database_and_restore_verified_backup_or_forward_fix"
        ),
        "reviewer": "M05-M7-budget-reports-root-review",
    }
)


def upgrade() -> None:
    op.create_table(
        "capacity_budget_report",
        sa.Column("report_sequence", sa.Integer(), primary_key=True),
        sa.Column("report_id", sa.String(64), nullable=False, unique=True),
        sa.Column("receipt_id", sa.String(64), nullable=False, unique=True),
        sa.Column("provenance_id", sa.String(64), nullable=False),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=False),
        sa.Column("requested_start", sa.String(40), nullable=False),
        sa.Column("requested_end", sa.String(40), nullable=False),
        sa.Column("collected_at", sa.String(40), nullable=False),
        sa.Column("stored_at", sa.String(40), nullable=False),
        sa.Column("canonical_report_json", sa.Text(), nullable=False),
        sa.Column("canonical_provenance_json", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["receipt_id"], ["capacity_commit_receipt.receipt_id"]),
        sa.ForeignKeyConstraint(
            ["provenance_id"], ["capacity_observation_provenance.provenance_id"]
        ),
        sa.CheckConstraint(
            "requested_end>requested_start AND stored_at>=collected_at",
            name="ck_budget_report_time",
        ),
        sa.CheckConstraint(
            "length(CAST(canonical_report_json AS BLOB)) BETWEEN 2 AND 16777216",
            name="ck_budget_report_size",
        ),
        sa.CheckConstraint(
            "length(CAST(canonical_provenance_json AS BLOB)) BETWEEN 2 AND 65536",
            name="ck_budget_report_provenance_size",
        ),
        sqlite_autoincrement=True,
    )
    op.create_index(
        "ix_capacity_budget_report_history",
        "capacity_budget_report",
        ["account_id", "resource_id", "report_sequence"],
    )
    op.create_table(
        "capacity_budget_signed_cost_measure",
        sa.Column("observation_id", sa.String(64), primary_key=True),
        sa.Column("coefficient", sa.String(79), nullable=False),
        sa.Column("scale", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("cost_kind", sa.String(16), nullable=False),
        sa.ForeignKeyConstraint(
            ["observation_id"], ["capacity_budget_observation.observation_id"]
        ),
        sa.CheckConstraint(
            "typeof(scale)='integer' AND scale BETWEEN 0 AND 18",
            name="ck_budget_cost_scale",
        ),
        sa.CheckConstraint(
            "length(currency)=3 AND currency NOT GLOB '*[^A-Z]*'",
            name="ck_budget_cost_currency",
        ),
        sa.CheckConstraint(
            "cost_kind IN ('charge','adjustment') AND "
            "(cost_kind='adjustment' OR substr(coefficient,1,1)<>'-')",
            name="ck_budget_cost_kind",
        ),
        sa.CheckConstraint(
            "(coefficient='0' AND scale=0) OR ("
            "length(CASE WHEN substr(coefficient,1,1)='-' "
            "THEN substr(coefficient,2) ELSE coefficient END) BETWEEN 1 AND 78 AND "
            "(CASE WHEN substr(coefficient,1,1)='-' THEN substr(coefficient,2) "
            "ELSE coefficient END) GLOB '[1-9]*' AND "
            "(CASE WHEN substr(coefficient,1,1)='-' THEN substr(coefficient,2) "
            "ELSE coefficient END) NOT GLOB '*[^0-9]*' AND "
            "(scale=0 OR substr(coefficient,-1)<>'0'))",
            name="ck_budget_cost_canonical",
        ),
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

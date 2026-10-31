"""M05 idempotent commit receipts and current quota projections."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0501"
down_revision = "v1_0500"
branch_labels = None
depends_on = None

TABLES = (
    "capacity_commit_receipt",
    "capacity_commit_receipt_observation",
    "capacity_current_projection",
)

METADATA = MappingProxyType(
    {
        "revision": "v1_0501",
        "parent_revision": "v1_0500",
        "owner": "M05",
        "plan_id": "PLAN-M05",
        "requirement_ids": (
            "FR-COL-004",
            "FR-COL-008",
            "FR-QUOTA-001",
            "FR-QUOTA-004",
            "NFR-DATA-001",
        ),
        "schema_range": (
            "v1_0501",
            "v1_0501",
            "v1_0501",
            "v1_0501",
            "v1_0501",
        ),
        "tables": (
            "capacity_commit_receipt",
            "capacity_commit_receipt_observation",
            "capacity_current_projection",
        ),
        "portability_notes": (
            "Idempotency receipts bind one run generation and payload digest",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_capacity_rows_on_initial_install",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m05_receipt_projection_tables",
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
        "capacity_commit_receipt",
        sa.Column("receipt_id", sa.String(64), primary_key=True),
        sa.Column("collection_run_id", sa.String(64), nullable=False),
        sa.Column("target_generation", sa.Integer(), nullable=False),
        sa.Column("capability_id", sa.String(128), nullable=False),
        sa.Column("payload_schema", sa.String(128), nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("consumer_key", sa.String(64), nullable=False),
        sa.Column("consumer_version", sa.String(32), nullable=False),
        sa.Column("observation_set_digest", sa.String(64), nullable=False),
        sa.Column("stored_at_start", sa.String(40), nullable=False),
        sa.Column("stored_at_end", sa.String(40), nullable=False),
        sa.Column("stored_at", sa.String(40), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("conflict_state", sa.Integer(), nullable=False),
        sa.Column("conflict_reason", sa.String(128)),
        sa.Column("affected_projection_ids_json", sa.String(4096), nullable=False),
        sa.Column("projection_versions_json", sa.String(4096), nullable=False),
        sa.Column("event_ids_json", sa.String(4096), nullable=False),
        sa.Column("receipt_version", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "collection_run_id",
            "capability_id",
            name="uq_capacity_receipt_commit_key",
        ),
        sa.CheckConstraint(
            "target_generation > 0 AND receipt_version > 0",
            name="ck_capacity_receipt_versions",
        ),
        sa.CheckConstraint(
            "length(payload_digest) = 64", name="ck_capacity_receipt_digest"
        ),
        sa.CheckConstraint(
            "length(observation_set_digest) = 64",
            name="ck_capacity_receipt_observation_digest",
        ),
        sa.CheckConstraint(
            "conflict_state IN (0,1) AND ((conflict_state=0 AND "
            "conflict_reason IS NULL) OR (conflict_state=1 AND "
            "conflict_reason IS NOT NULL))",
            name="ck_capacity_receipt_conflict",
        ),
    )
    op.create_index(
        "ix_capacity_receipt_run",
        "capacity_commit_receipt",
        ["collection_run_id", "capability_id", "receipt_id"],
    )
    op.create_table(
        "capacity_commit_receipt_observation",
        sa.Column("receipt_id", sa.String(64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("observation_kind", sa.String(32), nullable=False),
        sa.Column("observation_id", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(
            ["receipt_id"], ["capacity_commit_receipt.receipt_id"]
        ),
        sa.PrimaryKeyConstraint("receipt_id", "ordinal"),
        sa.UniqueConstraint(
            "receipt_id",
            "observation_id",
            name="uq_capacity_receipt_observation",
        ),
        sa.CheckConstraint("ordinal >= 0", name="ck_capacity_receipt_ordinal"),
        sa.CheckConstraint(
            "observation_kind IN ('quota','budget','usage')",
            name="ck_capacity_receipt_observation_kind",
        ),
    )
    op.create_table(
        "capacity_current_projection",
        sa.Column("projection_id", sa.String(64), primary_key=True),
        sa.Column("projection_key", sa.String(64), nullable=False, unique=True),
        sa.Column("projection_kind", sa.String(24), nullable=False),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("installation_id", sa.String(64), nullable=False),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=False),
        sa.Column("capability_id", sa.String(128), nullable=False),
        sa.Column("window_definition_id", sa.String(64)),
        sa.Column("budget_definition_id", sa.String(64)),
        sa.Column("metric_key", sa.String(64), nullable=False),
        sa.Column("definition_version", sa.Integer(), nullable=False),
        sa.Column("current_observation_id", sa.String(64), nullable=False),
        sa.Column("collection_run_id", sa.String(64), nullable=False),
        sa.Column("target_generation", sa.Integer(), nullable=False),
        sa.Column("freshness_state", sa.String(32), nullable=False),
        sa.Column("freshness_deadline", sa.String(40)),
        sa.Column("completeness", sa.String(24), nullable=False),
        sa.Column("conflict_state", sa.String(24), nullable=False),
        sa.Column("registry_revision", sa.Integer(), nullable=False),
        sa.Column("source_generation", sa.Integer(), nullable=False),
        sa.Column("projection_policy_id", sa.String(64), nullable=False),
        sa.Column("projection_policy_version", sa.String(32), nullable=False),
        sa.Column("evaluated_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.Column("projected_at", sa.String(40), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["window_definition_id"],
            ["capacity_quota_window_definition.window_definition_id"],
        ),
        sa.ForeignKeyConstraint(
            ["budget_definition_id"],
            ["capacity_budget_definition.budget_definition_id"],
        ),
        sa.CheckConstraint(
            "definition_version > 0 AND target_generation > 0 AND "
            "registry_revision > 0 AND "
            "source_generation > 0 AND record_version > 0",
            name="ck_capacity_current_versions",
        ),
        sa.CheckConstraint(
            "freshness_state IN ('fresh','stale','freshness_unknown','conflicted')",
            name="ck_capacity_current_freshness",
        ),
        sa.CheckConstraint(
            "completeness IN ('complete','partial','unknown')",
            name="ck_capacity_current_completeness",
        ),
        sa.CheckConstraint(
            "conflict_state IN ('none','conflicted')",
            name="ck_capacity_current_conflict",
        ),
        sa.CheckConstraint(
            "(projection_kind='quota' AND window_definition_id IS NOT NULL AND "
            "budget_definition_id IS NULL) OR (projection_kind='budget' AND "
            "budget_definition_id IS NOT NULL AND window_definition_id IS NULL)",
            name="ck_capacity_current_kind",
        ),
    )
    op.create_index(
        "ix_capacity_current_freshness",
        "capacity_current_projection",
        ["freshness_state", "freshness_deadline", "projection_id"],
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

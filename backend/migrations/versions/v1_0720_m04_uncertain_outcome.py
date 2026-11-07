"""M04 explicit uncertain cloud outcomes without fabricated provider responses."""

# ruff: noqa: E501 -- immutable schema predicates remain explicit.

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0720"
down_revision = "v1_0719"
branch_labels = None
depends_on = None
TABLES = ("collection_cloud_uncertain_outcome",)
METADATA = MappingProxyType(
    {
        "revision": "v1_0720",
        "parent_revision": "v1_0719",
        "owner": "M04",
        "plan_id": "PLAN-M04",
        "requirement_ids": ("FR-COL-003", "FR-COL-007", "M6-A07", "M6-A09"),
        "schema_range": ("v1_0720", "v1_0720", "v1_0720", "v1_0720", "v1_0720"),
        "tables": ("collection_cloud_uncertain_outcome",),
        "portability_notes": (
            "Additive uncertainty receipt leaves original dispatch and response fields unchanged",
            "Known unrepresentable Retry-After remains an unreleased hold",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_rows_until_actual_uncertain_outcome",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m04_uncertain_outcome_schema",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": "preserve_failed_database_and_restore_verified_backup_or_forward_fix",
        "reviewer": "M04-M6-uncertain-outcome-review",
    }
)


def upgrade() -> None:
    op.create_table(
        "collection_cloud_uncertain_outcome",
        sa.Column("admission_id", sa.String(64), primary_key=True),
        sa.Column("reason", sa.String(40), nullable=False),
        sa.Column("recorded_at", sa.String(40), nullable=False),
        sa.Column("released_at", sa.String(40)),
        sa.Column("next_allowed_at", sa.String(40)),
        sa.Column("gate_record_version", sa.Integer()),
        sa.ForeignKeyConstraint(
            ["admission_id"], ["collection_ollama_cloud_admission.admission_id"]
        ),
        sa.CheckConstraint(
            "reason IN ('abandoned_outcome_unknown','retry_after_unrepresentable')",
            name="ck_cloud_uncertain_reason",
        ),
        sa.CheckConstraint(
            "(reason='retry_after_unrepresentable' AND released_at IS NULL AND next_allowed_at IS NULL AND gate_record_version IS NULL) OR (reason='abandoned_outcome_unknown' AND released_at IS NOT NULL AND next_allowed_at IS NOT NULL AND gate_record_version IS NOT NULL AND gate_record_version>0 AND released_at>=recorded_at AND next_allowed_at>=released_at)",
            name="ck_cloud_uncertain_shape",
        ),
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

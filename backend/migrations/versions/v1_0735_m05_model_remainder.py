"""Fence optional model grouping/remainder encodings from older readers."""

from types import MappingProxyType

revision = "v1_0735"
down_revision = "v1_0734"
branch_labels = None
depends_on = None
TABLES = ()
METADATA = MappingProxyType(
    {
        "revision": "v1_0735",
        "parent_revision": "v1_0734",
        "owner": "M05",
        "plan_id": "PLAN-M05",
        "requirement_ids": ("FR-BUDGET-001", "FR-BUDGET-003", "M7-A03", "M7-A08"),
        "schema_range": ("v1_0735", "v1_0735", "v1_0735", "v1_0735", "v1_0735"),
        "tables": (),
        "portability_notes": (
            "Semantic marker for optional model grouping and remainder fields",
            "Physical schema and retained report/request bytes remain unchanged",
            "Legacy encodings keep absent grouping and remainder defaults",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_semantic_schema_marker",
        "expected_data_volume": "no_business_row_changes",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m05_model_remainder_marker",
            "retained_financial_hashes",
            "old_reader_refuses",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": (
            "preserve_failed_database_and_restore_verified_backup_or_forward_fix"
        ),
        "reviewer": "M05-M7-model-remainder-root-review",
    }
)


def upgrade() -> None:
    """Alembic advances only its version marker; no schema or row rewrite."""


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

"""M04 durable verification initiation identity for exact replay."""

# ruff: noqa: E501 -- exact reviewed metadata remains explicit.

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0717"
down_revision = "v1_0716"
branch_labels = None
depends_on = None
TABLES = ("collection_cloud_verification_job",)
METADATA = MappingProxyType(
    {
        "revision": "v1_0717",
        "parent_revision": "v1_0716",
        "owner": "M04",
        "plan_id": "PLAN-M04",
        "requirement_ids": (
            "FR-COL-003",
            "FR-COL-005",
            "FR-COL-007",
            "M6-A07",
            "M6-A09",
            "NFR-DATA-001",
        ),
        "schema_range": (
            "v1_0717",
            "v1_0717",
            "v1_0717",
            "v1_0717",
            "v1_0717",
        ),
        "tables": ("collection_cloud_verification_job",),
        "portability_notes": (
            "New verification jobs retain the external account version as part of their durable idempotency identity",
            "Legacy jobs remain nullable and fail closed rather than being assigned an invented request version",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "one nullable bounded integer per verification request",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m04_cloud_verification_replay_schema",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": "preserve_failed_database_and_restore_verified_backup_or_forward_fix",
        "reviewer": "pending-M04-independent-review",
    }
)


def upgrade() -> None:
    op.add_column(
        "collection_cloud_verification_job",
        sa.Column(
            "expected_account_record_version",
            sa.Integer(),
            sa.CheckConstraint(
                "expected_account_record_version IS NULL "
                "OR expected_account_record_version > 0",
                name="ck_collection_cloud_verification_request_version",
            ),
            nullable=True,
        ),
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

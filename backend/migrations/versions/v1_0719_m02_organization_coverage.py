"""M02 owner-asserted organization coverage and immutable revision history."""

# ruff: noqa: E501 -- immutable schema predicates remain explicit.

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0719"
down_revision = "v1_0718"
branch_labels = None
depends_on = None
TABLES = (
    "reg_organization_provider_coverage",
    "reg_organization_provider_coverage_revision",
)
METADATA = MappingProxyType(
    {
        "revision": "v1_0719",
        "parent_revision": "v1_0718",
        "owner": "M02",
        "plan_id": "PLAN-M02",
        "requirement_ids": (
            "FR-ACC-001",
            "FR-ACC-002",
            "FR-ACC-004",
            "FR-ACC-006",
            "FR-ORG-001",
            "FR-SAFE-001",
            "FR-SAFE-002",
            "M6-A03",
            "M6-A04",
            "M6-A05",
            "M6-A09",
            "NFR-DATA-001",
        ),
        "schema_range": ("v1_0719", "v1_0719", "v1_0719", "v1_0719", "v1_0719"),
        "tables": (
            "reg_organization_provider_coverage",
            "reg_organization_provider_coverage_revision",
        ),
        "portability_notes": (
            "Owner assertions contain only M02 references and closed disposition metadata",
            "Immutable revisions retain source organization fences without mutable source foreign keys",
            "Existing accounts and telemetry are unchanged and no coverage is inferred",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_coverage_rows_until_explicit_owner_action",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m02_organization_coverage_schema",
            "m02_coverage_revision_immutable",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": "preserve_failed_database_and_restore_verified_backup_or_forward_fix",
        "reviewer": "M02-M6-organization-coverage-independent-review",
    }
)


def _columns() -> list[sa.Column]:
    return [
        sa.Column("coverage_id", sa.String(64), nullable=False),
        sa.Column("organization_id", sa.String(64), nullable=False),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("account_id", sa.String(64)),
        sa.Column("account_organization_id", sa.String(64)),
        sa.Column("unavailable_reason", sa.String(32)),
        sa.Column("provenance", sa.String(16), nullable=False),
        sa.Column("confirmed_by", sa.String(64), nullable=False),
        sa.Column("confirmed_at", sa.String(27), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("registry_revision", sa.Integer(), nullable=False),
        sa.Column("invalidated_at", sa.String(27)),
        sa.Column("invalidation_reason", sa.String(40)),
    ]


def _checks(stem: str) -> list[sa.CheckConstraint]:
    return [
        sa.CheckConstraint(
            "length(coverage_id) BETWEEN 1 AND 64 AND coverage_id NOT GLOB '*[^A-Za-z0-9_-]*' AND length(confirmed_by) BETWEEN 1 AND 64 AND confirmed_by NOT GLOB '*[^A-Za-z0-9_-]*'",
            name=f"ck_{stem}_ids",
        ),
        sa.CheckConstraint(
            "length(organization_id) BETWEEN 1 AND 64 AND organization_id NOT GLOB '*[^A-Za-z0-9_-]*' AND length(provider_key) BETWEEN 1 AND 64 AND provider_key NOT GLOB '*[^A-Za-z0-9_-]*'",
            name=f"ck_{stem}_key",
        ),
        sa.CheckConstraint(
            "(account_id IS NULL OR (length(account_id) BETWEEN 1 AND 64 AND account_id NOT GLOB '*[^A-Za-z0-9_-]*')) AND (account_organization_id IS NULL OR (length(account_organization_id) BETWEEN 1 AND 64 AND account_organization_id NOT GLOB '*[^A-Za-z0-9_-]*'))",
            name=f"ck_{stem}_source_ids",
        ),
        sa.CheckConstraint(
            "provenance='owner_asserted'",
            name=f"ck_{stem}_provenance",
        ),
        sa.CheckConstraint(
            "typeof(record_version)='integer' AND record_version>0 AND typeof(registry_revision)='integer' AND registry_revision>0",
            name=f"ck_{stem}_versions",
        ),
        sa.CheckConstraint(
            "(outcome='unavailable' AND account_id IS NULL AND account_organization_id IS NULL AND unavailable_reason IS NOT NULL AND unavailable_reason IN ('account_unavailable','subscription_unavailable','access_unavailable','owner_unavailable')) OR (outcome IN ('account','shared') AND account_id IS NOT NULL AND account_organization_id IS NOT NULL AND unavailable_reason IS NULL AND ((outcome='account' AND account_organization_id=organization_id) OR (outcome='shared' AND account_organization_id<>organization_id)))",
            name=f"ck_{stem}_shape",
        ),
        sa.CheckConstraint(
            "length(confirmed_at)=27 AND confirmed_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]Z' AND julianday(confirmed_at) IS NOT NULL",
            name=f"ck_{stem}_confirmed_at",
        ),
        sa.CheckConstraint(
            "(invalidated_at IS NULL AND invalidation_reason IS NULL) OR (invalidated_at IS NOT NULL AND invalidation_reason IS NOT NULL AND invalidation_reason IN ('owner_revoked','account_archived','account_reassigned','organization_archived','source_organization_archived','provider_withdrawn') AND length(invalidated_at)=27 AND invalidated_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]Z' AND julianday(invalidated_at) IS NOT NULL AND invalidated_at>=confirmed_at)",
            name=f"ck_{stem}_invalidation",
        ),
    ]


def upgrade() -> None:
    current, history = TABLES
    op.create_table(
        current,
        *_columns(),
        sa.PrimaryKeyConstraint("coverage_id"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["reg_organization.organization_id"]
        ),
        sa.ForeignKeyConstraint(
            ["provider_key"], ["reg_provider_definition.provider_key"]
        ),
        sa.ForeignKeyConstraint(["account_id"], ["reg_account.account_id"]),
        sa.ForeignKeyConstraint(
            ["account_organization_id"], ["reg_organization.organization_id"]
        ),
        *_checks("reg_coverage"),
    )
    op.create_index(
        "uq_reg_coverage_org_provider",
        current,
        ["organization_id", "provider_key"],
        unique=True,
    )
    op.create_index(
        "ix_reg_coverage_account",
        current,
        ["account_id", "invalidated_at", "coverage_id"],
    )
    op.create_index(
        "ix_reg_coverage_source_organization",
        current,
        ["account_organization_id", "invalidated_at", "coverage_id"],
    )
    op.create_index(
        "ix_reg_coverage_provider",
        current,
        ["provider_key", "invalidated_at", "coverage_id"],
    )
    op.create_table(
        history,
        *_columns(),
        sa.PrimaryKeyConstraint("coverage_id", "record_version"),
        sa.ForeignKeyConstraint(["coverage_id"], [f"{current}.coverage_id"]),
        *_checks("reg_coverage_revision"),
    )
    for operation in ("UPDATE", "DELETE"):
        op.execute(
            f"CREATE TRIGGER tr_reg_coverage_revision_no_{operation.lower()} "
            f"BEFORE {operation} ON {history} BEGIN SELECT "
            "RAISE(ABORT,'registry_coverage_revision_immutable'); END"
        )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

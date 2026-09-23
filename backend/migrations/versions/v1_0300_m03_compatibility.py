"""M03 immutable provider compatibility history and transactional outbox."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0300"
down_revision = "v1_0204"
branch_labels = None
depends_on = None

METADATA = MappingProxyType(
    {
        "revision": "v1_0300",
        "parent_revision": "v1_0204",
        "owner": "M03",
        "plan_id": "PLAN-M03",
        "requirement_ids": (
            "FR-COL-004",
            "FR-COL-006",
            "FR-COL-007",
            "FR-COL-008",
            "NFR-COMP-001",
            "NFR-DATA-001",
            "NFR-SEC-001",
        ),
        "schema_range": (
            "v1_0300",
            "v1_0300",
            "v1_0300",
            "v1_0300",
            "v1_0300",
        ),
        "tables": (
            "provider_system_compatibility_assessment",
            "provider_system_event_outbox",
        ),
        "portability_notes": (
            "Immutable bounded compatibility facts; M03-local references only",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_provider_system_rows_on_initial_install",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m03_compatibility_tables",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": (
            "preserve_failed_database_and_restore_verified_backup_or_forward_fix"
        ),
        "reviewer": "M03-PLAN-DB-security-review",
    }
)

_UTC_TIMESTAMP_GLOB = (
    "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T"
    "[0-9][0-9]:[0-9][0-9]:[0-9][0-9]."
    "[0-9][0-9][0-9][0-9][0-9][0-9]Z"
)


def _canonical_utc(column: str) -> str:
    return (
        f"length({column}) = 27 AND {column} GLOB '{_UTC_TIMESTAMP_GLOB}' "
        f"AND julianday({column}) IS NOT NULL "
        f"AND date(substr({column}, 1, 10), '+0 days') = substr({column}, 1, 10)"
    )


def upgrade() -> None:
    op.create_table(
        "provider_system_compatibility_assessment",
        sa.Column("assessment_id", sa.String(64), primary_key=True),
        sa.Column("registration_id", sa.String(64), nullable=False),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("adapter_id", sa.String(128), nullable=False),
        sa.Column("adapter_version", sa.String(32), nullable=False),
        sa.Column("protocol_version", sa.String(32), nullable=False),
        sa.Column("installation_id", sa.String(64)),
        sa.Column("capability_id", sa.String(128), nullable=False),
        sa.Column("capability_schema_version", sa.String(32), nullable=False),
        sa.Column("source_id", sa.String(128)),
        sa.Column("provider_version_value", sa.String(64)),
        sa.Column("provider_version_state", sa.String(16), nullable=False),
        sa.Column("version_scheme", sa.String(32)),
        sa.Column("version_rule_id", sa.String(128)),
        sa.Column("compatibility_state", sa.String(32), nullable=False),
        sa.Column("reason_code", sa.String(128), nullable=False),
        sa.Column("manifest_schema_version", sa.String(32), nullable=False),
        sa.Column("manifest_fingerprint", sa.String(64), nullable=False),
        sa.Column("input_fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("assessed_at", sa.String(40), nullable=False),
        sa.Column("valid_until", sa.String(40)),
        sa.Column("supersedes_assessment_id", sa.String(64)),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("is_current", sa.Integer(), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["supersedes_assessment_id"],
            ["provider_system_compatibility_assessment.assessment_id"],
        ),
        sa.CheckConstraint(
            "provider_version_state IN ('available', 'unknown', 'unavailable')",
            name="ck_provider_system_version_state",
        ),
        sa.CheckConstraint(
            "compatibility_state IN "
            "('compatible', 'incompatible', 'unverified', 'unsupported', 'disabled')",
            name="ck_provider_system_compatibility_state",
        ),
        sa.CheckConstraint(
            "length(manifest_fingerprint) = 64 "
            "AND manifest_fingerprint NOT GLOB '*[^0-9a-f]*'",
            name="ck_provider_system_manifest_fingerprint",
        ),
        sa.CheckConstraint(
            "length(input_fingerprint) = 64 "
            "AND input_fingerprint NOT GLOB '*[^0-9a-f]*'",
            name="ck_provider_system_input_fingerprint",
        ),
        sa.CheckConstraint(
            _canonical_utc("assessed_at"),
            name="ck_provider_system_assessed_at_utc",
        ),
        sa.CheckConstraint(
            f"valid_until IS NULL OR ({_canonical_utc('valid_until')})",
            name="ck_provider_system_valid_until_utc",
        ),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until >= assessed_at",
            name="ck_provider_system_validity_order",
        ),
        sa.CheckConstraint("is_current IN (0, 1)", name="ck_provider_system_current"),
        sa.CheckConstraint(
            "record_version > 0", name="ck_provider_system_record_version"
        ),
        sa.CheckConstraint(
            "(provider_version_state = 'available' AND "
            "length(provider_version_value) BETWEEN 1 AND 64 "
            "AND version_scheme IN "
            "('opaque_exact', 'semantic_exact', 'date_exact') "
            "AND length(version_rule_id) BETWEEN 1 AND 128) OR "
            "(provider_version_state <> 'available' AND "
            "provider_version_value IS NULL AND version_scheme IS NULL "
            "AND version_rule_id IS NULL)",
            name="ck_provider_system_version_pair",
        ),
    )
    op.create_index(
        "ix_provider_system_current_assessment",
        "provider_system_compatibility_assessment",
        [
            "registration_id",
            "installation_id",
            "capability_id",
            "source_id",
        ],
        unique=True,
        sqlite_where=sa.text("is_current = 1"),
    )
    op.create_index(
        "ix_provider_system_provider_latest",
        "provider_system_compatibility_assessment",
        ["provider_key", "adapter_id", "assessed_at", "assessment_id"],
    )
    op.create_index(
        "ix_provider_system_state_latest",
        "provider_system_compatibility_assessment",
        ["compatibility_state", "assessed_at", "assessment_id"],
    )
    op.create_index(
        "ix_provider_system_retention",
        "provider_system_compatibility_assessment",
        ["is_current", "assessed_at", "assessment_id"],
    )
    op.create_table(
        "provider_system_event_outbox",
        sa.Column("event_id", sa.String(64), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("assessment_id", sa.String(64), nullable=False),
        sa.Column("registration_id", sa.String(64), nullable=False),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("capability_id", sa.String(128), nullable=False),
        sa.Column("compatibility_state", sa.String(32), nullable=False),
        sa.Column("reason_code", sa.String(128), nullable=False),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("producer_sequence", sa.Integer(), nullable=False, unique=True),
        sa.Column("occurred_at", sa.String(40), nullable=False),
        sa.Column("recorded_at", sa.String(40), nullable=False),
        sa.Column("delivery_state", sa.String(16), nullable=False),
        sa.Column("available_at", sa.String(40), nullable=False),
        sa.Column("claimed_at", sa.String(40)),
        sa.Column("delivered_at", sa.String(40)),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["provider_system_compatibility_assessment.assessment_id"],
        ),
        sa.CheckConstraint(
            "producer_sequence > 0", name="ck_provider_system_outbox_sequence"
        ),
        sa.CheckConstraint(
            "attempt_count >= 0", name="ck_provider_system_outbox_attempts"
        ),
        sa.CheckConstraint(
            "delivery_state IN ('pending', 'claimed', 'delivered')",
            name="ck_provider_system_outbox_delivery",
        ),
        sa.CheckConstraint(
            "compatibility_state IN "
            "('compatible', 'incompatible', 'unverified', 'unsupported', 'disabled')",
            name="ck_provider_system_outbox_compatibility_state",
        ),
        sa.CheckConstraint(
            _canonical_utc("occurred_at"),
            name="ck_provider_system_outbox_occurred_at_utc",
        ),
        sa.CheckConstraint(
            _canonical_utc("recorded_at"),
            name="ck_provider_system_outbox_recorded_at_utc",
        ),
        sa.CheckConstraint(
            _canonical_utc("available_at"),
            name="ck_provider_system_outbox_available_at_utc",
        ),
        sa.CheckConstraint(
            f"claimed_at IS NULL OR ({_canonical_utc('claimed_at')})",
            name="ck_provider_system_outbox_claimed_at_utc",
        ),
        sa.CheckConstraint(
            f"delivered_at IS NULL OR ({_canonical_utc('delivered_at')})",
            name="ck_provider_system_outbox_delivered_at_utc",
        ),
        sa.CheckConstraint(
            "recorded_at >= occurred_at AND available_at >= recorded_at "
            "AND (claimed_at IS NULL OR claimed_at >= available_at) "
            "AND (delivered_at IS NULL OR "
            "(claimed_at IS NOT NULL AND delivered_at >= claimed_at))",
            name="ck_provider_system_outbox_time_order",
        ),
        sa.CheckConstraint(
            "(delivery_state = 'pending' AND claimed_at IS NULL "
            "AND delivered_at IS NULL) OR "
            "(delivery_state = 'claimed' AND claimed_at IS NOT NULL "
            "AND delivered_at IS NULL AND attempt_count > 0) OR "
            "(delivery_state = 'delivered' AND claimed_at IS NOT NULL "
            "AND delivered_at IS NOT NULL AND attempt_count > 0)",
            name="ck_provider_system_outbox_state_pair",
        ),
    )
    op.create_index(
        "ix_provider_system_outbox_delivery",
        "provider_system_event_outbox",
        ["delivery_state", "available_at", "producer_sequence"],
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

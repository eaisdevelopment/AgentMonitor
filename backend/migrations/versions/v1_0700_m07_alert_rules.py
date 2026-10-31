"""M07 additive v1_0700; no telemetry or builtin policy rows."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0700"
down_revision = "v1_0603"
branch_labels = None
depends_on = None

TABLES = ("alert_rule", "alert_rule_revision")

METADATA = MappingProxyType(
    {
        "revision": "v1_0700",
        "parent_revision": "v1_0603",
        "owner": "M07",
        "plan_id": "PLAN-M07",
        "requirement_ids": (
            "FR-ALERT-001",
            "FR-ALERT-002",
            "FR-ALERT-003",
            "FR-ALERT-004",
            "FR-ALERT-005",
            "FR-HIST-001",
            "FR-HIST-002",
            "FR-HIST-003",
            "NFR-DATA-001",
        ),
        "portability_notes": (
            "Portable scalar identifiers, UTC instants and closed "
            "canonical JSON; M07-local foreign keys only",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_alert_rows_on_initial_install",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m07_owned_tables",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": "preserve_failed_database_and_restore_verified_backup_or_forward_fix",
        "reviewer": "M07-PLAN-DB-security-review",
        "schema_range": ("v1_0700", "v1_0700", "v1_0700", "v1_0700", "v1_0700"),
        "tables": ("alert_rule", "alert_rule_revision"),
    }
)


def _text(name: str, *, nullable: bool = False, size: int = 128):
    return sa.Column(name, sa.String(size), nullable=nullable)


def _integer(name: str, *, nullable: bool = False):
    return sa.Column(name, sa.Integer(), nullable=nullable)


def _json(name: str):
    return sa.Column(name, sa.Text(), nullable=False)


def _utc(name: str, *, nullable: bool = False):
    condition = (
        f"length({name})=27 AND substr({name},27,1)='Z' "
        f"AND julianday({name}) IS NOT NULL "
        f"AND date(substr({name},1,10),'+0 days')=substr({name},1,10)"
    )
    if nullable:
        condition = f"{name} IS NULL OR ({condition})"
    return sa.CheckConstraint(condition, name=f"ck_{name}_utc")


def _object(name: str):
    return sa.CheckConstraint(
        f"json_valid({name})=1 AND json_type({name})='object'",
        name=f"ck_{name}_object",
    )


def upgrade() -> None:
    op.create_table(
        "alert_rule",
        sa.Column("rule_id", sa.String(64), primary_key=True),
        _text("condition_type", size=40),
        _text("scope_kind", size=24),
        _text("scope_key"),
        _integer("enabled"),
        _integer("config_schema"),
        _json("config_json"),
        _integer("record_version"),
        _text("actor_id", size=64),
        _text("created_at", size=40),
        _text("updated_at", size=40),
        _text("archived_at", nullable=True, size=40),
        sa.CheckConstraint(
            "condition_type IN ('capacity_remaining','capacity_exhausted','capacity_unavailable','forecasted_exhaustion','authentication_attention','data_stale','collector_failure','possible_stall')",
            name="ck_alert_rule_condition",
        ),
        sa.CheckConstraint(
            "scope_kind IN ('global','organization','provider','account') AND ((scope_kind='global' AND scope_key='global') OR (scope_kind<>'global' AND scope_key<>'global' AND length(scope_key)>0))",
            name="ck_alert_rule_scope",
        ),
        sa.CheckConstraint(
            "enabled IN (0,1) AND config_schema=1 AND record_version>0",
            name="ck_alert_rule_versions",
        ),
        _object("config_json"),
        sa.CheckConstraint(
            "json_extract(config_json,'$.schema_major')=1 AND ((condition_type='capacity_remaining' AND json_type(config_json,'$.warning_remaining_basis_points')='integer' AND json_type(config_json,'$.critical_remaining_basis_points')='integer' AND json_extract(config_json,'$.critical_remaining_basis_points')>=0 AND json_extract(config_json,'$.critical_remaining_basis_points')<=json_extract(config_json,'$.warning_remaining_basis_points') AND json_extract(config_json,'$.warning_remaining_basis_points')<=10000) OR (condition_type<>'capacity_remaining' AND json_extract(config_json,'$.warning_remaining_basis_points') IS NULL AND json_extract(config_json,'$.critical_remaining_basis_points') IS NULL))",
            name="ck_alert_rule_configuration",
        ),
        _utc("created_at"),
        _utc("updated_at"),
        _utc("archived_at", nullable=True),
        sa.CheckConstraint(
            "updated_at>=created_at AND (archived_at IS NULL OR archived_at=updated_at)",
            name="ck_alert_rule_times",
        ),
    )
    op.create_index(
        "uq_alert_rule_active_scope",
        "alert_rule",
        ["condition_type", "scope_kind", "scope_key"],
        unique=True,
        sqlite_where=sa.text("archived_at IS NULL"),
    )
    op.create_index("ix_alert_rule_page", "alert_rule", ["rule_id"])
    op.create_table(
        "alert_rule_revision",
        _text("rule_id", size=64),
        _integer("record_version"),
        _text("condition_type", size=40),
        _text("scope_kind", size=24),
        _text("scope_key"),
        _integer("enabled"),
        _integer("config_schema"),
        _json("config_json"),
        _text("actor_id", size=64),
        _text("command_id", size=128),
        _text("created_at", size=40),
        _text("updated_at", size=40),
        _text("archived_at", nullable=True, size=40),
        sa.PrimaryKeyConstraint("rule_id", "record_version"),
        sa.ForeignKeyConstraint(["rule_id"], ["alert_rule.rule_id"]),
        sa.CheckConstraint(
            "record_version>0 AND enabled IN (0,1) AND config_schema=1",
            name="ck_alert_revision_versions",
        ),
        _object("config_json"),
        _utc("created_at"),
        _utc("updated_at"),
        _utc("archived_at", nullable=True),
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

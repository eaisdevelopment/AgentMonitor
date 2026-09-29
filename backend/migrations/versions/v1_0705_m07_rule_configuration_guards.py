"""M07 forward-only closed rule configuration guards; no repair or backfill."""

from types import MappingProxyType

from alembic import op

revision = "v1_0705"
down_revision = "v1_0704"
branch_labels = None
depends_on = None

TABLES = ()
TRIGGERS = (
    "tr_alert_rule_configuration_insert",
    "tr_alert_rule_configuration_update",
    "tr_alert_rule_revision_configuration_insert",
    "tr_alert_rule_revision_configuration_update",
)

METADATA = MappingProxyType(
    {
        "revision": "v1_0705",
        "parent_revision": "v1_0704",
        "owner": "M07",
        "plan_id": "PLAN-M07",
        "requirement_ids": ("FR-ALERT-001", "FR-ALERT-002", "NFR-DATA-001"),
        "schema_range": ("v1_0705", "v1_0705", "v1_0705", "v1_0705", "v1_0705"),
        "tables": (),
        "portability_notes": (
            (
                "SQLite trigger guards isolate nullable CHECK semantics; "
                "portable adapter must enforce the same closed "
                "configuration invariant"
            ),
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "bounded current rule and immutable rule revision "
        "validation; no telemetry touched",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m07_configuration_guards",
            "existing_rule_validation",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": (
            "preserve_failed_database_and_restore_verified_backup_or_forward_fix"
        ),
        "reviewer": "M07-PLAN-DB-security-review",
    }
)


_CONDITIONS = (
    "'capacity_remaining','capacity_exhausted','capacity_unavailable',"
    "'forecasted_exhaustion','authentication_attention','data_stale',"
    "'collector_failure','possible_stall'"
)


def _configuration_is_valid(prefix: str) -> str:
    condition = prefix + "condition_type"
    schema = prefix + "config_schema"
    config = prefix + "config_json"
    # CASE avoids invoking JSON functions on malformed input. COALESCE ensures
    # SQL NULL is false, never the implicit success permitted by CHECK.
    return (
        "COALESCE(CASE WHEN json_valid("
        + config
        + ")=1 THEN ("
        + schema
        + "=1 AND "
        + condition
        + " IN ("
        + _CONDITIONS
        + ") AND "
        + "json_type("
        + config
        + ")='object' AND "
        + "json_type("
        + config
        + ",'$.schema_major')='integer' AND "
        + "json_extract("
        + config
        + ",'$.schema_major')=1 AND (("
        + condition
        + "='capacity_remaining' AND "
        + "(SELECT count(*) FROM json_each("
        + config
        + "))=3 AND "
        + "json_type("
        + config
        + ",'$.warning_remaining_basis_points')='integer' AND "
        + "json_type("
        + config
        + ",'$.critical_remaining_basis_points')='integer' AND "
        + "json_extract("
        + config
        + ",'$.critical_remaining_basis_points')>=0 AND "
        + "json_extract("
        + config
        + ",'$.critical_remaining_basis_points')"
        + "<=json_extract("
        + config
        + ",'$.warning_remaining_basis_points') AND "
        + "json_extract("
        + config
        + ",'$.warning_remaining_basis_points')<=10000"
        + ") OR ("
        + condition
        + "<>'capacity_remaining' AND "
        + "(SELECT count(*) FROM json_each("
        + config
        + "))=1))) ELSE 0 END,0)=1"
    )


def upgrade() -> None:
    connection = op.get_bind()
    for table in ("alert_rule", "alert_rule_revision"):
        # Both names are a closed module-owned set; values are never displayed.
        invalid = connection.exec_driver_sql(
            "SELECT 1 FROM "
            + table
            + " WHERE NOT ("
            + _configuration_is_valid("")
            + ") LIMIT 1"
        ).scalar_one_or_none()
        if invalid is not None:
            raise ValueError("alert_rule_configuration_guard_preflight_failed")
    for table in ("alert_rule", "alert_rule_revision"):
        for operation in ("INSERT", "UPDATE"):
            name = "tr_" + table + "_configuration_" + operation.lower()
            connection.exec_driver_sql(
                "CREATE TRIGGER "
                + name
                + " BEFORE "
                + operation
                + " ON "
                + table
                + " WHEN NOT ("
                + _configuration_is_valid("NEW.")
                + ") "
                + "BEGIN SELECT RAISE(ABORT,'alert_rule_configuration_invalid'); END"
            )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

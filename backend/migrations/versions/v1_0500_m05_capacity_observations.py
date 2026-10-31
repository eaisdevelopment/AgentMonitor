"""M05 exact immutable quota, budget, usage, and provenance facts."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0500"
down_revision = "v1_0400"
branch_labels = None
depends_on = None

TABLES = (
    "capacity_resource_policy",
    "capacity_quota_window_definition",
    "capacity_budget_definition",
    "capacity_quota_observation",
    "capacity_quota_measure",
    "capacity_budget_observation",
    "capacity_budget_measure",
    "capacity_usage_bucket",
    "capacity_usage_dimension",
    "capacity_usage_measure",
    "capacity_observation_provenance",
)

METADATA = MappingProxyType(
    {
        "revision": "v1_0500",
        "parent_revision": "v1_0400",
        "owner": "M05",
        "plan_id": "PLAN-M05",
        "requirement_ids": (
            "FR-QUOTA-001",
            "FR-QUOTA-002",
            "FR-QUOTA-004",
            "FR-BUDGET-001",
            "FR-BUDGET-002",
            "FR-BUDGET-003",
            "FR-BUDGET-004",
            "FR-BUDGET-005",
            "NFR-DATA-001",
        ),
        "schema_range": (
            "v1_0500",
            "v1_0500",
            "v1_0500",
            "v1_0500",
            "v1_0500",
        ),
        "tables": (
            "capacity_resource_policy",
            "capacity_quota_window_definition",
            "capacity_budget_definition",
            "capacity_quota_observation",
            "capacity_quota_measure",
            "capacity_budget_observation",
            "capacity_budget_measure",
            "capacity_usage_bucket",
            "capacity_usage_dimension",
            "capacity_usage_measure",
            "capacity_observation_provenance",
        ),
        "portability_notes": (
            "Exact coefficient and scale columns prohibit binary floating point",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_capacity_rows_on_initial_install",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m05_observation_tables",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": (
            "preserve_failed_database_and_restore_verified_backup_or_forward_fix"
        ),
        "reviewer": "M05-PLAN-DB-security-review",
    }
)


def _exact_field_checks(prefix: str) -> tuple[sa.CheckConstraint, ...]:
    return (
        sa.CheckConstraint(
            f"{prefix}_state IN ('available','unknown','unsupported',"
            "'not_applicable','withheld_or_denied','stale')",
            name=f"ck_{prefix}_state",
        ),
        sa.CheckConstraint(
            f"(({prefix}_state IN ('available','stale') AND "
            f"{prefix}_coefficient IS NOT NULL AND {prefix}_scale IS NOT NULL "
            f"AND {prefix}_unit IS NOT NULL) OR "
            f"({prefix}_state NOT IN ('available','stale') AND "
            f"{prefix}_coefficient IS NULL AND {prefix}_scale IS NULL "
            f"AND {prefix}_unit IS NULL))",
            name=f"ck_{prefix}_value_pair",
        ),
        sa.CheckConstraint(
            f"{prefix}_scale IS NULL OR {prefix}_scale BETWEEN 0 AND 18",
            name=f"ck_{prefix}_scale",
        ),
    )


def upgrade() -> None:
    op.create_table(
        "capacity_resource_policy",
        sa.Column("policy_id", sa.String(64), primary_key=True),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("installation_id", sa.String(64), nullable=False),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=False),
        sa.Column("capability_id", sa.String(128), nullable=False),
        sa.Column("resource_kind", sa.String(40), nullable=False),
        sa.Column("relationship_semantic", sa.String(24), nullable=False),
        sa.Column("parent_resource_id", sa.String(64)),
        sa.Column("aggregation_group_id", sa.String(64)),
        sa.Column("constraining", sa.Integer(), nullable=False),
        sa.Column("registry_revision", sa.Integer(), nullable=False),
        sa.Column("decision_reference", sa.String(128), nullable=False),
        sa.Column("policy_schema_version", sa.String(32), nullable=False),
        sa.Column("effective_from", sa.String(40), nullable=False),
        sa.Column("invalidated_at", sa.String(40)),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "provider_key",
            "account_id",
            "resource_id",
            "capability_id",
            "policy_schema_version",
            name="uq_capacity_resource_policy_scope",
        ),
        sa.CheckConstraint("constraining IN (0,1)", name="ck_capacity_policy_bool"),
        sa.CheckConstraint(
            "relationship_semantic IN ('independent','additive','rollup_parent',"
            "'informational','unknown')",
            name="ck_capacity_policy_relationship",
        ),
        sa.CheckConstraint(
            "registry_revision > 0 AND record_version > 0",
            name="ck_capacity_policy_versions",
        ),
    )

    op.create_table(
        "capacity_quota_window_definition",
        sa.Column("window_definition_id", sa.String(64), primary_key=True),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("installation_id", sa.String(64), nullable=False),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=False),
        sa.Column("capability_id", sa.String(128), nullable=False),
        sa.Column("identity_scheme_version", sa.Integer(), nullable=False),
        sa.Column("native_window_key", sa.String(128), nullable=False),
        sa.Column("definition_version", sa.Integer(), nullable=False),
        sa.Column("lifecycle", sa.String(32), nullable=False),
        sa.Column("safe_label", sa.String(128)),
        sa.Column("safe_label_state", sa.String(24), nullable=False),
        sa.Column("semantic_role", sa.String(64), nullable=False),
        sa.Column("native_unit", sa.String(64)),
        sa.Column("window_start", sa.String(40)),
        sa.Column("window_end", sa.String(40)),
        sa.Column("reset_at", sa.String(40)),
        sa.Column("renewal_semantic", sa.String(64)),
        sa.Column("reset_precision", sa.String(24), nullable=False),
        sa.Column("timezone_precision", sa.String(24), nullable=False),
        sa.Column("provider_timezone", sa.String(64)),
        sa.Column("extension_schema_ref", sa.String(128)),
        sa.Column("first_observed_at", sa.String(40), nullable=False),
        sa.Column("last_observed_at", sa.String(40), nullable=False),
        sa.Column("decision_reference", sa.String(128), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.UniqueConstraint(
            "provider_key",
            "resource_id",
            "capability_id",
            "identity_scheme_version",
            "native_window_key",
            "definition_version",
            name="uq_capacity_window_identity_version",
        ),
        sa.CheckConstraint(
            "identity_scheme_version > 0 AND definition_version > 0",
            name="ck_capacity_window_versions",
        ),
        sa.CheckConstraint(
            "(safe_label_state = 'available' AND safe_label IS NOT NULL) OR "
            "(safe_label_state <> 'available' AND safe_label IS NULL)",
            name="ck_capacity_window_label_pair",
        ),
        sa.CheckConstraint(
            "safe_label_state IN ('available','unknown','unsupported',"
            "'withheld_or_denied')",
            name="ck_capacity_window_label_state",
        ),
        sa.CheckConstraint(
            "lifecycle IN ('active','not_observed_currently','retired')",
            name="ck_capacity_window_lifecycle",
        ),
        sa.CheckConstraint(
            "window_start IS NULL OR window_end IS NULL OR window_end > window_start",
            name="ck_capacity_window_time",
        ),
        sa.CheckConstraint(
            "reset_precision IN ('exact','rounded','range','estimated','unknown') "
            "AND timezone_precision IN "
            "('exact','rounded','range','estimated','unknown')",
            name="ck_capacity_window_time_precision",
        ),
    )
    op.create_index(
        "ix_capacity_window_account_lifecycle",
        "capacity_quota_window_definition",
        ["account_id", "resource_id", "lifecycle", "window_definition_id"],
    )

    op.create_table(
        "capacity_budget_definition",
        sa.Column("budget_definition_id", sa.String(64), primary_key=True),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=False),
        sa.Column("project_id", sa.String(64)),
        sa.Column("workspace_id", sa.String(64)),
        sa.Column("budget_key", sa.String(128), nullable=False),
        sa.Column("identity_scheme_version", sa.Integer(), nullable=False),
        sa.Column("resource_semantic", sa.String(64), nullable=False),
        sa.Column("currency_state", sa.String(24), nullable=False),
        sa.Column("currency", sa.String(3)),
        sa.Column("billing_interval_semantic", sa.String(64), nullable=False),
        sa.Column("enforcement_mapping_version", sa.String(32), nullable=False),
        sa.Column("definition_version", sa.Integer(), nullable=False),
        sa.Column("lifecycle", sa.String(32), nullable=False),
        sa.Column("effective_from", sa.String(40), nullable=False),
        sa.Column("invalidated_at", sa.String(40)),
        sa.Column("decision_reference", sa.String(128), nullable=False),
        sa.UniqueConstraint(
            "provider_key",
            "resource_id",
            "budget_key",
            "identity_scheme_version",
            "definition_version",
            name="uq_capacity_budget_identity_version",
        ),
        sa.CheckConstraint(
            "identity_scheme_version > 0 AND definition_version > 0",
            name="ck_capacity_budget_versions",
        ),
        sa.CheckConstraint(
            "(currency_state = 'available' AND currency IS NOT NULL) OR "
            "(currency_state <> 'available' AND currency IS NULL)",
            name="ck_capacity_budget_currency_pair",
        ),
    )

    op.create_table(
        "capacity_observation_provenance",
        sa.Column("provenance_id", sa.String(64), primary_key=True),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("capability_id", sa.String(128), nullable=False),
        sa.Column("capability_schema_version", sa.String(32), nullable=False),
        sa.Column("adapter_id", sa.String(64), nullable=False),
        sa.Column("adapter_version", sa.String(64), nullable=False),
        sa.Column("provider_protocol_version", sa.String(32), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("source_class", sa.String(64), nullable=False),
        sa.Column("mechanism_version", sa.String(64), nullable=False),
        sa.Column("parser_version", sa.String(64)),
        sa.Column("provider_version", sa.String(128)),
        sa.Column("value_kind", sa.String(32), nullable=False),
        sa.Column("precision", sa.String(24), nullable=False),
        sa.Column("confidence", sa.String(24), nullable=False),
        sa.Column("confidence_reason_code", sa.String(128), nullable=False),
        sa.Column("freshness_deadline", sa.String(40)),
        sa.Column("freshness_policy_id", sa.String(64), nullable=False),
        sa.Column("experimental", sa.Integer(), nullable=False),
        sa.Column("operation_id", sa.String(64), nullable=False),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("decision_reference", sa.String(128), nullable=False),
        sa.CheckConstraint("experimental IN (0,1)", name="ck_capacity_provenance_bool"),
    )

    op.create_table(
        "capacity_quota_observation",
        sa.Column("observation_id", sa.String(64), primary_key=True),
        sa.Column("window_definition_id", sa.String(64), nullable=False),
        sa.Column("definition_version", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=False),
        sa.Column("observation_kind", sa.String(32), nullable=False),
        sa.Column("completeness", sa.String(24), nullable=False),
        sa.Column("provider_status_state", sa.String(24), nullable=False),
        sa.Column("provider_status_code", sa.String(128)),
        sa.Column("observed_at", sa.String(40)),
        sa.Column("reset_at", sa.String(40)),
        sa.Column("data_through_start", sa.String(40)),
        sa.Column("data_through_end", sa.String(40)),
        sa.Column("collected_at", sa.String(40), nullable=False),
        sa.Column("stored_at", sa.String(40), nullable=False),
        sa.Column("provenance_id", sa.String(64), nullable=False),
        sa.Column("collection_run_id", sa.String(64), nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("capability_schema_version", sa.String(32), nullable=False),
        sa.Column("current_candidate", sa.Integer(), nullable=False),
        sa.Column("invalidation_reason", sa.String(128)),
        sa.ForeignKeyConstraint(
            ["window_definition_id"],
            ["capacity_quota_window_definition.window_definition_id"],
        ),
        sa.ForeignKeyConstraint(
            ["provenance_id"], ["capacity_observation_provenance.provenance_id"]
        ),
        sa.CheckConstraint("definition_version > 0", name="ck_capacity_quota_defver"),
        sa.CheckConstraint("current_candidate IN (0,1)", name="ck_capacity_quota_bool"),
    )
    op.create_index(
        "ix_capacity_quota_window_time",
        "capacity_quota_observation",
        ["window_definition_id", "observed_at", "observation_id"],
    )
    op.create_index(
        "ix_capacity_quota_resource_stored",
        "capacity_quota_observation",
        ["resource_id", "stored_at", "observation_id"],
    )
    op.create_index(
        "ix_capacity_quota_run",
        "capacity_quota_observation",
        ["collection_run_id", "observation_id"],
    )

    op.create_table(
        "capacity_quota_measure",
        sa.Column("observation_id", sa.String(64), nullable=False),
        sa.Column("metric_kind", sa.String(32), nullable=False),
        sa.Column("field_state", sa.String(24), nullable=False),
        sa.Column("coefficient", sa.String(80)),
        sa.Column("scale", sa.Integer()),
        sa.Column("unit", sa.String(64)),
        sa.Column("precision", sa.String(24), nullable=False),
        sa.Column("confidence", sa.String(24), nullable=False),
        sa.Column("value_kind", sa.String(32), nullable=False),
        sa.Column("reason_code", sa.String(128)),
        sa.Column("derivation_id", sa.String(64)),
        sa.ForeignKeyConstraint(
            ["observation_id"], ["capacity_quota_observation.observation_id"]
        ),
        sa.PrimaryKeyConstraint("observation_id", "metric_kind"),
        sa.CheckConstraint(
            "metric_kind IN ('used','remaining','limit','remaining_ratio')",
            name="ck_capacity_quota_metric_kind",
        ),
        sa.CheckConstraint(
            "field_state IN ('available','unknown','unsupported','not_applicable',"
            "'withheld_or_denied','stale')",
            name="ck_capacity_quota_measure_state",
        ),
        sa.CheckConstraint(
            "((field_state IN ('available','stale') AND coefficient IS NOT NULL "
            "AND scale IS NOT NULL AND unit IS NOT NULL AND reason_code IS NULL) OR "
            "(field_state NOT IN ('available','stale') AND coefficient IS NULL "
            "AND scale IS NULL AND unit IS NULL AND reason_code IS NOT NULL))",
            name="ck_capacity_quota_measure_pair",
        ),
        sa.CheckConstraint(
            "scale IS NULL OR scale BETWEEN 0 AND 18",
            name="ck_capacity_quota_measure_scale",
        ),
        sa.CheckConstraint(
            "precision IN ('exact','rounded','range','estimated','unknown') AND "
            "confidence IN ('confirmed','high','medium','low','unknown') AND "
            "value_kind IN ('authoritative','provider_reported','derived',"
            "'heuristic','unknown')",
            name="ck_capacity_quota_measure_metadata",
        ),
        sa.CheckConstraint(
            "coefficient IS NULL OR (coefficient='0' OR "
            "(coefficient GLOB '[1-9]*' AND coefficient NOT GLOB '*[^0-9]*'))",
            name="ck_capacity_quota_measure_coefficient",
        ),
        sa.CheckConstraint(
            "coefficient IS NULL OR scale=0 OR substr(coefficient,-1)<>'0'",
            name="ck_capacity_quota_measure_canonical",
        ),
        sa.CheckConstraint(
            "metric_kind<>'remaining_ratio' OR field_state NOT IN "
            "('available','stale') OR (unit='ratio' AND (coefficient='0' OR "
            "(scale=0 AND coefficient='1') OR "
            "(scale>0 AND length(coefficient)<=scale)))",
            name="ck_capacity_quota_measure_ratio",
        ),
    )

    op.create_table(
        "capacity_budget_observation",
        sa.Column("observation_id", sa.String(64), primary_key=True),
        sa.Column("budget_definition_id", sa.String(64), nullable=False),
        sa.Column("definition_version", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=False),
        sa.Column("project_id", sa.String(64)),
        sa.Column("workspace_id", sa.String(64)),
        sa.Column("observation_kind", sa.String(32), nullable=False),
        sa.Column("completeness", sa.String(24), nullable=False),
        sa.Column("billing_start", sa.String(40)),
        sa.Column("billing_end", sa.String(40)),
        sa.Column("data_through_end", sa.String(40)),
        sa.Column("enforcement_state", sa.String(24), nullable=False),
        sa.Column("enforcement_code", sa.String(128)),
        sa.Column("observed_at", sa.String(40)),
        sa.Column("collected_at", sa.String(40), nullable=False),
        sa.Column("stored_at", sa.String(40), nullable=False),
        sa.Column("provenance_id", sa.String(64), nullable=False),
        sa.Column("collection_run_id", sa.String(64), nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("capability_schema_version", sa.String(32), nullable=False),
        sa.Column("current_candidate", sa.Integer(), nullable=False),
        sa.Column("invalidation_reason", sa.String(128)),
        sa.ForeignKeyConstraint(
            ["budget_definition_id"],
            ["capacity_budget_definition.budget_definition_id"],
        ),
        sa.ForeignKeyConstraint(
            ["provenance_id"], ["capacity_observation_provenance.provenance_id"]
        ),
        sa.CheckConstraint("definition_version > 0", name="ck_capacity_budget_defver"),
        sa.CheckConstraint(
            "current_candidate IN (0,1)", name="ck_capacity_budget_bool"
        ),
    )
    op.create_index(
        "ix_capacity_budget_definition_time",
        "capacity_budget_observation",
        ["budget_definition_id", "data_through_end", "observation_id"],
    )
    op.create_index(
        "ix_capacity_budget_run",
        "capacity_budget_observation",
        ["collection_run_id", "observation_id"],
    )

    op.create_table(
        "capacity_budget_measure",
        sa.Column("observation_id", sa.String(64), nullable=False),
        sa.Column("metric_kind", sa.String(32), nullable=False),
        sa.Column("field_state", sa.String(24), nullable=False),
        sa.Column("representation", sa.String(24)),
        sa.Column("currency", sa.String(3)),
        sa.Column("minor_units", sa.BigInteger()),
        sa.Column("coefficient", sa.String(80)),
        sa.Column("scale", sa.Integer()),
        sa.Column("precision", sa.String(24), nullable=False),
        sa.Column("confidence", sa.String(24), nullable=False),
        sa.Column("value_kind", sa.String(32), nullable=False),
        sa.Column("reason_code", sa.String(128)),
        sa.Column("derivation_id", sa.String(64)),
        sa.ForeignKeyConstraint(
            ["observation_id"], ["capacity_budget_observation.observation_id"]
        ),
        sa.PrimaryKeyConstraint("observation_id", "metric_kind"),
        sa.CheckConstraint(
            "metric_kind IN ('current_spend','available_spend','prepaid_credit',"
            "'soft_limit','hard_limit')",
            name="ck_capacity_budget_metric_kind",
        ),
        sa.CheckConstraint(
            "((field_state IN ('available','stale') AND currency IS NOT NULL AND "
            "((representation = 'minor_units' AND minor_units IS NOT NULL AND "
            "coefficient IS NULL AND scale IS NULL) OR "
            "(representation = 'decimal' AND minor_units IS NULL AND "
            "coefficient IS NOT NULL AND scale IS NOT NULL))) OR "
            "(field_state NOT IN ('available','stale') AND representation IS NULL "
            "AND currency IS NULL AND minor_units IS NULL AND coefficient IS NULL "
            "AND scale IS NULL))",
            name="ck_capacity_budget_measure_representation",
        ),
        sa.CheckConstraint(
            "scale IS NULL OR scale BETWEEN 0 AND 18",
            name="ck_capacity_budget_measure_scale",
        ),
        sa.CheckConstraint(
            "field_state IN ('available','unknown','unsupported','not_applicable',"
            "'withheld_or_denied','stale') AND "
            "precision IN ('exact','rounded','range','estimated','unknown') AND "
            "confidence IN ('confirmed','high','medium','low','unknown') AND "
            "value_kind IN ('authoritative','provider_reported','derived',"
            "'heuristic','unknown')",
            name="ck_capacity_budget_measure_metadata",
        ),
        sa.CheckConstraint(
            "(field_state IN ('available','stale') AND reason_code IS NULL) OR "
            "(field_state NOT IN ('available','stale') AND reason_code IS NOT NULL)",
            name="ck_capacity_budget_measure_reason",
        ),
        sa.CheckConstraint(
            "currency IS NULL OR (length(currency)=3 AND "
            "currency GLOB '[A-Z][A-Z][A-Z]' AND "
            "currency NOT GLOB '*[^A-Z]*')",
            name="ck_capacity_budget_measure_currency",
        ),
        sa.CheckConstraint(
            "minor_units IS NULL OR minor_units >= 0",
            name="ck_capacity_budget_measure_minor_units",
        ),
        sa.CheckConstraint(
            "coefficient IS NULL OR coefficient='0' OR "
            "(coefficient GLOB '[1-9]*' AND coefficient NOT GLOB '*[^0-9]*')",
            name="ck_capacity_budget_measure_coefficient",
        ),
        sa.CheckConstraint(
            "coefficient IS NULL OR scale=0 OR substr(coefficient,-1)<>'0'",
            name="ck_capacity_budget_measure_canonical",
        ),
    )

    op.create_table(
        "capacity_usage_bucket",
        sa.Column("bucket_id", sa.String(64), primary_key=True),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=False),
        sa.Column("project_id", sa.String(64)),
        sa.Column("workspace_id", sa.String(64)),
        sa.Column("bucket_start", sa.String(40), nullable=False),
        sa.Column("bucket_end", sa.String(40), nullable=False),
        sa.Column("data_through_end", sa.String(40)),
        sa.Column("observed_at", sa.String(40)),
        sa.Column("collected_at", sa.String(40), nullable=False),
        sa.Column("stored_at", sa.String(40), nullable=False),
        sa.Column("completeness", sa.String(24), nullable=False),
        sa.Column("provenance_id", sa.String(64), nullable=False),
        sa.Column("collection_run_id", sa.String(64), nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("capability_schema_version", sa.String(32), nullable=False),
        sa.ForeignKeyConstraint(
            ["provenance_id"], ["capacity_observation_provenance.provenance_id"]
        ),
        sa.CheckConstraint("bucket_end > bucket_start", name="ck_capacity_usage_time"),
    )
    op.create_index(
        "ix_capacity_usage_resource_time",
        "capacity_usage_bucket",
        ["resource_id", "bucket_start", "bucket_end", "bucket_id"],
    )
    op.create_index(
        "ix_capacity_usage_run",
        "capacity_usage_bucket",
        ["collection_run_id", "bucket_id"],
    )
    op.create_table(
        "capacity_usage_dimension",
        sa.Column("bucket_id", sa.String(64), nullable=False),
        sa.Column("dimension_kind", sa.String(32), nullable=False),
        sa.Column("field_state", sa.String(24), nullable=False),
        sa.Column("dimension_value", sa.String(128)),
        sa.Column("schema_version", sa.String(32), nullable=False),
        sa.ForeignKeyConstraint(["bucket_id"], ["capacity_usage_bucket.bucket_id"]),
        sa.PrimaryKeyConstraint("bucket_id", "dimension_kind"),
        sa.CheckConstraint(
            "dimension_kind IN ('organization','account','project','workspace',"
            "'api_key_safe','model','token_category','time_bucket')",
            name="ck_capacity_usage_dimension_kind",
        ),
        sa.CheckConstraint(
            "(field_state = 'available' AND dimension_value IS NOT NULL) OR "
            "(field_state <> 'available' AND dimension_value IS NULL)",
            name="ck_capacity_usage_dimension_pair",
        ),
    )
    op.create_table(
        "capacity_usage_measure",
        sa.Column("bucket_id", sa.String(64), nullable=False),
        sa.Column("metric_kind", sa.String(32), nullable=False),
        sa.Column("field_state", sa.String(24), nullable=False),
        sa.Column("coefficient", sa.String(80)),
        sa.Column("scale", sa.Integer()),
        sa.Column("unit", sa.String(64)),
        sa.Column("precision", sa.String(24), nullable=False),
        sa.Column("confidence", sa.String(24), nullable=False),
        sa.Column("value_kind", sa.String(32), nullable=False),
        sa.Column("reason_code", sa.String(128)),
        sa.Column("derivation_id", sa.String(64)),
        sa.ForeignKeyConstraint(["bucket_id"], ["capacity_usage_bucket.bucket_id"]),
        sa.PrimaryKeyConstraint("bucket_id", "metric_kind"),
        sa.CheckConstraint(
            "metric_kind IN ('input_tokens','output_tokens','cache_read_tokens',"
            "'cache_write_tokens','requests','quantity')",
            name="ck_capacity_usage_measure_kind",
        ),
        sa.CheckConstraint(
            "((field_state IN ('available','stale') AND coefficient IS NOT NULL "
            "AND scale IS NOT NULL AND unit IS NOT NULL AND reason_code IS NULL) OR "
            "(field_state NOT IN ('available','stale') AND coefficient IS NULL "
            "AND scale IS NULL AND unit IS NULL AND reason_code IS NOT NULL))",
            name="ck_capacity_usage_measure_pair",
        ),
        sa.CheckConstraint(
            "scale IS NULL OR scale BETWEEN 0 AND 18",
            name="ck_capacity_usage_measure_scale",
        ),
        sa.CheckConstraint(
            "field_state IN ('available','unknown','unsupported','not_applicable',"
            "'withheld_or_denied','stale') AND "
            "precision IN ('exact','rounded','range','estimated','unknown') AND "
            "confidence IN ('confirmed','high','medium','low','unknown') AND "
            "value_kind IN ('authoritative','provider_reported','derived',"
            "'heuristic','unknown')",
            name="ck_capacity_usage_measure_metadata",
        ),
        sa.CheckConstraint(
            "coefficient IS NULL OR coefficient='0' OR "
            "(coefficient GLOB '[1-9]*' AND coefficient NOT GLOB '*[^0-9]*')",
            name="ck_capacity_usage_measure_coefficient",
        ),
        sa.CheckConstraint(
            "coefficient IS NULL OR scale=0 OR substr(coefficient,-1)<>'0'",
            name="ck_capacity_usage_measure_canonical",
        ),
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

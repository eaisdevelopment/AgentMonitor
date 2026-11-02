"""M05 discriminated cloud targets without fabricated installation identity."""

# ruff: noqa: E501 -- deterministic SQLite rebuild SQL is intentionally explicit.

from types import MappingProxyType

from alembic import op

revision = "v1_0715"
down_revision = "v1_0714"
branch_labels = None
depends_on = None
TABLES = ("capacity_quota_window_definition", "capacity_current_projection")
METADATA = MappingProxyType(
    {
        "revision": "v1_0715",
        "parent_revision": "v1_0714",
        "owner": "M05",
        "plan_id": "PLAN-M05",
        "requirement_ids": (
            "FR-QUOTA-001",
            "FR-QUOTA-004",
            "FR-COL-004",
            "M6-A03",
            "M6-A07",
            "NFR-DATA-001",
        ),
        "schema_range": ("v1_0715", "v1_0715", "v1_0715", "v1_0715", "v1_0715"),
        "tables": (
            "capacity_quota_window_definition",
            "capacity_current_projection",
        ),
        "portability_notes": (
            "V2 cloud capacity rows retain an explicit discriminated target and a null legacy installation identity",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "existing_capacity_rows_preserved_during_offline_table_rebuild",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m05_cloud_target_schema",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": "preserve_failed_database_and_restore_verified_backup_or_forward_fix",
        "reviewer": "M05-M6-cloud-target-review",
    }
)


def upgrade() -> None:
    op.execute("PRAGMA defer_foreign_keys=ON")
    op.execute(
        "CREATE TABLE _am_v1_0715_capacity_quota_window_definition ("
        "window_definition_id VARCHAR(64) NOT NULL PRIMARY KEY,"
        "provider_key VARCHAR(64) NOT NULL,installation_id VARCHAR(64),"
        "provider_target_kind VARCHAR(32),provider_target_id VARCHAR(64),"
        "account_id VARCHAR(64) NOT NULL,resource_id VARCHAR(64) NOT NULL,"
        "capability_id VARCHAR(128) NOT NULL,identity_scheme_version INTEGER NOT NULL,"
        "native_window_key VARCHAR(128) NOT NULL,definition_version INTEGER NOT NULL,"
        "lifecycle VARCHAR(32) NOT NULL,safe_label VARCHAR(128),"
        "safe_label_state VARCHAR(24) NOT NULL,semantic_role VARCHAR(64) NOT NULL,"
        "native_unit VARCHAR(64),window_start VARCHAR(40),window_end VARCHAR(40),"
        "reset_at VARCHAR(40),renewal_semantic VARCHAR(64),"
        "reset_precision VARCHAR(24) NOT NULL,timezone_precision VARCHAR(24) NOT NULL,"
        "provider_timezone VARCHAR(64),extension_schema_ref VARCHAR(128),"
        "first_observed_at VARCHAR(40) NOT NULL,last_observed_at VARCHAR(40) NOT NULL,"
        "decision_reference VARCHAR(128) NOT NULL,created_at VARCHAR(40) NOT NULL,"
        "updated_at VARCHAR(40) NOT NULL,is_constraining INTEGER,"
        "CONSTRAINT uq_capacity_window_identity_version UNIQUE "
        "(provider_key,resource_id,capability_id,identity_scheme_version,"
        "native_window_key,definition_version),"
        "CONSTRAINT ck_capacity_window_versions CHECK "
        "(identity_scheme_version > 0 AND definition_version > 0),"
        "CONSTRAINT ck_capacity_window_label_pair CHECK "
        "((safe_label_state='available' AND safe_label IS NOT NULL) OR "
        "(safe_label_state<>'available' AND safe_label IS NULL)),"
        "CONSTRAINT ck_capacity_window_label_state CHECK "
        "(safe_label_state IN ('available','unknown','unsupported','withheld_or_denied')),"
        "CONSTRAINT ck_capacity_window_lifecycle CHECK "
        "(lifecycle IN ('active','not_observed_currently','retired')),"
        "CONSTRAINT ck_capacity_window_time CHECK "
        "(window_start IS NULL OR window_end IS NULL OR window_end > window_start),"
        "CONSTRAINT ck_capacity_window_time_precision CHECK "
        "(reset_precision IN ('exact','rounded','range','estimated','unknown') "
        "AND timezone_precision IN ('exact','rounded','range','estimated','unknown')),"
        "CONSTRAINT ck_capacity_constraint_evidence CHECK "
        "(is_constraining IS NULL OR is_constraining IN (0,1)),"
        "CONSTRAINT ck_capacity_window_provider_target CHECK "
        "((installation_id IS NOT NULL AND provider_target_kind IS NULL "
        "AND provider_target_id IS NULL) OR "
        "(installation_id IS NULL AND provider_target_kind='cloud_service' "
        "AND length(provider_target_id)=37 "
        "AND substr(provider_target_id,1,5)='amat_' "
        "AND substr(provider_target_id,6) NOT GLOB '*[^a-f0-9]*')))"
    )
    op.execute(
        "INSERT INTO _am_v1_0715_capacity_quota_window_definition "
        "(window_definition_id,provider_key,installation_id,account_id,resource_id,"
        "capability_id,identity_scheme_version,native_window_key,definition_version,"
        "lifecycle,safe_label,safe_label_state,semantic_role,native_unit,window_start,"
        "window_end,reset_at,renewal_semantic,reset_precision,timezone_precision,"
        "provider_timezone,extension_schema_ref,first_observed_at,last_observed_at,"
        "decision_reference,created_at,updated_at,is_constraining) SELECT "
        "window_definition_id,provider_key,installation_id,account_id,resource_id,"
        "capability_id,identity_scheme_version,native_window_key,definition_version,"
        "lifecycle,safe_label,safe_label_state,semantic_role,native_unit,window_start,"
        "window_end,reset_at,renewal_semantic,reset_precision,timezone_precision,"
        "provider_timezone,extension_schema_ref,first_observed_at,last_observed_at,"
        "decision_reference,created_at,updated_at,is_constraining "
        "FROM capacity_quota_window_definition"
    )
    op.drop_table("capacity_quota_window_definition")
    op.rename_table(
        "_am_v1_0715_capacity_quota_window_definition",
        "capacity_quota_window_definition",
    )
    op.create_index(
        "ix_capacity_window_account_lifecycle",
        "capacity_quota_window_definition",
        ["account_id", "resource_id", "lifecycle", "window_definition_id"],
    )
    op.create_index(
        "ix_capacity_window_provider_target",
        "capacity_quota_window_definition",
        ["provider_target_kind", "provider_target_id", "window_definition_id"],
    )
    op.execute(
        "CREATE TABLE _am_v1_0715_capacity_current_projection ("
        "projection_id VARCHAR(64) NOT NULL PRIMARY KEY,"
        "projection_key VARCHAR(64) NOT NULL UNIQUE,projection_kind VARCHAR(24) NOT NULL,"
        "provider_key VARCHAR(64) NOT NULL,installation_id VARCHAR(64),"
        "provider_target_kind VARCHAR(32),provider_target_id VARCHAR(64),"
        "account_id VARCHAR(64) NOT NULL,resource_id VARCHAR(64) NOT NULL,"
        "capability_id VARCHAR(128) NOT NULL,window_definition_id VARCHAR(64),"
        "budget_definition_id VARCHAR(64),metric_key VARCHAR(64) NOT NULL,"
        "definition_version INTEGER NOT NULL,current_observation_id VARCHAR(64) NOT NULL,"
        "collection_run_id VARCHAR(64) NOT NULL,target_generation INTEGER NOT NULL,"
        "freshness_state VARCHAR(32) NOT NULL,freshness_deadline VARCHAR(40),"
        "completeness VARCHAR(24) NOT NULL,conflict_state VARCHAR(24) NOT NULL,"
        "registry_revision INTEGER NOT NULL,source_generation INTEGER NOT NULL,"
        "projection_policy_id VARCHAR(64) NOT NULL,"
        "projection_policy_version VARCHAR(32) NOT NULL,evaluated_at VARCHAR(40) NOT NULL,"
        "updated_at VARCHAR(40) NOT NULL,projected_at VARCHAR(40) NOT NULL,"
        "record_version INTEGER NOT NULL,"
        "FOREIGN KEY(window_definition_id) REFERENCES "
        "capacity_quota_window_definition(window_definition_id),"
        "FOREIGN KEY(budget_definition_id) REFERENCES capacity_budget_definition(budget_definition_id),"
        "CONSTRAINT ck_capacity_current_versions CHECK "
        "(definition_version > 0 AND target_generation > 0 AND registry_revision > 0 "
        "AND source_generation > 0 AND record_version > 0),"
        "CONSTRAINT ck_capacity_current_freshness CHECK "
        "(freshness_state IN ('fresh','stale','freshness_unknown','conflicted')),"
        "CONSTRAINT ck_capacity_current_completeness CHECK "
        "(completeness IN ('complete','partial','unknown')),"
        "CONSTRAINT ck_capacity_current_conflict CHECK "
        "(conflict_state IN ('none','conflicted')),"
        "CONSTRAINT ck_capacity_current_kind CHECK "
        "((projection_kind='quota' AND window_definition_id IS NOT NULL "
        "AND budget_definition_id IS NULL) OR (projection_kind='budget' "
        "AND budget_definition_id IS NOT NULL AND window_definition_id IS NULL)),"
        "CONSTRAINT ck_capacity_current_provider_target CHECK "
        "((installation_id IS NOT NULL AND provider_target_kind IS NULL "
        "AND provider_target_id IS NULL) OR "
        "(installation_id IS NULL AND provider_target_kind='cloud_service' "
        "AND length(provider_target_id)=37 "
        "AND substr(provider_target_id,1,5)='amat_' "
        "AND substr(provider_target_id,6) NOT GLOB '*[^a-f0-9]*')))"
    )
    op.execute(
        "INSERT INTO _am_v1_0715_capacity_current_projection "
        "(projection_id,projection_key,projection_kind,provider_key,installation_id,"
        "account_id,resource_id,capability_id,window_definition_id,budget_definition_id,"
        "metric_key,definition_version,current_observation_id,collection_run_id,"
        "target_generation,freshness_state,freshness_deadline,completeness,"
        "conflict_state,registry_revision,source_generation,projection_policy_id,"
        "projection_policy_version,evaluated_at,updated_at,projected_at,record_version) "
        "SELECT projection_id,projection_key,projection_kind,provider_key,installation_id,"
        "account_id,resource_id,capability_id,window_definition_id,budget_definition_id,"
        "metric_key,definition_version,current_observation_id,collection_run_id,"
        "target_generation,freshness_state,freshness_deadline,completeness,"
        "conflict_state,registry_revision,source_generation,projection_policy_id,"
        "projection_policy_version,evaluated_at,updated_at,projected_at,record_version "
        "FROM capacity_current_projection"
    )
    op.drop_table("capacity_current_projection")
    op.rename_table(
        "_am_v1_0715_capacity_current_projection", "capacity_current_projection"
    )
    op.create_index(
        "ix_capacity_current_freshness",
        "capacity_current_projection",
        ["freshness_state", "freshness_deadline", "projection_id"],
    )
    op.create_index(
        "ix_capacity_current_provider_target",
        "capacity_current_projection",
        ["provider_target_kind", "provider_target_id", "projection_id"],
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

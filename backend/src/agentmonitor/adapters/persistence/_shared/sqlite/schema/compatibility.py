"""CTR-DB-001 inspection and explicit fresh-only Alembic initialization.

The bounded runner admits an absent file through the reviewed linear chain or
the current-head no-op. Existing older/empty files require the separately
approved backup and quiescence workflow and are never silently changed.
Catalog and environment digests are pinned in the binary, revisions in catalog.
"""

import ast
import hashlib
import re
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseOpenModeV1,
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
    open_sqlite_inspection,
)
from agentmonitor.contracts.database_v1 import SchemaCompatibilityV1
from agentmonitor.contracts.foundation_v1 import MigrationMetadataV1
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Connection

MIGRATIONS_PATH = Path(__file__).resolve().parents[7] / "migrations"
CATALOG_SHA256 = "d64793d4f591eeed306e0b2290766d5d0618f883b8457923f7415852df2d271d"
IAM_TABLES = frozenset(
    {
        "iam_administrator",
        "iam_browser_session",
        "iam_api_token",
        "iam_api_token_scope",
        "iam_login_throttle",
        "iam_idempotency_record",
        "iam_security_audit_event",
    }
)
IAM_INDEXES = frozenset(
    {
        "ix_iam_session_admin_issued",
        "ix_iam_session_idle",
        "ix_iam_session_absolute",
        "ix_iam_token_admin_issued",
        "ix_iam_token_expiry",
        "ix_iam_token_revoked",
        "ix_iam_idempotency_expiry",
        "ix_iam_audit_occurred",
        "ix_iam_audit_actor",
        "ix_iam_audit_type",
    }
)
# SHA-256 of sorted, whitespace-normalized CREATE TABLE/INDEX statements emitted
# by the admitted v1_0100 migration for the seven IAM tables and ten explicit
# indexes. The migration/catalog hashes independently pin the source chain.
# This catches changed columns, CHECK/FK constraints and index definitions that
# name-only inspection cannot detect. No business rows or values are inspected.
IAM_SCHEMA_SHA256 = "e534a0410662add7c0aa817b69b404f0017c158974c3692e867f919b81562b2f"
REGISTRY_TABLES = frozenset(
    {
        "reg_registry_state",
        "reg_organization",
        "reg_provider_definition",
        "reg_account",
        "reg_registry_change",
        "reg_provider_installation",
        "reg_discovery_candidate",
        "reg_provider_identity_claim",
        "reg_identity_decision",
        "reg_monitoring_profile",
        "reg_account_resource",
        "reg_profile_resource_link",
        "reg_account_configuration_reference",
        "reg_command_receipt",
        "reg_event_outbox",
    }
)
REGISTRY_INDEXES = frozenset(
    {
        "ix_reg_org_lifecycle_order",
        "ix_reg_org_normalized_name",
        "ix_reg_account_org_lifecycle_name",
        "ix_reg_account_provider_lifecycle",
        "ix_reg_change_subject_time",
        "ix_reg_change_expiry",
        "ix_reg_installation_presence",
        "ix_reg_candidate_state_seen",
        "ix_reg_decision_account_valid",
        "ix_reg_profile_account_lifecycle",
        "ix_reg_profile_installation_lifecycle",
        "ix_reg_resource_account_kind",
        "ix_reg_resource_parent",
        "ix_reg_link_resource",
        "ix_reg_config_account_owner",
        "ix_reg_receipt_expiry",
        "ix_reg_outbox_delivery",
    }
)
PROVIDER_SYSTEM_TABLES = frozenset(
    {
        "provider_system_compatibility_assessment",
        "provider_system_event_outbox",
    }
)
PROVIDER_SYSTEM_INDEXES = frozenset(
    {
        "ix_provider_system_current_assessment",
        "ix_provider_system_provider_latest",
        "ix_provider_system_state_latest",
        "ix_provider_system_retention",
        "ix_provider_system_outbox_delivery",
    }
)
COLLECTION_TABLES = frozenset(
    {
        "collection_schedule",
        "collection_request",
        "collection_lease",
        "collection_run",
        "collection_run_warning",
        "collection_run_observation_ref",
        "collection_budget_reservation",
        "collection_scheduler_instance",
        "collection_event_outbox",
        "collection_event_delivery",
    }
)
COLLECTION_INDEXES = frozenset(
    {
        "ix_collection_schedule_due",
        "ix_collection_schedule_target",
        "ix_collection_request_state_time",
        "ix_collection_lease_expiry",
        "ix_collection_run_schedule_time",
        "ix_collection_run_state_time",
        "uq_collection_run_active_schedule",
        "ix_collection_budget_scope_window",
        "ix_collection_outbox_available",
        "ix_collection_delivery_due",
    }
)
CAPACITY_TABLES = frozenset(
    {
        "capacity_resource_policy",
        "capacity_quota_window_definition",
        "capacity_budget_definition",
        "capacity_observation_provenance",
        "capacity_quota_observation",
        "capacity_quota_measure",
        "capacity_budget_observation",
        "capacity_budget_measure",
        "capacity_usage_bucket",
        "capacity_usage_dimension",
        "capacity_usage_measure",
        "capacity_commit_receipt",
        "capacity_commit_receipt_observation",
        "capacity_current_projection",
        "capacity_health_projection",
        "capacity_aggregate_projection",
        "capacity_aggregate_value",
        "capacity_availability_signal",
        "capacity_event_outbox",
        "capacity_event_delivery",
        "capacity_derivation",
        "capacity_derivation_input",
        "capacity_forecast_projection",
        "capacity_retention_run",
    }
)
CAPACITY_INDEXES = frozenset(
    {
        "ix_capacity_window_account_lifecycle",
        "ix_capacity_quota_window_time",
        "ix_capacity_quota_resource_stored",
        "ix_capacity_quota_run",
        "ix_capacity_budget_definition_time",
        "ix_capacity_budget_run",
        "ix_capacity_usage_resource_time",
        "ix_capacity_usage_run",
        "ix_capacity_receipt_run",
        "ix_capacity_current_freshness",
        "ix_capacity_health_account",
        "ix_capacity_signal_current",
        "uq_capacity_signal_one_current",
        "ix_capacity_event_available",
        "ix_capacity_delivery_due",
        "ix_capacity_forecast_account",
        "ix_capacity_quota_history_measured",
        "ix_capacity_usage_history_measured",
        "ix_capacity_retention_started",
        "ix_capacity_quota_export_cursor",
        "ix_capacity_budget_export_cursor",
        "ix_capacity_usage_export_cursor",
    }
)
RUNTIME_TABLES = frozenset(
    {
        "runtime_session",
        "runtime_process_instance",
        "runtime_process_snapshot",
        "runtime_session_observation",
        "runtime_metric_observation",
        "runtime_session_process_link",
        "runtime_session_relationship",
        "runtime_correlation_evidence",
        "runtime_session_correlation_decision",
        "runtime_stall_policy",
        "runtime_state_transition",
        "runtime_ingest_receipt",
        "runtime_event_outbox",
    }
)
RUNTIME_INDEXES = frozenset(
    {
        "ix_runtime_process_current",
        "ix_runtime_process_provider",
        "ix_runtime_process_history",
        "ix_runtime_session_current",
        "ix_runtime_session_account",
        "ix_runtime_session_history",
        "ix_runtime_metric_history",
        "ix_runtime_metric_process_history",
        "ix_runtime_link_session_current",
        "uq_runtime_link_one_current_pair",
        "ix_runtime_relationship_child_current",
        "uq_runtime_relationship_one_current_parent",
        "ix_runtime_evidence_session_time",
        "ix_runtime_decision_session_current",
        "uq_runtime_decision_one_current",
        "ix_runtime_policy_scope_current",
        "uq_runtime_policy_one_current",
        "ix_runtime_transition_session",
        "ix_runtime_receipt_run",
        "ix_runtime_outbox_available",
    }
)
# Filled from the normalized statements emitted by the reviewed v1_0100 and
# v1_0200..0204 migrations. Revision/catalog digests independently pin bytes.
OWNED_SCHEMA_SHA256 = "d95878f11f1ebbe6cafadd418fd1fbd0f7b65dac024a66e50471107557d40384"
M3_OWNED_SCHEMA_SHA256 = (
    "aa65cda689f337c8fe7189d723812b10a2a4ecac53d63e68a9e56ff51a4b48e7"
)
M5_OWNED_SCHEMA_SHA256 = (
    "8a975e08cf454d1c1189791d5e53c248786d42857d66df4d0bcf745deaa28111"
)
M6_OWNED_SCHEMA_SHA256 = (
    "4e90274e1aa5e867e044d168a51ebb4d2864f77f64acb89ada64dacf046250f7"
)
ALERT_TABLES = frozenset(
    {
        "alert_rule",
        "alert_rule_revision",
        "alert_alert",
        "alert_event",
        "alert_evidence_reference",
        "alert_event_receipt",
        "alert_stream_checkpoint",
        "alert_command_receipt",
        "alert_deadline",
        "alert_reevaluation_job",
        "alert_event_outbox",
        "alert_retention_run",
    }
)
ALERT_INDEXES = frozenset(
    {
        "ix_alert_deadline_due",
        "ix_alert_event_history",
        "ix_alert_evidence_alert",
        "ix_alert_notifications",
        "ix_alert_outbox_available",
        "ix_alert_receipt_stream",
        "ix_alert_reevaluation_due",
        "ix_alert_rule_page",
        "ix_alert_scope",
        "ix_alert_subject",
        "ix_alert_terminal_retention",
        "ix_alert_unread_snooze",
        "uq_alert_rule_active_scope",
    }
)
M4_OWNED_SCHEMA_SHA256 = (
    "444f60488a42d8c0d5755711a48007927911d81b27dd4eb66d5b8898550c5cb4"
)
M4_DELIVERY_SCHEMA_SHA256 = (
    "18661bbdb99a85eb0db083e63fffde28b90fae14b946e64fec9c2a46c015480a"
)
M4_RULE_GUARD_SCHEMA_SHA256 = (
    "081864af24c3b6ce41dcad093e785d9dc0b4b07e35239a7120946f1a843abbb4"
)
M4_COLLECTOR_SCHEMA_SHA256 = (
    "3b3bf7db294670c5ff38c7d797de46119e645c07c06224c4fa09789861c230e4"
)
M4_CURRENT_SCHEMA_SHA256 = (
    "bb7fc3101bff956f452a2fd79b8c085c3c930dee9d90f0e25bb931a5dbf7ebfb"
)
CAPACITY_PROJECTION_TRIGGERS = frozenset(
    {
        "tr_capacity_forecast_snapshot_insert",
        "tr_capacity_forecast_snapshot_update",
        "tr_capacity_projection_event_insert",
        "tr_capacity_projection_event_update",
    }
)
COLLECTOR_DELIVERY_TRIGGERS = frozenset(
    {
        "tr_collection_delivery_proof_insert",
        "tr_collection_delivery_proof_update",
    }
)
ALERT_CONFIGURATION_TRIGGERS = frozenset(
    {
        "tr_alert_rule_configuration_insert",
        "tr_alert_rule_configuration_update",
        "tr_alert_rule_revision_configuration_insert",
        "tr_alert_rule_revision_configuration_update",
    }
)
REVISION_ORDER = {
    "base": -1,
    "v1_0000": 0,
    "v1_0100": 100,
    "v1_0200": 200,
    "v1_0201": 201,
    "v1_0202": 202,
    "v1_0203": 203,
    "v1_0204": 204,
    "v1_0300": 300,
    "v1_0400": 400,
    "v1_0500": 500,
    "v1_0501": 501,
    "v1_0502": 502,
    "v1_0503": 503,
    "v1_0504": 504,
    "v1_0600": 600,
    "v1_0601": 601,
    "v1_0602": 602,
    "v1_0603": 603,
    "v1_0700": 700,
    "v1_0701": 701,
    "v1_0702": 702,
    "v1_0703": 703,
    "v1_0704": 704,
    "v1_0705": 705,
    "v1_0706": 706,
    "v1_0707": 707,
}
ApplicationSchemaRangeV1 = SchemaCompatibilityV1
SchemaState = Literal[
    "missing",
    "empty",
    "upgrade_required",
    "compatible",
    "newer_than_binary",
    "locked",
    "unreadable",
    "corrupt",
    "unknown_revision",
    "multiple_heads",
    "checksum_mismatch",
    "policy_incompatible",
    "migration_failed",
]


class SchemaCompatibilityError(ValueError):
    """Public safe bounded classification, without paths, SQL or stored values."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class MigrationCatalogV1:
    version: str
    digest: str
    head: str
    revisions: tuple[MigrationMetadataV1, ...]


@dataclass(frozen=True, slots=True)
class SchemaCompatibilityViewV1:
    state: SchemaState
    current_revision: str | None
    application_range: ApplicationSchemaRangeV1
    integrity_state: Literal["passed", "failed", "not_checked"]
    policy_state: Literal["passed", "failed", "not_checked"]
    migration_required: bool
    reason_codes: tuple[str, ...]
    checked_at: datetime
    catalog_version: str
    mode: DatabaseOpenModeV1


@dataclass(frozen=True, slots=True)
class WritableSchemaReceiptV1:
    revision: str
    catalog_digest: str
    checked_at: datetime


def _read_artifact(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
        raise SchemaCompatibilityError("migration_catalog_invalid")
    return path.read_bytes()


def _text(record: dict[str, object], key: str, *, empty: bool = False) -> str:
    value = record.get(key)
    if not isinstance(value, str) or (not empty and not value) or len(value) > 256:
        raise SchemaCompatibilityError("migration_catalog_invalid")
    return value


def _strings(
    record: dict[str, object], key: str, *, empty: bool = False
) -> tuple[str, ...]:
    value = record.get(key)
    if not isinstance(value, list) or len(value) > 32 or (not value and not empty):
        raise SchemaCompatibilityError("migration_catalog_invalid")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item or len(item) > 256:
            raise SchemaCompatibilityError("migration_catalog_invalid")
        result.append(item)
    return tuple(result)


def _metadata(record: dict[str, object], digest: str) -> MigrationMetadataV1:
    revisions = _strings(record, "schema_range")
    if len(revisions) != 5 or any(item != record.get("revision") for item in revisions):
        raise SchemaCompatibilityError("migration_catalog_invalid")
    app = ApplicationSchemaRangeV1(*revisions, catalog_digest=digest)
    return MigrationMetadataV1(
        revision=_text(record, "revision"),
        parent_revision=_text(record, "parent_revision", empty=True) or None,
        owner=_text(record, "owner"),
        plan_id=_text(record, "plan_id"),
        requirement_ids=_strings(record, "requirement_ids"),
        schema_range=app,
        tables=_strings(record, "tables", empty=True),
        portability_notes=_strings(record, "portability_notes"),
        lock_policy=_text(record, "lock_policy"),
        downtime_policy=_text(record, "downtime_policy"),
        expected_data_volume=_text(record, "expected_data_volume"),
        backup_prerequisite=_text(record, "backup_prerequisite"),
        validation_ids=_strings(record, "validation_ids"),
        recovery_policy=_text(record, "recovery_policy"),
        reviewer=_text(record, "reviewer"),
    )


def _validate_revision(source: bytes, record: dict[str, object]) -> None:
    """Inspect literals without executing migration code before trust checks."""
    assignments: dict[str, ast.expr] = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id in assignments:
                        raise SchemaCompatibilityError("migration_catalog_invalid")
                    assignments[target.id] = node.value
    for name, expected in (
        ("revision", record["revision"]),
        ("down_revision", record["parent_revision"] or None),
        ("branch_labels", None),
        ("depends_on", None),
    ):
        if ast.literal_eval(assignments[name]) != expected:
            raise SchemaCompatibilityError("migration_catalog_invalid")
    metadata = assignments["METADATA"]
    if (
        not isinstance(metadata, ast.Call)
        or not isinstance(metadata.func, ast.Name)
        or metadata.func.id != "MappingProxyType"
        or len(metadata.args) != 1
        or metadata.keywords
    ):
        raise SchemaCompatibilityError("migration_catalog_invalid")
    literal = ast.literal_eval(metadata.args[0])
    expected_metadata = {
        key: tuple(value) if isinstance(value, list) else value
        for key, value in record.items()
        if key not in {"ordinal", "filename", "sha256", "status", "reviewed_at"}
    }
    if literal != expected_metadata:
        raise SchemaCompatibilityError("migration_catalog_invalid")


def load_migration_catalog(
    migrations_path: Path = MIGRATIONS_PATH,
) -> MigrationCatalogV1:
    """Validate the reviewed catalog, full revision inventory and immutable bytes."""
    failure: str | None = None
    result: MigrationCatalogV1 | None = None
    try:
        if migrations_path.is_symlink() or (migrations_path / "versions").is_symlink():
            raise SchemaCompatibilityError("migration_catalog_invalid")
        source = _read_artifact(migrations_path / "catalog.toml")
        digest = hashlib.sha256(source).hexdigest()
        if digest != CATALOG_SHA256:
            raise SchemaCompatibilityError("migration_checksum_mismatch")
        document = tomllib.loads(source.decode("utf-8"))
        if document.keys() != {"version", "head", "env_sha256", "revisions"}:
            raise SchemaCompatibilityError("migration_catalog_invalid")
        records = document["revisions"]
        if (
            document["version"] != "1.7.7"
            or document["head"] != "v1_0707"
            or not isinstance(records, list)
            or len(records) != 26
            or not all(isinstance(record, dict) for record in records)
        ):
            raise SchemaCompatibilityError("migration_catalog_invalid")
        filenames = tuple(_text(record, "filename") for record in records)
        if filenames != (
            "v1_0000_fnd_anchor.py",
            "v1_0100_m01_identity_access.py",
            "v1_0200_m02_registry_core.py",
            "v1_0201_m02_provider_identity.py",
            "v1_0202_m02_profiles_resources.py",
            "v1_0203_m02_account_configuration.py",
            "v1_0204_m02_receipts_outbox.py",
            "v1_0300_m03_compatibility.py",
            "v1_0400_m04_collection.py",
            "v1_0500_m05_capacity_observations.py",
            "v1_0501_m05_capacity_receipts.py",
            "v1_0502_m05_capacity_health.py",
            "v1_0503_m05_capacity_forecasts.py",
            "v1_0504_m05_capacity_retention.py",
            "v1_0600_m06_runtime_core.py",
            "v1_0601_m06_runtime_correlation.py",
            "v1_0602_m06_runtime_state_outbox.py",
            "v1_0603_m06_runtime_indexes.py",
            "v1_0700_m07_alert_rules.py",
            "v1_0701_m07_alert_lifecycle.py",
            "v1_0702_m07_alert_deadlines_outbox.py",
            "v1_0703_m05_capacity_projection_metadata.py",
            "v1_0704_m05_event_delivery_proof.py",
            "v1_0705_m07_rule_configuration_guards.py",
            "v1_0706_m04_collector_alerts.py",
            "v1_0707_m05_current_capacity_projections.py",
        ) or tuple(record.get("ordinal") for record in records) != (
            0,
            100,
            200,
            201,
            202,
            203,
            204,
            300,
            400,
            500,
            501,
            502,
            503,
            504,
            600,
            601,
            602,
            603,
            700,
            701,
            702,
            703,
            704,
            705,
            706,
            707,
        ):
            raise SchemaCompatibilityError("migration_catalog_invalid")
        inventory = {path.name for path in (migrations_path / "versions").glob("*.py")}
        if inventory != set(filenames):
            raise SchemaCompatibilityError("migration_catalog_invalid")
        artifact_digests = [(migrations_path / "env.py", document["env_sha256"])]
        artifact_digests.extend(
            (migrations_path / "versions" / filename, _text(record, "sha256"))
            for record, filename in zip(records, filenames, strict=True)
        )
        for path, expected in artifact_digests:
            if not isinstance(expected, str) or not re.fullmatch(
                r"[a-f0-9]{64}", expected
            ):
                raise SchemaCompatibilityError("migration_catalog_invalid")
            if hashlib.sha256(_read_artifact(path)).hexdigest() != expected:
                raise SchemaCompatibilityError("migration_checksum_mismatch")
        for record, filename in zip(records, filenames, strict=True):
            _validate_revision(
                _read_artifact(migrations_path / "versions" / filename), record
            )
        metadata = tuple(_metadata(record, digest) for record in records)
        if (
            metadata[0].revision != "v1_0000"
            or metadata[0].parent_revision is not None
            or metadata[0].owner != "PLAN-FND"
            or metadata[0].plan_id != "PLAN-FND"
            or metadata[0].tables
            or records[0].get("status") != "shared"
            or metadata[1].revision != "v1_0100"
            or metadata[1].parent_revision != "v1_0000"
            or metadata[1].owner != "M01"
            or metadata[1].plan_id != "PLAN-M01"
            or set(metadata[1].tables) != IAM_TABLES
            or records[1].get("status") not in {"implemented", "shared"}
            or tuple(item.revision for item in metadata[2:7])
            != ("v1_0200", "v1_0201", "v1_0202", "v1_0203", "v1_0204")
            or any(
                item.owner != "M02" or item.plan_id != "PLAN-M02"
                for item in metadata[2:7]
            )
            or set(table for item in metadata[2:7] for table in item.tables)
            != REGISTRY_TABLES
            or any(record.get("status") != "shared" for record in records[2:7])
            or metadata[7].revision != "v1_0300"
            or metadata[7].parent_revision != "v1_0204"
            or metadata[7].owner != "M03"
            or metadata[7].plan_id != "PLAN-M03"
            or set(metadata[7].tables) != PROVIDER_SYSTEM_TABLES
            or records[7].get("status") != "shared"
            or metadata[8].revision != "v1_0400"
            or metadata[8].parent_revision != "v1_0300"
            or metadata[8].owner != "M04"
            or metadata[8].plan_id != "PLAN-M04"
            or set(metadata[8].tables) != COLLECTION_TABLES
            or records[8].get("status") != "shared"
            or tuple(item.revision for item in metadata[9:14])
            != ("v1_0500", "v1_0501", "v1_0502", "v1_0503", "v1_0504")
            or any(
                item.owner != "M05" or item.plan_id != "PLAN-M05"
                for item in metadata[9:14]
            )
            or set(table for item in metadata[9:14] for table in item.tables)
            != CAPACITY_TABLES
            or any(record.get("status") != "shared" for record in records[9:14])
            or tuple(item.revision for item in metadata[14:18])
            != ("v1_0600", "v1_0601", "v1_0602", "v1_0603")
            or any(
                item.owner != "M06" or item.plan_id != "PLAN-M06"
                for item in metadata[14:18]
            )
            or set(table for item in metadata[14:18] for table in item.tables)
            != RUNTIME_TABLES
            or any(record.get("status") != "shared" for record in records[14:18])
            or tuple(item.revision for item in metadata[18:21])
            != ("v1_0700", "v1_0701", "v1_0702")
            or tuple(item.parent_revision for item in metadata[18:22])
            != ("v1_0603", "v1_0700", "v1_0701", "v1_0702")
            or any(
                item.owner != "M07" or item.plan_id != "PLAN-M07"
                for item in metadata[18:21]
            )
            or set(table for item in metadata[18:21] for table in item.tables)
            != ALERT_TABLES
            or metadata[21].owner != "M05"
            or metadata[21].plan_id != "PLAN-M05"
            or set(metadata[21].tables)
            != {"capacity_quota_window_definition", "capacity_forecast_projection"}
            or metadata[22].parent_revision != "v1_0703"
            or metadata[22].owner != "M05"
            or metadata[22].plan_id != "PLAN-M05"
            or metadata[22].tables != ("capacity_event_delivery",)
            or metadata[23].parent_revision != "v1_0704"
            or metadata[23].owner != "M07"
            or metadata[23].plan_id != "PLAN-M07"
            or metadata[23].tables != ()
            or metadata[24].parent_revision != "v1_0705"
            or metadata[24].owner != "M04"
            or metadata[24].plan_id != "PLAN-M04"
            or set(metadata[24].tables)
            != {
                "collection_alert_condition",
                "collection_run",
                "collection_event_delivery",
            }
            or metadata[25].parent_revision != "v1_0706"
            or metadata[25].owner != "M05"
            or metadata[25].plan_id != "PLAN-M05"
            or set(metadata[25].tables)
            != {
                "capacity_forecast_projection",
                "capacity_event_outbox",
                "capacity_availability_current",
            }
            or any(record.get("status") != "shared" for record in records[18:26])
            or any(
                item.backup_prerequisite
                not in {"none_empty_bootstrap", "required_existing_database"}
                for item in metadata
            )
        ):
            raise SchemaCompatibilityError("migration_catalog_invalid")
        result = MigrationCatalogV1("1.7.7", digest, "v1_0707", metadata)
    except SchemaCompatibilityError as error:
        failure = error.code
    except (OSError, ValueError, KeyError, TypeError, SyntaxError, UnicodeError):
        failure = "migration_catalog_invalid"
    if failure is not None or result is None:
        raise SchemaCompatibilityError(failure or "migration_catalog_invalid") from None
    return result


def application_schema_range() -> ApplicationSchemaRangeV1:
    return load_migration_catalog().revisions[-1].schema_range


def _objects(connection: Connection) -> set[tuple[str, str]]:
    # Schema metadata only: never read business rows or sqlite_schema.sql.
    objects = {
        (row[0], row[1])
        for row in connection.exec_driver_sql(
            "SELECT type, name FROM sqlite_schema ORDER BY type, name LIMIT 513"
        )
    }
    if len(objects) > 512:
        raise SchemaCompatibilityError("migration_catalog_invalid")
    return objects


def _inspect(
    connection: Connection, app: ApplicationSchemaRangeV1
) -> tuple[SchemaState, str | None]:
    if connection.exec_driver_sql("PRAGMA quick_check").scalars().fetchmany(2) != [
        "ok"
    ]:
        return "corrupt", None
    objects = _objects(connection)
    if not objects:
        return "empty", None
    anchor_objects = {
        ("table", "alembic_version"),
        ("index", "sqlite_autoindex_alembic_version_1"),
    }
    if not anchor_objects <= objects:
        return "migration_failed", None
    if not _marker_structure_is_valid(connection):
        return "migration_failed", None
    heads = (
        connection.exec_driver_sql("SELECT version_num FROM alembic_version LIMIT 2")
        .scalars()
        .all()
    )
    if not heads:
        return (
            ("upgrade_required", None)
            if objects == anchor_objects
            else ("migration_failed", None)
        )
    if len(heads) != 1:
        return "multiple_heads", None
    current = heads[0]
    if current not in REVISION_ORDER or current == "base":
        return "unknown_revision", None
    if current == "v1_0000" and objects != anchor_objects:
        return "migration_failed", current
    if current == "v1_0100":
        table_names = {name for kind, name in objects if kind == "table"}
        indexes = {name for kind, name in objects if kind == "index"}
        auto_indexes = {
            name for name in indexes if name.startswith("sqlite_autoindex_iam_")
        }
        if (
            table_names != IAM_TABLES | {"alembic_version"}
            or not IAM_INDEXES <= indexes
            or indexes - auto_indexes - IAM_INDEXES
            != {"sqlite_autoindex_alembic_version_1"}
            or any(kind not in {"table", "index"} for kind, _ in objects)
        ):
            return "migration_failed", current
        if not _iam_structure_is_valid(connection):
            return "migration_failed", current
    if current in {"v1_0200", "v1_0201", "v1_0202", "v1_0203"}:
        # Intermediate revisions exist only inside the explicit runner. Normal
        # service never accepts a partially applied module chain.
        return "upgrade_required", current
    if current == "v1_0204":
        table_names = {name for kind, name in objects if kind == "table"}
        indexes = {name for kind, name in objects if kind == "index"}
        explicit_indexes = {
            name for name in indexes if not name.startswith("sqlite_autoindex_")
        }
        if (
            table_names != IAM_TABLES | REGISTRY_TABLES | {"alembic_version"}
            or explicit_indexes != IAM_INDEXES | REGISTRY_INDEXES
            or any(kind not in {"table", "index"} for kind, _ in objects)
        ):
            return "migration_failed", current
        if not _owned_structure_is_valid(connection):
            return "migration_failed", current
    if current == "v1_0300":
        table_names = {name for kind, name in objects if kind == "table"}
        indexes = {name for kind, name in objects if kind == "index"}
        explicit_indexes = {
            name for name in indexes if not name.startswith("sqlite_autoindex_")
        }
        if (
            table_names
            != IAM_TABLES
            | REGISTRY_TABLES
            | PROVIDER_SYSTEM_TABLES
            | {"alembic_version"}
            or explicit_indexes
            != IAM_INDEXES | REGISTRY_INDEXES | PROVIDER_SYSTEM_INDEXES
            or any(kind not in {"table", "index"} for kind, _ in objects)
        ):
            return "migration_failed", current
        if not _m3_owned_structure_is_valid(connection):
            return "migration_failed", current
    if current in {"v1_0400", "v1_0500", "v1_0501", "v1_0502", "v1_0503"}:
        # The M04/M05 chain is an atomic shared allocation from the service's
        # perspective. Partially applied revisions are never writable.
        return "upgrade_required", current
    if current == "v1_0504":
        table_names = {name for kind, name in objects if kind == "table"}
        indexes = {name for kind, name in objects if kind == "index"}
        explicit_indexes = {
            name for name in indexes if not name.startswith("sqlite_autoindex_")
        }
        if (
            table_names
            != IAM_TABLES
            | REGISTRY_TABLES
            | PROVIDER_SYSTEM_TABLES
            | COLLECTION_TABLES
            | CAPACITY_TABLES
            | {"alembic_version"}
            or explicit_indexes
            != IAM_INDEXES
            | REGISTRY_INDEXES
            | PROVIDER_SYSTEM_INDEXES
            | COLLECTION_INDEXES
            | CAPACITY_INDEXES
            or any(kind not in {"table", "index"} for kind, _ in objects)
        ):
            return "migration_failed", current
        if not _m5_owned_structure_is_valid(connection):
            return "migration_failed", current
    if current in {"v1_0600", "v1_0601", "v1_0602"}:
        # The frozen M06 allocation is admitted only as one complete chain.
        return "upgrade_required", current
    if current == "v1_0603":
        table_names = {name for kind, name in objects if kind == "table"}
        indexes = {name for kind, name in objects if kind == "index"}
        explicit_indexes = {
            name for name in indexes if not name.startswith("sqlite_autoindex_")
        }
        if (
            table_names
            != IAM_TABLES
            | REGISTRY_TABLES
            | PROVIDER_SYSTEM_TABLES
            | COLLECTION_TABLES
            | CAPACITY_TABLES
            | RUNTIME_TABLES
            | {"alembic_version"}
            or explicit_indexes
            != IAM_INDEXES
            | REGISTRY_INDEXES
            | PROVIDER_SYSTEM_INDEXES
            | COLLECTION_INDEXES
            | CAPACITY_INDEXES
            | RUNTIME_INDEXES
            or any(kind not in {"table", "index"} for kind, _ in objects)
        ):
            return "migration_failed", current
        if not _m6_owned_structure_is_valid(connection):
            return "migration_failed", current
    if current in {"v1_0700", "v1_0701", "v1_0702"}:
        return "upgrade_required", current
    if current in {"v1_0703", "v1_0704", "v1_0705", "v1_0706", "v1_0707"}:
        table_names = {name for kind, name in objects if kind == "table"}
        explicit_indexes = {
            name
            for kind, name in objects
            if kind == "index" and not name.startswith("sqlite_autoindex_")
        }
        expected_tables = (
            IAM_TABLES
            | REGISTRY_TABLES
            | PROVIDER_SYSTEM_TABLES
            | COLLECTION_TABLES
            | CAPACITY_TABLES
            | RUNTIME_TABLES
            | ALERT_TABLES
        )
        expected_indexes = (
            IAM_INDEXES
            | REGISTRY_INDEXES
            | PROVIDER_SYSTEM_INDEXES
            | COLLECTION_INDEXES
            | CAPACITY_INDEXES
            | RUNTIME_INDEXES
            | ALERT_INDEXES
        )
        guarded = current in {"v1_0705", "v1_0706", "v1_0707"}
        collector_guarded = current in {"v1_0706", "v1_0707"}
        projection_guarded = current == "v1_0707"
        expected_triggers = (
            (ALERT_CONFIGURATION_TRIGGERS if guarded else frozenset())
            | (COLLECTOR_DELIVERY_TRIGGERS if collector_guarded else frozenset())
            | (CAPACITY_PROJECTION_TRIGGERS if projection_guarded else frozenset())
        )
        additional_tables = (
            frozenset({"collection_alert_condition"})
            if collector_guarded
            else frozenset()
        ) | (
            frozenset({"capacity_availability_current"})
            if projection_guarded
            else frozenset()
        )
        additional_indexes = (
            frozenset({"ix_collection_alert_subject", "ix_collection_alert_freshness"})
            if collector_guarded
            else frozenset()
        ) | (
            frozenset({"ix_capacity_availability_account"})
            if projection_guarded
            else frozenset()
        )
        triggers = {name for kind, name in objects if kind == "trigger"}
        if (
            table_names != expected_tables | additional_tables | {"alembic_version"}
            or explicit_indexes != expected_indexes | additional_indexes
            or triggers != expected_triggers
            or any(kind not in {"table", "index", "trigger"} for kind, _ in objects)
            or not _m4_owned_structure_is_valid(
                connection,
                M4_CURRENT_SCHEMA_SHA256
                if projection_guarded
                else M4_COLLECTOR_SCHEMA_SHA256
                if collector_guarded
                else M4_RULE_GUARD_SCHEMA_SHA256
                if guarded
                else M4_OWNED_SCHEMA_SHA256
                if current == "v1_0703"
                else M4_DELIVERY_SCHEMA_SHA256,
                expected_triggers=expected_triggers,
                additional_tables=additional_tables,
                additional_indexes=additional_indexes,
            )
        ):
            return "migration_failed", current
    order = REVISION_ORDER
    bounds = (
        app.minimum_readable_revision,
        app.minimum_writable_revision,
        app.maximum_readable_revision,
        app.maximum_writable_revision,
        app.migration_target_revision,
    )
    if any(bound not in order for bound in bounds):
        return "unknown_revision", current
    if (
        order[app.minimum_readable_revision] > order[app.maximum_readable_revision]
        or order[app.minimum_writable_revision] > order[app.maximum_writable_revision]
        or not order[app.minimum_writable_revision]
        <= order[app.migration_target_revision]
        <= order[app.maximum_writable_revision]
    ):
        return "policy_incompatible", current
    if (
        order[app.maximum_readable_revision] < order[current]
        or order[app.maximum_writable_revision] < order[current]
    ):
        return "newer_than_binary", current
    if order[current] < order[app.minimum_writable_revision]:
        return "upgrade_required", current
    if order[current] < order[app.minimum_readable_revision]:
        return "upgrade_required", current
    return "compatible", current


def _iam_structure_is_valid(connection: Connection) -> bool:
    """Verify the exact admitted IAM schema without reading business data."""
    rows = connection.exec_driver_sql(
        "SELECT type, name, sql FROM sqlite_schema "
        "WHERE type IN ('table', 'index') ORDER BY type, name LIMIT 129"
    ).fetchall()
    definitions: list[str] = []
    names: set[str] = set()
    for kind, name, sql in rows:
        if name not in IAM_TABLES | IAM_INDEXES:
            continue
        if not isinstance(sql, str) or kind not in {"table", "index"}:
            return False
        names.add(name)
        definitions.append(f"{kind}|{name}|{' '.join(sql.split())}")
    if names != IAM_TABLES | IAM_INDEXES:
        return False
    digest = hashlib.sha256("\n".join(definitions).encode("utf-8")).hexdigest()
    return digest == IAM_SCHEMA_SHA256


def _owned_structure_is_valid(connection: Connection) -> bool:
    """Verify the exact M01+M02 schema without reading any business row."""
    rows = connection.exec_driver_sql(
        "SELECT type, name, sql FROM sqlite_schema "
        "WHERE type IN ('table', 'index') ORDER BY type, name LIMIT 257"
    ).fetchall()
    definitions: list[str] = []
    expected = IAM_TABLES | REGISTRY_TABLES | IAM_INDEXES | REGISTRY_INDEXES
    names: set[str] = set()
    for kind, name, sql in rows:
        if name not in expected:
            continue
        if not isinstance(sql, str) or kind not in {"table", "index"}:
            return False
        names.add(name)
        definitions.append(f"{kind}|{name}|{' '.join(sql.split())}")
    if names != expected:
        return False
    digest = hashlib.sha256("\n".join(definitions).encode("utf-8")).hexdigest()
    return digest == OWNED_SCHEMA_SHA256


def _m3_owned_structure_is_valid(connection: Connection) -> bool:
    """Verify the exact M01+M02+M03 schema without reading business rows."""
    rows = connection.exec_driver_sql(
        "SELECT type, name, sql FROM sqlite_schema "
        "WHERE type IN ('table', 'index') ORDER BY type, name LIMIT 257"
    ).fetchall()
    expected = (
        IAM_TABLES
        | REGISTRY_TABLES
        | PROVIDER_SYSTEM_TABLES
        | IAM_INDEXES
        | REGISTRY_INDEXES
        | PROVIDER_SYSTEM_INDEXES
    )
    names: set[str] = set()
    definitions: list[str] = []
    for kind, name, sql in rows:
        if name not in expected:
            continue
        if not isinstance(sql, str) or kind not in {"table", "index"}:
            return False
        names.add(name)
        definitions.append(f"{kind}|{name}|{' '.join(sql.split())}")
    if names != expected:
        return False
    digest = hashlib.sha256("\n".join(definitions).encode("utf-8")).hexdigest()
    return digest == M3_OWNED_SCHEMA_SHA256


def _m5_owned_structure_is_valid(connection: Connection) -> bool:
    """Verify the exact admitted schema through M05 without business rows."""
    rows = connection.exec_driver_sql(
        "SELECT type, name, sql FROM sqlite_schema "
        "WHERE type IN ('table', 'index') ORDER BY type, name LIMIT 513"
    ).fetchall()
    expected = (
        IAM_TABLES
        | REGISTRY_TABLES
        | PROVIDER_SYSTEM_TABLES
        | COLLECTION_TABLES
        | CAPACITY_TABLES
        | IAM_INDEXES
        | REGISTRY_INDEXES
        | PROVIDER_SYSTEM_INDEXES
        | COLLECTION_INDEXES
        | CAPACITY_INDEXES
    )
    names: set[str] = set()
    definitions: list[str] = []
    for kind, name, sql in rows:
        if name not in expected:
            continue
        if not isinstance(sql, str) or kind not in {"table", "index"}:
            return False
        names.add(name)
        definitions.append(f"{kind}|{name}|{' '.join(sql.split())}")
    if names != expected:
        return False
    digest = hashlib.sha256("\n".join(definitions).encode("utf-8")).hexdigest()
    return digest == M5_OWNED_SCHEMA_SHA256


def _m6_owned_structure_is_valid(connection: Connection) -> bool:
    """Verify the exact admitted schema through M06 without business rows."""
    rows = connection.exec_driver_sql(
        "SELECT type, name, sql FROM sqlite_schema "
        "WHERE type IN ('table', 'index') ORDER BY type, name LIMIT 513"
    ).fetchall()
    expected = (
        IAM_TABLES
        | REGISTRY_TABLES
        | PROVIDER_SYSTEM_TABLES
        | COLLECTION_TABLES
        | CAPACITY_TABLES
        | RUNTIME_TABLES
        | IAM_INDEXES
        | REGISTRY_INDEXES
        | PROVIDER_SYSTEM_INDEXES
        | COLLECTION_INDEXES
        | CAPACITY_INDEXES
        | RUNTIME_INDEXES
    )
    names: set[str] = set()
    definitions: list[str] = []
    for kind, name, sql in rows:
        if name not in expected:
            continue
        if not isinstance(sql, str) or kind not in {"table", "index"}:
            return False
        names.add(name)
        definitions.append(f"{kind}|{name}|{' '.join(sql.split())}")
    if names != expected:
        return False
    digest = hashlib.sha256("\n".join(definitions).encode("utf-8")).hexdigest()
    return digest == M6_OWNED_SCHEMA_SHA256


def _m4_owned_structure_is_valid(
    connection: Connection,
    expected_digest: str,
    *,
    expected_triggers: frozenset[str] = frozenset(),
    additional_tables: frozenset[str] = frozenset(),
    additional_indexes: frozenset[str] = frozenset(),
) -> bool:
    """Verify exact reviewed M4 schema; never inspect stored business values."""
    expected = (
        IAM_TABLES
        | REGISTRY_TABLES
        | PROVIDER_SYSTEM_TABLES
        | COLLECTION_TABLES
        | CAPACITY_TABLES
        | RUNTIME_TABLES
        | ALERT_TABLES
        | IAM_INDEXES
        | REGISTRY_INDEXES
        | PROVIDER_SYSTEM_INDEXES
        | COLLECTION_INDEXES
        | CAPACITY_INDEXES
        | RUNTIME_INDEXES
        | ALERT_INDEXES
        | expected_triggers
        | additional_tables
        | additional_indexes
    )
    rows = connection.exec_driver_sql(
        "SELECT type, name, sql FROM sqlite_schema "
        "WHERE type IN ('table', 'index', 'trigger') ORDER BY type, name LIMIT 513"
    ).fetchall()
    definitions: list[str] = []
    names: set[str] = set()
    for kind, name, sql in rows:
        if name not in expected:
            continue
        if not isinstance(sql, str):
            return False
        names.add(name)
        definitions.append(f"{kind}|{name}|{' '.join(sql.split())}")
    return (
        names == expected
        and hashlib.sha256("\n".join(definitions).encode("utf-8")).hexdigest()
        == expected_digest
    )


def _marker_structure_is_valid(connection: Connection) -> bool:
    """Exact admitted Alembic marker, including otherwise invisible constraints.

    All statements/identifiers are code-owned. Only technical schema metadata is
    read, never business content. SQL text remains inside this validator and is
    not returned or attached to errors. Any externally changed structure refuses.
    """
    expected: tuple[tuple[str, list[tuple[object, ...]]], ...] = (
        (
            "PRAGMA table_xinfo(alembic_version)",
            [(0, "version_num", "VARCHAR(32)", 1, None, 1, 0)],
        ),
        (
            "PRAGMA index_list(alembic_version)",
            [(0, "sqlite_autoindex_alembic_version_1", 1, "pk", 0)],
        ),
        (
            "PRAGMA index_xinfo(sqlite_autoindex_alembic_version_1)",
            [(0, 0, "version_num", 0, "BINARY", 1), (1, -1, None, 0, "BINARY", 0)],
        ),
        ("PRAGMA foreign_key_list(alembic_version)", []),
    )
    for statement, rows in expected:
        actual = [
            tuple(row) for row in connection.exec_driver_sql(statement).fetchmany(3)
        ]
        if actual != rows:
            return False
    definition = connection.exec_driver_sql(
        "SELECT sql FROM sqlite_schema WHERE type='table' AND name='alembic_version'"
    ).scalar()
    # PRAGMA does not expose CHECK expressions or the PK constraint name. The
    # pinned Alembic dialect emits this one statement for the approved anchor.
    return isinstance(definition, str) and " ".join(definition.split()) == (
        "CREATE TABLE alembic_version ( version_num VARCHAR(32) NOT NULL, "
        "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num) )"
    )


def InspectSchemaCompatibilityV1(
    database_ref: DatabaseRefV1,
    application_range: ApplicationSchemaRangeV1,
    mode: DatabaseOpenModeV1,
) -> SchemaCompatibilityViewV1:
    """Read-only inspection. Never creates a file, DDL, revision or repair."""
    state: SchemaState = "policy_incompatible"
    current: str | None = None
    integrity: Literal["passed", "failed", "not_checked"] = "not_checked"
    policy: Literal["passed", "failed", "not_checked"] = "not_checked"
    catalog_version = "unknown"
    try:
        catalog = load_migration_catalog()
        catalog_version = catalog.version
        if application_range.catalog_digest != catalog.digest:
            state = "checksum_mismatch"
        elif mode not in {"runtime_read_only", "runtime_read_write"}:
            state = "policy_incompatible"
        elif database_ref.validate(missing_ok=True) is None:
            state = "missing"
        else:
            with open_sqlite_inspection(database_ref) as connection:
                state, current = _inspect(connection, application_range)
                policy = "passed"
                integrity = "failed" if state == "corrupt" else "passed"
    except SchemaCompatibilityError:
        state = "checksum_mismatch"
    except SqlitePolicyError as error:
        states: dict[str, SchemaState] = {
            "database_missing": "missing",
            "persistence_busy": "locked",
            "database_inspection_requires_quiescence": "locked",
            "database_inspection_changed": "locked",
            "database_identity_changed": "locked",
            "persistence_corrupt": "corrupt",
            "database_policy_incompatible": "policy_incompatible",
        }
        state = states.get(error.code, "unreadable")
        if state == "policy_incompatible":
            policy = "failed"
        if state == "corrupt":
            integrity = "failed"
    except OSError:
        state = "unreadable"
    return SchemaCompatibilityViewV1(
        state,
        current,
        application_range,
        integrity,
        policy,
        state in {"missing", "empty", "upgrade_required"},
        (state,),
        datetime.now(UTC),
        catalog_version,
        mode,
    )


def RequireWritableSchemaV1(view: SchemaCompatibilityViewV1) -> WritableSchemaReceiptV1:
    """A readiness receipt, not a connection or authorization for migration."""
    if (
        view.state != "compatible"
        or view.current_revision != view.application_range.migration_target_revision
        or view.integrity_state != "passed"
        or view.policy_state != "passed"
        or view.mode != "runtime_read_write"
        or view.migration_required
        or view.application_range != application_schema_range()
    ):
        raise SchemaCompatibilityError("schema_not_writable") from None
    return WritableSchemaReceiptV1(
        view.current_revision, view.application_range.catalog_digest, view.checked_at
    )


def migrate_to_head(
    database_ref: DatabaseRefV1, *, migrations_path: Path = MIGRATIONS_PATH
) -> None:
    """Explicit offline fresh M2 bootstrap through real Alembic; no upgrades.

    BEGIN IMMEDIATE serializes competing writers. On failure rollback/close and
    preserve the exact target; there is no delete, retry, downgrade or recovery
    claim. AUTO-MIGRATE's later backup/quiescence workflow remains separate.
    """
    catalog = load_migration_catalog(migrations_path)
    exists = database_ref.validate(missing_ok=True) is not None
    if exists:
        view = InspectSchemaCompatibilityV1(
            database_ref, catalog.revisions[-1].schema_range, "runtime_read_write"
        )
        if view.state == "compatible":
            return
        raise SchemaCompatibilityError("migration_preflight_refused") from None
    failure: str | None = None
    try:
        with open_sqlite_database(database_ref, "migration_initialize") as handle:
            with handle.connect() as connection:
                connection.exec_driver_sql("BEGIN IMMEDIATE")
                state, _ = _inspect(connection, catalog.revisions[-1].schema_range)
                if state != "empty":
                    raise SchemaCompatibilityError("migration_preflight_refused")
                config = Config()
                config.set_main_option(
                    "script_location", str(migrations_path).replace("%", "%%")
                )
                config.attributes.update(
                    connection=connection,
                    migrations_path=migrations_path,
                    catalog_digest=catalog.digest,
                )
                command.upgrade(config, catalog.head)
                if (
                    _inspect(connection, catalog.revisions[-1].schema_range)[0]
                    != "compatible"
                    or connection.exec_driver_sql("PRAGMA integrity_check")
                    .scalars()
                    .fetchmany(2)
                    != ["ok"]
                    or connection.exec_driver_sql("PRAGMA foreign_key_check").first()
                    is not None
                ):
                    raise SchemaCompatibilityError("migration_validation_failed")
                connection.commit()
    except (SchemaCompatibilityError, SqlitePolicyError) as error:
        failure = error.code
    except Exception:
        # Alembic boundary: never expose script paths, SQL or stored values.
        failure = "migration_failed"
    if failure is not None:
        raise SchemaCompatibilityError(failure) from None

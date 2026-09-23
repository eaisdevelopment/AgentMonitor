"""M06 metrics, runtime graphs, and evidence-qualified correlation."""

from types import MappingProxyType

import sqlalchemy as sa
from alembic import op

revision = "v1_0601"
down_revision = "v1_0600"
branch_labels = None
depends_on = None

TABLES = (
    "runtime_metric_observation",
    "runtime_session_process_link",
    "runtime_session_relationship",
    "runtime_correlation_evidence",
    "runtime_session_correlation_decision",
)

_UTC_GLOB = (
    "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T"
    "[0-9][0-9]:[0-9][0-9]:[0-9][0-9]."
    "[0-9][0-9][0-9][0-9][0-9][0-9]Z"
)

METADATA = MappingProxyType(
    {
        "revision": "v1_0601",
        "parent_revision": "v1_0600",
        "owner": "M06",
        "plan_id": "PLAN-M06",
        "requirement_ids": (
            "FR-DISC-004",
            "FR-DISC-005",
            "FR-DISC-006",
            "AC-PROC-002",
            "AC-PROC-003",
            "NFR-DATA-001",
        ),
        "schema_range": (
            "v1_0601",
            "v1_0601",
            "v1_0601",
            "v1_0601",
            "v1_0601",
        ),
        "tables": (
            "runtime_metric_observation",
            "runtime_session_process_link",
            "runtime_session_relationship",
            "runtime_correlation_evidence",
            "runtime_session_correlation_decision",
        ),
        "portability_notes": (
            "partial current-row uniqueness requires PostgreSQL equivalents",
        ),
        "lock_policy": "exclusive_migration_and_begin_immediate",
        "downtime_policy": "offline_additive_schema_migration",
        "expected_data_volume": "zero_runtime_rows_on_initial_install",
        "backup_prerequisite": "required_existing_database",
        "validation_ids": (
            "single_head",
            "m06_metric_graph_correlation_tables",
            "foreign_key_check",
            "full_integrity",
        ),
        "recovery_policy": (
            "preserve_failed_database_and_restore_verified_backup_or_forward_fix"
        ),
        "reviewer": "M06-PLAN-DB-security-review",
    }
)


def _utc(column: str) -> str:
    return (
        f"length({column})=27 AND {column} GLOB '{_UTC_GLOB}' "
        f"AND julianday({column}) IS NOT NULL "
        f"AND date(substr({column},1,10),'+0 days')=substr({column},1,10)"
    )


def _nullable_utc(column: str) -> str:
    return f"{column} IS NULL OR ({_utc(column)})"


def upgrade() -> None:
    op.create_table(
        "runtime_metric_observation",
        sa.Column("metric_id", sa.String(64), primary_key=True),
        sa.Column("session_id", sa.String(64)),
        sa.Column("process_id", sa.String(64)),
        sa.Column("collection_run_id", sa.String(64), nullable=False),
        sa.Column("metric_kind", sa.String(64), nullable=False),
        sa.Column("coefficient", sa.String(80), nullable=False),
        sa.Column("scale", sa.Integer(), nullable=False),
        sa.Column("unit", sa.String(64), nullable=False),
        sa.Column("scope", sa.String(64), nullable=False),
        sa.Column("measurement_semantics", sa.String(16), nullable=False),
        sa.Column("overlap_class", sa.String(24), nullable=False),
        sa.Column("interval_start", sa.String(40)),
        sa.Column("interval_end", sa.String(40)),
        sa.Column("observed_at", sa.String(40), nullable=False),
        sa.Column("collected_at", sa.String(40), nullable=False),
        sa.Column("stored_at", sa.String(40), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("source_version", sa.String(64), nullable=False),
        sa.Column("parser_version", sa.String(64), nullable=False),
        sa.Column("provider_version", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["runtime_session.session_id"]),
        sa.ForeignKeyConstraint(
            ["process_id"], ["runtime_process_instance.process_id"]
        ),
        sa.CheckConstraint(
            "session_id IS NOT NULL OR process_id IS NOT NULL",
            name="ck_runtime_metric_subject",
        ),
        sa.CheckConstraint(
            "length(metric_kind)>0 AND length(coefficient)>0 "
            "AND length(unit)>0 AND length(scope)>0 AND length(source_id)>0 "
            "AND length(source_version)>0 AND length(parser_version)>0 "
            "AND length(provider_version)>0",
            name="ck_runtime_metric_required_values",
        ),
        sa.CheckConstraint(
            "length(coefficient)<=80 AND (coefficient='0' OR "
            "(substr(coefficient,1,1) BETWEEN '1' AND '9' "
            "AND substr(coefficient,2) NOT GLOB '*[^0-9]*') OR "
            "(substr(coefficient,1,1)='-' "
            "AND substr(coefficient,2,1) BETWEEN '1' AND '9' "
            "AND substr(coefficient,3) NOT GLOB '*[^0-9]*'))",
            name="ck_runtime_metric_coefficient",
        ),
        sa.CheckConstraint(
            "scale BETWEEN 0 AND 18",
            name="ck_runtime_metric_scale",
        ),
        sa.CheckConstraint(
            "measurement_semantics IN ('interval','cumulative','gauge')",
            name="ck_runtime_metric_semantics",
        ),
        sa.CheckConstraint(
            "overlap_class IN ('disjoint','inclusive','unknown','not_applicable')",
            name="ck_runtime_metric_overlap",
        ),
        sa.CheckConstraint(
            "(measurement_semantics IN ('interval','cumulative') "
            "AND interval_start IS NOT NULL AND interval_end IS NOT NULL "
            "AND overlap_class IN ('disjoint','inclusive','unknown')) OR "
            "(measurement_semantics='gauge' AND interval_start IS NULL "
            "AND interval_end IS NULL AND overlap_class='not_applicable')",
            name="ck_runtime_metric_interval_pair",
        ),
        sa.CheckConstraint(
            "interval_start IS NULL OR interval_end >= interval_start",
            name="ck_runtime_metric_interval_order",
        ),
        sa.CheckConstraint(
            f"({_nullable_utc('interval_start')}) AND "
            f"({_nullable_utc('interval_end')}) AND ({_utc('observed_at')}) "
            f"AND ({_utc('collected_at')}) AND ({_utc('stored_at')})",
            name="ck_runtime_metric_utc",
        ),
        sa.CheckConstraint(
            "stored_at >= collected_at",
            name="ck_runtime_metric_storage_time",
        ),
    )
    op.create_table(
        "runtime_session_process_link",
        sa.Column("link_id", sa.String(64), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("process_id", sa.String(64), nullable=False),
        sa.Column("relationship_kind", sa.String(24), nullable=False),
        sa.Column("evidence_class", sa.String(24), nullable=False),
        sa.Column("certainty", sa.String(16), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("source_version", sa.String(64), nullable=False),
        sa.Column("valid_from", sa.String(40), nullable=False),
        sa.Column("valid_until", sa.String(40)),
        sa.Column("is_current", sa.Integer(), nullable=False),
        sa.Column("conflict_state", sa.String(24), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["runtime_session.session_id"]),
        sa.ForeignKeyConstraint(
            ["process_id"], ["runtime_process_instance.process_id"]
        ),
        sa.CheckConstraint(
            "relationship_kind IN ('primary','worker','wrapper','observer','unknown')",
            name="ck_runtime_link_kind",
        ),
        sa.CheckConstraint(
            "evidence_class IN ('strong','corroborated','weak')",
            name="ck_runtime_link_evidence",
        ),
        sa.CheckConstraint(
            "certainty IN ('definitive','inferred','unknown')",
            name="ck_runtime_link_certainty",
        ),
        sa.CheckConstraint("is_current IN (0,1)", name="ck_runtime_link_current"),
        sa.CheckConstraint(
            "conflict_state IN ('clear','conflict','invalidated')",
            name="ck_runtime_link_conflict",
        ),
        sa.CheckConstraint(
            "(is_current=1 AND valid_until IS NULL AND conflict_state='clear') OR "
            "(is_current=0 AND valid_until IS NOT NULL)",
            name="ck_runtime_link_current_validity",
        ),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from",
            name="ck_runtime_link_validity_order",
        ),
        sa.CheckConstraint(
            f"({_utc('valid_from')}) AND ({_nullable_utc('valid_until')})",
            name="ck_runtime_link_utc",
        ),
    )
    op.create_table(
        "runtime_session_relationship",
        sa.Column("relationship_id", sa.String(64), primary_key=True),
        sa.Column("child_session_id", sa.String(64), nullable=False),
        sa.Column("parent_session_id", sa.String(64), nullable=False),
        sa.Column("relationship_kind", sa.String(32), nullable=False),
        sa.Column("evidence_class", sa.String(24), nullable=False),
        sa.Column("certainty", sa.String(16), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("source_version", sa.String(64), nullable=False),
        sa.Column("valid_from", sa.String(40), nullable=False),
        sa.Column("valid_until", sa.String(40)),
        sa.Column("is_current", sa.Integer(), nullable=False),
        sa.Column("conflict_state", sa.String(24), nullable=False),
        sa.Column("orphan_reason_code", sa.String(128)),
        sa.ForeignKeyConstraint(["child_session_id"], ["runtime_session.session_id"]),
        sa.ForeignKeyConstraint(["parent_session_id"], ["runtime_session.session_id"]),
        sa.CheckConstraint(
            "child_session_id <> parent_session_id",
            name="ck_runtime_relationship_not_self",
        ),
        sa.CheckConstraint(
            "relationship_kind IN ('subagent','worker','wrapper','owner_confirmed')",
            name="ck_runtime_relationship_kind",
        ),
        sa.CheckConstraint(
            "evidence_class IN ('strong','corroborated','weak')",
            name="ck_runtime_relationship_evidence",
        ),
        sa.CheckConstraint(
            "certainty IN ('definitive','inferred','unknown')",
            name="ck_runtime_relationship_certainty",
        ),
        sa.CheckConstraint(
            "is_current IN (0,1)",
            name="ck_runtime_relationship_current",
        ),
        sa.CheckConstraint(
            "conflict_state IN ('clear','conflict','invalidated','orphan')",
            name="ck_runtime_relationship_conflict",
        ),
        sa.CheckConstraint(
            "(is_current=1 AND valid_until IS NULL AND conflict_state='clear') OR "
            "(is_current=0 AND valid_until IS NOT NULL)",
            name="ck_runtime_relationship_current_validity",
        ),
        sa.CheckConstraint(
            "(conflict_state='clear' AND orphan_reason_code IS NULL) OR "
            "(conflict_state<>'clear' AND orphan_reason_code IS NOT NULL)",
            name="ck_runtime_relationship_reason_pair",
        ),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from",
            name="ck_runtime_relationship_validity_order",
        ),
        sa.CheckConstraint(
            f"({_utc('valid_from')}) AND ({_nullable_utc('valid_until')})",
            name="ck_runtime_relationship_utc",
        ),
    )
    op.create_table(
        "runtime_correlation_evidence",
        sa.Column("evidence_id", sa.String(64), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("evidence_class", sa.String(24), nullable=False),
        sa.Column("rule_id", sa.String(128), nullable=False),
        sa.Column("account_id", sa.String(64)),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("source_version", sa.String(64), nullable=False),
        sa.Column("reason_code", sa.String(128), nullable=False),
        sa.Column("observed_at", sa.String(40), nullable=False),
        sa.Column("expires_at", sa.String(40)),
        sa.Column("is_valid", sa.Integer(), nullable=False),
        sa.Column("conflict_state", sa.String(24), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["runtime_session.session_id"]),
        sa.CheckConstraint(
            "evidence_class IN ('strong','corroborated','weak')",
            name="ck_runtime_evidence_class",
        ),
        sa.CheckConstraint(
            "(evidence_class='strong' AND account_id IS NOT NULL) OR "
            "(evidence_class<>'strong' AND account_id IS NULL)",
            name="ck_runtime_evidence_account_pair",
        ),
        sa.CheckConstraint("is_valid IN (0,1)", name="ck_runtime_evidence_valid"),
        sa.CheckConstraint(
            "conflict_state IN ('clear','conflict','invalidated')",
            name="ck_runtime_evidence_conflict",
        ),
        sa.CheckConstraint(
            "(is_valid=1 AND conflict_state='clear') OR "
            "(is_valid=0 AND conflict_state<>'clear')",
            name="ck_runtime_evidence_validity_pair",
        ),
        sa.CheckConstraint(
            "expires_at IS NULL OR expires_at >= observed_at",
            name="ck_runtime_evidence_expiry_order",
        ),
        sa.CheckConstraint(
            f"({_utc('observed_at')}) AND ({_nullable_utc('expires_at')})",
            name="ck_runtime_evidence_utc",
        ),
    )
    op.create_table(
        "runtime_session_correlation_decision",
        sa.Column("decision_id", sa.String(64), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("decision_state", sa.String(32), nullable=False),
        sa.Column("account_id", sa.String(64)),
        sa.Column("evidence_set_digest", sa.String(64), nullable=False),
        sa.Column("reason_code", sa.String(128), nullable=False),
        sa.Column("decided_at", sa.String(40), nullable=False),
        sa.Column("confirmed_at", sa.String(40)),
        sa.Column("actor_id", sa.String(64)),
        sa.Column("valid_until", sa.String(40)),
        sa.Column("is_current", sa.Integer(), nullable=False),
        sa.Column("decision_version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["runtime_session.session_id"]),
        sa.CheckConstraint(
            "decision_state IN ('unresolved','automatic_matched',"
            "'confirmation_required','conflict','unsupported','owner_confirmed',"
            "'invalidated')",
            name="ck_runtime_decision_state",
        ),
        sa.CheckConstraint(
            "(decision_state IN ('automatic_matched','owner_confirmed') "
            "AND account_id IS NOT NULL) OR "
            "(decision_state NOT IN ('automatic_matched','owner_confirmed') "
            "AND account_id IS NULL)",
            name="ck_runtime_decision_account_pair",
        ),
        sa.CheckConstraint(
            "(decision_state='owner_confirmed' AND actor_id IS NOT NULL "
            "AND confirmed_at IS NOT NULL) OR "
            "(decision_state<>'owner_confirmed' AND actor_id IS NULL "
            "AND confirmed_at IS NULL)",
            name="ck_runtime_decision_confirmation_pair",
        ),
        sa.CheckConstraint(
            "(is_current=1 AND valid_until IS NULL) OR "
            "(is_current=0 AND valid_until IS NOT NULL)",
            name="ck_runtime_decision_validity_pair",
        ),
        sa.CheckConstraint(
            "is_current IN (0,1) AND decision_version > 0",
            name="ck_runtime_decision_current_version",
        ),
        sa.CheckConstraint(
            "length(evidence_set_digest)=64",
            name="ck_runtime_decision_digest",
        ),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until >= decided_at",
            name="ck_runtime_decision_validity_order",
        ),
        sa.CheckConstraint(
            f"({_utc('decided_at')}) AND ({_nullable_utc('confirmed_at')}) "
            f"AND ({_nullable_utc('valid_until')})",
            name="ck_runtime_decision_utc",
        ),
    )


def downgrade() -> None:
    raise ValueError("migration_downgrade_unsupported")

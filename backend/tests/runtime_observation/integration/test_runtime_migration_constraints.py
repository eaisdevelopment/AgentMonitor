"""M06 migration invariants against real file-backed SQLite.

The rows in this module are structural DDL probes.  They are not provider
observations and make no live-provider claim.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

BACKEND = Path(__file__).resolve().parents[3]
VERSIONS = BACKEND / "migrations" / "versions"
sys.path.insert(0, str(VERSIONS))

MIGRATION_NAMES = (
    "v1_0600_m06_runtime_core",
    "v1_0601_m06_runtime_correlation",
    "v1_0602_m06_runtime_state_outbox",
    "v1_0603_m06_runtime_indexes",
)
MIGRATIONS = tuple(importlib.import_module(name) for name in MIGRATION_NAMES)
UTC_1 = "2026-09-22T10:00:00.000000Z"
UTC_2 = "2026-09-22T10:01:00.000000Z"


def _apply(connection: Connection, count: int = 4) -> None:
    context = MigrationContext.configure(connection)
    for migration in MIGRATIONS[:count]:
        with Operations.context(context):
            migration.upgrade()


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Connection]:
    path = tmp_path / "runtime-constraints.db"
    engine = sa.create_engine(f"sqlite:///{path}")
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        _apply(connection)
        connection.commit()
        assert path.is_file()
        yield connection
    engine.dispose()


def _insert_process(
    connection: Connection,
    *,
    process_id: str = "process-1",
    platform_scope_id: str = "boot-scope-1",
    executable_identity: str | None = None,
    provider_key: str | None = None,
    installation_id: str | None = None,
    first_observed_at: str = UTC_1,
) -> None:
    connection.execute(
        sa.text(
            """
            INSERT INTO runtime_process_instance (
                process_id, platform_source, platform_scope_id, pid,
                start_time_ticks, executable_identity, executable_label, provider_key,
                installation_id, first_observed_at, last_observed_at,
                presence_state, current_snapshot_id, record_version
            ) VALUES (
                :process_id, 'linux-procfs-v1', :platform_scope_id, 101,
                123456, :executable_identity, 'claude', :provider_key, :installation_id,
                :first_observed_at, :last_observed_at, 'running', NULL, 1
            )
            """
        ),
        {
            "process_id": process_id,
            "platform_scope_id": platform_scope_id,
            "executable_identity": executable_identity,
            "provider_key": provider_key,
            "installation_id": installation_id,
            "first_observed_at": first_observed_at,
            "last_observed_at": UTC_2,
        },
    )


def _insert_session(connection: Connection, session_id: str = "session-1") -> None:
    connection.execute(
        sa.text(
            """
            INSERT INTO runtime_session (
                session_id, provider_key, installation_id, identity_kind,
                identity_value, first_observed_at, last_observed_at,
                current_observation_id, correlation_state, account_id,
                current_decision_id, record_version
            ) VALUES (
                :session_id, 'claude', 'installation-1', 'process_instance',
                :session_id, :first_observed_at, :last_observed_at,
                NULL, 'unresolved', NULL, NULL, 1
            )
            """
        ),
        {
            "session_id": session_id,
            "first_observed_at": UTC_1,
            "last_observed_at": UTC_2,
        },
    )


@pytest.mark.parametrize("migration_index", range(len(MIGRATIONS)))
def test_runtime_migration_downgrades_fail_closed_without_mutating_schema(
    tmp_path: Path,
    migration_index: int,
) -> None:
    path = tmp_path / f"runtime-downgrade-{migration_index}.db"
    engine = sa.create_engine(f"sqlite:///{path}")
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        _apply(connection)
        connection.commit()
        inspector = sa.inspect(connection)
        tables_before = set(inspector.get_table_names())
        indexes_before = {
            (table, index["name"])
            for table in tables_before
            for index in inspector.get_indexes(table)
        }

        context = MigrationContext.configure(connection)
        with Operations.context(context):
            with pytest.raises(
                ValueError,
                match="^migration_downgrade_unsupported$",
            ):
                MIGRATIONS[migration_index].downgrade()

        inspector = sa.inspect(connection)
        tables_after = set(inspector.get_table_names())
        indexes_after = {
            (table, index["name"])
            for table in tables_after
            for index in inspector.get_indexes(table)
        }
        assert tables_after == tables_before
        assert indexes_after == indexes_before
    engine.dispose()


def test_revision_allocation_places_metrics_only_in_v1_0601(tmp_path: Path) -> None:
    path = tmp_path / "runtime-allocation.db"
    engine = sa.create_engine(f"sqlite:///{path}")
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        _apply(connection, count=1)
        tables_after_0600 = set(sa.inspect(connection).get_table_names())
        assert "runtime_metric_observation" not in tables_after_0600
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            MIGRATIONS[1].upgrade()
        assert "runtime_metric_observation" in set(
            sa.inspect(connection).get_table_names()
        )
    engine.dispose()


def test_process_identity_is_boot_scoped_and_generic_attribution_is_nullable(
    database: Connection,
) -> None:
    _insert_process(database)
    row = database.execute(
        sa.text(
            "SELECT platform_scope_id, provider_key, installation_id "
            "FROM runtime_process_instance"
        )
    ).one()
    assert row == ("boot-scope-1", None, None)

    _insert_process(
        database,
        process_id="process-another-boot",
        platform_scope_id="boot-scope-2",
    )
    with pytest.raises(IntegrityError):
        _insert_process(
            database,
            process_id="process-duplicate-identity",
            platform_scope_id="boot-scope-1",
        )

    with pytest.raises(IntegrityError):
        _insert_process(database, process_id="process-2", platform_scope_id="")
    with pytest.raises(IntegrityError):
        _insert_process(
            database,
            process_id="process-3",
            executable_identity="verified-executable-1",
            provider_key=None,
            installation_id="installation-without-provider",
        )
    with pytest.raises(IntegrityError):
        _insert_process(
            database,
            process_id="process-4",
            first_observed_at="2026-09-22T10:00:00+00:00",
        )


@pytest.mark.parametrize(
    ("field", "state", "value", "unit", "reason"),
    [
        ("parent_pid", "present", None, "pid", None),
        ("user_cpu", "present", 1, None, None),
        ("system_cpu", "unsupported", 1, "ticks", "unsupported"),
        ("resident", "changed_during_read", None, None, None),
        ("thread", "unsafe_layout", 1, "count", "unsafe_layout"),
        ("kernel_state", "redacted_by_policy", "R", "linux-state", "redacted"),
        ("executable_label", "present", None, None, None),
    ],
)
def test_snapshot_optional_fields_require_exact_state_value_unit_reason_pairing(
    database: Connection,
    field: str,
    state: str,
    value: int | str | None,
    unit: str | None,
    reason: str | None,
) -> None:
    _insert_process(database)
    values: dict[str, object] = {
        "snapshot_id": f"snapshot-{field}",
        "process_id": "process-1",
        "collection_run_id": "run-1",
        "source_observation_id": f"source-{field}",
        "observed_at": UTC_1,
        "collected_at": UTC_1,
        "stored_at": UTC_2,
        "source_id": "linux-procfs-v1",
        "source_version": "1.0.0",
        "adapter_version": "1.0.0",
        "presence_state": "running",
        "executable_label_state": "present",
        "executable_label": "claude",
        "executable_label_reason_code": None,
        "parent_pid_state": "present",
        "parent_pid": 1,
        "parent_pid_unit": "pid",
        "parent_pid_reason_code": None,
        "user_cpu_state": "present",
        "user_cpu_ticks": 1,
        "user_cpu_unit": "ticks",
        "user_cpu_reason_code": None,
        "system_cpu_state": "present",
        "system_cpu_ticks": 1,
        "system_cpu_unit": "ticks",
        "system_cpu_reason_code": None,
        "resident_state": "present",
        "resident_pages": 1,
        "resident_unit": "pages",
        "resident_reason_code": None,
        "thread_state": "present",
        "thread_count": 1,
        "thread_unit": "count",
        "thread_reason_code": None,
        "kernel_state_state": "present",
        "kernel_state": "R",
        "kernel_state_unit": "linux-state",
        "kernel_state_reason_code": None,
        "clock_ticks_per_second": 100,
        "page_size_bytes": 4096,
    }
    value_columns = {
        "parent_pid": "parent_pid",
        "user_cpu": "user_cpu_ticks",
        "system_cpu": "system_cpu_ticks",
        "resident": "resident_pages",
        "thread": "thread_count",
        "kernel_state": "kernel_state",
        "executable_label": "executable_label",
    }
    values[f"{field}_state"] = state
    values[value_columns[field]] = value
    if field != "executable_label":
        values[f"{field}_unit"] = unit
    values[f"{field}_reason_code"] = reason
    columns = ", ".join(values)
    binds = ", ".join(f":{name}" for name in values)
    with pytest.raises(IntegrityError):
        database.execute(
            sa.text(
                f"INSERT INTO runtime_process_snapshot ({columns}) VALUES ({binds})"
            ),
            values,
        )


def test_session_activity_availability_and_metric_semantics_are_constrained(
    database: Connection,
) -> None:
    _insert_process(database)
    _insert_session(database)
    session_values = {
        "observation_id": "session-observation-1",
        "session_id": "session-1",
        "collection_run_id": "run-1",
        "source_observation_id": "provider-observation-1",
        "observed_at": UTC_1,
        "collected_at": UTC_1,
        "stored_at": UTC_2,
        "source_id": "claude-local-v1",
        "source_version": "1.0.0",
        "parser_version": "1.0.0",
        "provider_version": "2.1.278",
        "activity_state": "unverified_source",
        "activity_code": None,
        "activity_reason_code": "source_unverified",
    }
    database.execute(
        sa.text(
            """
            INSERT INTO runtime_session_observation (
                observation_id, session_id, collection_run_id,
                source_observation_id, observed_at, collected_at, stored_at,
                source_id, source_version, parser_version, provider_version,
                activity_state, activity_code, activity_reason_code
            ) VALUES (
                :observation_id, :session_id, :collection_run_id,
                :source_observation_id, :observed_at, :collected_at, :stored_at,
                :source_id, :source_version, :parser_version, :provider_version,
                :activity_state, :activity_code, :activity_reason_code
            )
            """
        ),
        session_values,
    )
    with pytest.raises(IntegrityError):
        database.execute(
            sa.text(
                "UPDATE runtime_session_observation SET activity_code='working' "
                "WHERE observation_id='session-observation-1'"
            )
        )

    metric_values = {
        "metric_id": "metric-1",
        "session_id": "session-1",
        "process_id": None,
        "collection_run_id": "run-1",
        "metric_kind": "tokens_total",
        "coefficient": "7",
        "scale": 0,
        "unit": "tokens",
        "scope": "session",
        "measurement_semantics": "interval",
        "overlap_class": "disjoint",
        "interval_start": UTC_1,
        "interval_end": UTC_2,
        "observed_at": UTC_2,
        "collected_at": UTC_2,
        "stored_at": UTC_2,
        "source_id": "claude-local-v1",
        "source_version": "1.0.0",
        "parser_version": "1.0.0",
        "provider_version": "2.1.278",
    }
    columns = ", ".join(metric_values)
    binds = ", ".join(f":{name}" for name in metric_values)
    database.execute(
        sa.text(f"INSERT INTO runtime_metric_observation ({columns}) VALUES ({binds})"),
        metric_values,
    )
    with pytest.raises(IntegrityError):
        database.execute(
            sa.text(
                "UPDATE runtime_metric_observation SET interval_end=NULL "
                "WHERE metric_id='metric-1'"
            )
        )
    with pytest.raises(IntegrityError):
        database.execute(
            sa.text(
                "UPDATE runtime_metric_observation SET overlap_class='guessed' "
                "WHERE metric_id='metric-1'"
            )
        )
    cumulative_values = dict(
        metric_values,
        metric_id="metric-cumulative",
        measurement_semantics="cumulative",
        overlap_class="inclusive",
    )
    database.execute(
        sa.text(f"INSERT INTO runtime_metric_observation ({columns}) VALUES ({binds})"),
        cumulative_values,
    )
    with pytest.raises(IntegrityError):
        database.execute(
            sa.text(
                "UPDATE runtime_metric_observation SET interval_start=NULL, "
                "interval_end=NULL WHERE metric_id='metric-cumulative'"
            )
        )
    gauge_values = dict(
        metric_values,
        metric_id="metric-gauge",
        measurement_semantics="gauge",
        overlap_class="not_applicable",
        interval_start=None,
        interval_end=None,
    )
    database.execute(
        sa.text(f"INSERT INTO runtime_metric_observation ({columns}) VALUES ({binds})"),
        gauge_values,
    )
    with pytest.raises(IntegrityError):
        database.execute(
            sa.text(
                "UPDATE runtime_metric_observation SET coefficient='00' "
                "WHERE metric_id='metric-gauge'"
            )
        )
    with pytest.raises(IntegrityError):
        database.execute(
            sa.text(
                "UPDATE runtime_metric_observation SET parser_version=NULL "
                "WHERE metric_id='metric-gauge'"
            )
        )


def test_links_relationships_and_correlation_enforce_current_truth(
    database: Connection,
) -> None:
    _insert_process(database)
    _insert_session(database, "session-child")
    _insert_session(database, "session-parent-a")
    _insert_session(database, "session-parent-b")
    database.execute(
        sa.text(
            """
            INSERT INTO runtime_session_process_link (
                link_id, session_id, process_id, relationship_kind,
                evidence_class, certainty, source_id, source_version,
                valid_from, valid_until, is_current, conflict_state
            ) VALUES (
                'link-1', 'session-child', 'process-1', 'primary', 'strong',
                'definitive', 'claude-local-v1', '1.0.0', :valid_from,
                NULL, 1, 'clear'
            )
            """
        ),
        {"valid_from": UTC_1},
    )
    with pytest.raises(IntegrityError):
        database.execute(
            sa.text(
                "UPDATE runtime_session_process_link SET valid_until=:valid_until "
                "WHERE link_id='link-1'"
            ),
            {"valid_until": UTC_2},
        )
    database.execute(
        sa.text(
            """
            INSERT INTO runtime_session_relationship (
                relationship_id, child_session_id, parent_session_id,
                relationship_kind, evidence_class, certainty, source_id,
                source_version, valid_from, valid_until, is_current,
                conflict_state, orphan_reason_code
            ) VALUES (
                'relationship-1', 'session-child', 'session-parent-a',
                'subagent', 'strong', 'definitive', 'claude-local-v1',
                '1.0.0', :valid_from, NULL, 1, 'clear', NULL
            )
            """
        ),
        {"valid_from": UTC_1},
    )
    with pytest.raises(IntegrityError):
        database.execute(
            sa.text(
                """
                INSERT INTO runtime_session_relationship (
                    relationship_id, child_session_id, parent_session_id,
                    relationship_kind, evidence_class, certainty, source_id,
                    source_version, valid_from, valid_until, is_current,
                    conflict_state, orphan_reason_code
                ) VALUES (
                    'relationship-2', 'session-child', 'session-parent-b',
                    'subagent', 'strong', 'definitive', 'claude-local-v1',
                    '1.0.0', :valid_from, NULL, 1, 'clear', NULL
                )
                """
            ),
            {"valid_from": UTC_1},
        )

    decision_base = {
        "session_id": "session-child",
        "evidence_set_digest": "a" * 64,
        "reason_code": "approved_rule",
        "decided_at": UTC_1,
    }
    with pytest.raises(IntegrityError):
        database.execute(
            sa.text(
                """
                INSERT INTO runtime_session_correlation_decision (
                    decision_id, session_id, decision_state, account_id,
                    evidence_set_digest, reason_code, decided_at, is_current,
                    decision_version
                ) VALUES (
                    'decision-invalid', :session_id, 'owner_confirmed', NULL,
                    :evidence_set_digest, :reason_code, :decided_at, 1, 1
                )
                """
            ),
            decision_base,
        )
    database.execute(
        sa.text(
            """
            INSERT INTO runtime_correlation_evidence (
                evidence_id, session_id, evidence_class, rule_id, account_id,
                source_id, source_version, reason_code, observed_at, expires_at,
                is_valid, conflict_state
            ) VALUES (
                'evidence-weak', 'session-child', 'weak', 'process-only-v1',
                NULL, 'claude-local-v1', '1.0.0', 'insufficient_identity',
                :observed_at, NULL, 1, 'clear'
            )
            """
        ),
        {"observed_at": UTC_1},
    )
    with pytest.raises(IntegrityError):
        database.execute(
            sa.text(
                "UPDATE runtime_correlation_evidence SET account_id='account-1' "
                "WHERE evidence_id='evidence-weak'"
            )
        )


def test_policy_state_and_outbox_lifecycle_constraints(database: Connection) -> None:
    _insert_session(database)
    database.execute(
        sa.text(
            """
            INSERT INTO runtime_stall_policy (
                policy_id, scope_kind, scope_id, threshold_seconds, enabled,
                is_current, policy_version, actor_id, created_at, updated_at
            ) VALUES (
                'policy-global', 'global', 'global', 600, 1, 1, 1,
                'administrator-1', :created_at, :updated_at
            )
            """
        ),
        {"created_at": UTC_1, "updated_at": UTC_2},
    )
    with pytest.raises(IntegrityError):
        database.execute(
            sa.text(
                """
                INSERT INTO runtime_stall_policy (
                    policy_id, scope_kind, scope_id, threshold_seconds, enabled,
                    is_current, policy_version, actor_id, created_at, updated_at
                ) VALUES (
                    'policy-global-2', 'global', 'not-global', 600, 1, 0, 2,
                    'administrator-1', :created_at, :updated_at
                )
                """
            ),
            {"created_at": UTC_1, "updated_at": UTC_2},
        )
    with pytest.raises(IntegrityError):
        database.execute(
            sa.text(
                """
                INSERT INTO runtime_stall_policy (
                    policy_id, scope_kind, scope_id, threshold_seconds, enabled,
                    is_current, policy_version, actor_id, created_at, updated_at
                ) VALUES (
                    'policy-global-duplicate', 'global', 'global', 900, 1, 1, 2,
                    'administrator-1', :created_at, :updated_at
                )
                """
            ),
            {"created_at": UTC_1, "updated_at": UTC_2},
        )
    with pytest.raises(IntegrityError):
        database.execute(
            sa.text(
                """
                INSERT INTO runtime_state_transition (
                    transition_id, session_id, stream_sequence, prior_state,
                    current_state, certainty, reason_code, observed_at,
                    evaluated_at, runtime_revision
                ) VALUES (
                    'transition-1', 'session-1', 1, NULL, 'invented_state',
                    'definitive', 'invalid_state', :observed_at, :evaluated_at, 1
                )
                """
            ),
            {"observed_at": UTC_1, "evaluated_at": UTC_2},
        )

    event_values = {
        "event_id": "event-1",
        "event_type": "runtime.state.changed.v1",
        "event_schema": "runtime-state-changed.v1",
        "subject_id": "session-1",
        "stream_sequence": 1,
        "producer_sequence": 1,
        "correlation_id": "correlation-1",
        "causation_id": None,
        "payload_json": "{}",
        "occurred_at": UTC_1,
        "recorded_at": UTC_1,
        "available_at": UTC_1,
        "delivery_state": "pending",
        "claimed_at": None,
        "delivered_at": None,
        "attempt_count": 0,
    }
    columns = ", ".join(event_values)
    binds = ", ".join(f":{name}" for name in event_values)
    database.execute(
        sa.text(f"INSERT INTO runtime_event_outbox ({columns}) VALUES ({binds})"),
        event_values,
    )
    with pytest.raises(IntegrityError):
        database.execute(
            sa.text(
                "UPDATE runtime_event_outbox SET delivery_state='delivered', "
                "delivered_at=:delivered_at WHERE event_id='event-1'"
            ),
            {"delivered_at": UTC_2},
        )


def test_ingest_receipt_persists_closed_provenance_with_pair_constraints(
    database: Connection,
) -> None:
    values: dict[str, object] = {
        "receipt_id": "receipt-1",
        "collection_run_id": "run-1",
        "target_generation": 1,
        "capability_id": "local_runtime",
        "capability_schema_version": "runtime-observation.v1",
        "payload_schema": "runtime-observation.v1",
        "payload_digest": "a" * 64,
        "consumer_key": "runtime-observation",
        "consumer_version": "1.0.0",
        "provider_key": "claude",
        "adapter_id": "claude-local-runtime",
        "adapter_version": "1.0.0",
        "provider_protocol_version": "1.0.0",
        "source_id": "claude-local-v1",
        "source_class": "approved_local_metadata",
        "mechanism_version": "1.0.0",
        "parser_version": "1.0.0",
        "provider_version": "2.1.278",
        "provider_version_availability": "available",
        "observed_at": UTC_1,
        "observed_at_availability": "available",
        "collected_at": UTC_2,
        "freshness_deadline": UTC_2,
        "freshness_availability": "available",
        "freshness_policy_id": "runtime-local-v1",
        "precision": "exact",
        "confidence": "confirmed",
        "confidence_reason_code": "local_read_only_source",
        "value_kind": "provider_reported",
        "is_experimental": 0,
        "operation_id": "operation-1",
        "correlation_id": "correlation-1",
        "decision_reference": "runtime-source-decision-v1",
        "derivation_method": None,
        "fallback_lineage_json": "[]",
        "warnings_json": "[]",
        "input_observation_ids_json": "[]",
        "observation_set_digest": "b" * 64,
        "observation_ids_json": "[]",
        "affected_projection_ids_json": "[]",
        "projection_versions_json": "[]",
        "event_ids_json": "[]",
        "stored_at_start": UTC_2,
        "stored_at_end": UTC_2,
        "stored_at": UTC_2,
        "receipt_version": 1,
    }
    columns = ", ".join(values)
    binds = ", ".join(f":{name}" for name in values)
    database.execute(
        sa.text(f"INSERT INTO runtime_ingest_receipt ({columns}) VALUES ({binds})"),
        values,
    )
    with pytest.raises(IntegrityError):
        database.execute(
            sa.text(
                "UPDATE runtime_ingest_receipt SET provider_version=NULL "
                "WHERE receipt_id='receipt-1'"
            )
        )
    with pytest.raises(IntegrityError):
        database.execute(
            sa.text(
                "UPDATE runtime_ingest_receipt SET observed_at="
                "'2026-09-22T10:00:00+00:00' WHERE receipt_id='receipt-1'"
            )
        )
    with pytest.raises(IntegrityError):
        database.execute(
            sa.text(
                "UPDATE runtime_ingest_receipt SET value_kind='derived' "
                "WHERE receipt_id='receipt-1'"
            )
        )


def test_runtime_schema_contains_no_prohibited_content_columns(
    database: Connection,
) -> None:
    prohibited = {
        "prompt",
        "response",
        "command_line",
        "argv",
        "environment",
        "terminal_output",
        "tool_arguments",
        "source_content",
        "raw_payload",
    }
    for table in sa.inspect(database).get_table_names():
        columns = {item["name"] for item in sa.inspect(database).get_columns(table)}
        assert columns.isdisjoint(prohibited)

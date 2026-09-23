"""M03 compatibility persistence over the real file-backed SQLite chain."""

from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    InspectSchemaCompatibilityV1,
    application_schema_range,
    migrate_to_head,
)
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError


def test_v1_0300_creates_empty_provider_system_schema(tmp_path: Path) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)

    view = InspectSchemaCompatibilityV1(
        reference, application_schema_range(), "runtime_read_write"
    )
    assert view.state == "compatible"
    assert view.current_revision == "v1_0603"

    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            tables = set(
                connection.exec_driver_sql(
                    "SELECT name FROM sqlite_schema WHERE type='table' "
                    "AND name LIKE 'provider_system_%' ORDER BY name"
                ).scalars()
            )
            columns = {
                table: {
                    row[1]
                    for row in connection.exec_driver_sql(
                        f"PRAGMA table_info({table})"  # noqa: S608 - closed table set
                    )
                }
                for table in tables
            }
            integrity = connection.exec_driver_sql("PRAGMA integrity_check").scalar()

    assert tables == {
        "provider_system_compatibility_assessment",
        "provider_system_event_outbox",
    }
    prohibited = {
        "password",
        "api_key",
        "oauth_token",
        "prompt",
        "response",
        "raw_payload",
        "path",
        "email",
    }
    assert not prohibited.intersection(set().union(*columns.values()))
    assert integrity == "ok"


def test_non_available_version_cannot_persist_scheme_or_rule(
    tmp_path: Path,
) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)

    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            with pytest.raises(IntegrityError):
                connection.exec_driver_sql(
                    "INSERT INTO provider_system_compatibility_assessment "
                    "(assessment_id, registration_id, provider_key, adapter_id, "
                    "adapter_version, protocol_version, capability_id, "
                    "capability_schema_version, provider_version_value, "
                    "provider_version_state, version_scheme, version_rule_id, "
                    "compatibility_state, reason_code, manifest_schema_version, "
                    "manifest_fingerprint, input_fingerprint, assessed_at, "
                    "correlation_id, is_current, record_version) VALUES "
                    "('assessment-invalid-version-pair', 'registration-001', "
                    "'claude', 'claude-adapter', '1.0.0', '1.0.0', "
                    "'subscription.quota', '1.0', NULL, 'unknown', "
                    "'opaque_exact', 'claude-code-exact-v1', 'unverified', "
                    "'version_evidence_unavailable', '1.0.0', ?, ?, "
                    "'2026-09-22T13:00:00.000000Z', 'correlation-001', 1, 1)",
                    ("e" * 64, "f" * 64),
                )


def _insert_valid_assessment(connection: Connection) -> None:
    connection.exec_driver_sql(
        "INSERT INTO provider_system_compatibility_assessment "
        "(assessment_id, registration_id, provider_key, adapter_id, "
        "adapter_version, protocol_version, capability_id, "
        "capability_schema_version, source_id, provider_version_value, "
        "provider_version_state, version_scheme, version_rule_id, "
        "compatibility_state, reason_code, manifest_schema_version, "
        "manifest_fingerprint, input_fingerprint, assessed_at, valid_until, "
        "correlation_id, is_current, record_version) VALUES "
        "('assessment-valid', 'registration-001', 'claude', "
        "'claude-adapter', '1.0.0', '1.0.0', 'subscription.quota', "
        "'1.0', 'claude.usage.ax-screen-reader.v1', '2.1.278', "
        "'available', 'opaque_exact', 'claude-code-exact-v1', "
        "'compatible', 'exact_evidenced_tuple', '1.0.0', ?, ?, "
        "'2026-09-22T13:00:00.000000Z', "
        "'2026-10-22T13:00:00.000000Z', 'correlation-001', 1, 1)",
        ("a" * 64, "b" * 64),
    )


@pytest.mark.parametrize(
    "mutation",
    (
        "UPDATE provider_system_compatibility_assessment "
        "SET manifest_fingerprint="
        "'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'",
        "UPDATE provider_system_compatibility_assessment "
        "SET input_fingerprint="
        "'gggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggg'",
        "UPDATE provider_system_compatibility_assessment "
        "SET assessed_at='2026-09-22T13:00:00+00:00'",
        "UPDATE provider_system_compatibility_assessment "
        "SET valid_until='2026-09-22T12:59:59.999999Z'",
        "UPDATE provider_system_compatibility_assessment "
        "SET provider_version_state='invalid'",
        "UPDATE provider_system_compatibility_assessment "
        "SET compatibility_state='invalid'",
        "UPDATE provider_system_compatibility_assessment "
        "SET version_scheme='not_a_scheme'",
        "UPDATE provider_system_compatibility_assessment SET provider_version_value=''",
    ),
)
def test_m03_db_008_rejects_noncanonical_compatibility_rows(
    tmp_path: Path, mutation: str
) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)

    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            _insert_valid_assessment(connection)
            connection.commit()
            with pytest.raises(IntegrityError):
                connection.exec_driver_sql(mutation)


def test_m03_db_008_rejects_calendar_invalid_canonical_utc(
    tmp_path: Path,
) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)

    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            _insert_valid_assessment(connection)
            connection.commit()
            connection.exec_driver_sql(
                "UPDATE provider_system_compatibility_assessment "
                "SET assessed_at='2024-02-29T23:59:59.123456Z'"
            )
            connection.commit()
            with pytest.raises(IntegrityError):
                connection.exec_driver_sql(
                    "UPDATE provider_system_compatibility_assessment "
                    "SET assessed_at='2026-02-30T13:00:00.123456Z'"
                )


def _insert_valid_outbox(connection: Connection) -> None:
    connection.exec_driver_sql(
        "INSERT INTO provider_system_event_outbox "
        "(event_id, event_type, assessment_id, registration_id, provider_key, "
        "capability_id, compatibility_state, reason_code, correlation_id, "
        "producer_sequence, occurred_at, recorded_at, delivery_state, "
        "available_at, claimed_at, delivered_at, attempt_count) VALUES "
        "('event-valid', 'provider.compatibility.assessed.v1', "
        "'assessment-valid', 'registration-001', 'claude', "
        "'subscription.quota', 'compatible', 'exact_evidenced_tuple', "
        "'correlation-001', 1, '2026-09-22T13:00:00.000000Z', "
        "'2026-09-22T13:00:00.000000Z', 'pending', "
        "'2026-09-22T13:00:00.000000Z', NULL, NULL, 0)"
    )


@pytest.mark.parametrize(
    "mutation",
    (
        "UPDATE provider_system_event_outbox "
        "SET occurred_at='2026-09-22T13:00:00+00:00'",
        "UPDATE provider_system_event_outbox "
        "SET recorded_at='2026-09-22T12:59:59.999999Z'",
        "UPDATE provider_system_event_outbox "
        "SET available_at='2026-09-22T12:59:59.999999Z'",
        "UPDATE provider_system_event_outbox "
        "SET claimed_at='2026-09-22T13:00:01.000000Z'",
        "UPDATE provider_system_event_outbox "
        "SET delivery_state='claimed', attempt_count=1",
        "UPDATE provider_system_event_outbox "
        "SET delivery_state='claimed', claimed_at='2026-09-22T12:59:59.999999Z', "
        "attempt_count=1",
        "UPDATE provider_system_event_outbox "
        "SET delivery_state='claimed', claimed_at='2026-09-22T13:00:01.000000Z', "
        "attempt_count=0",
        "UPDATE provider_system_event_outbox "
        "SET delivery_state='delivered', "
        "claimed_at='2026-09-22T13:00:02.000000Z', "
        "delivered_at='2026-09-22T13:00:01.000000Z', attempt_count=1",
    ),
)
def test_m03_outbox_rejects_invalid_state_and_timestamp_relationships(
    tmp_path: Path, mutation: str
) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)

    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            _insert_valid_assessment(connection)
            _insert_valid_outbox(connection)
            connection.commit()
            with pytest.raises(IntegrityError):
                connection.exec_driver_sql(mutation)

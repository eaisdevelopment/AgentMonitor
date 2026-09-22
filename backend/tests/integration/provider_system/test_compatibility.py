"""M03 compatibility persistence over the real file-backed SQLite chain."""

from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    InspectSchemaCompatibilityV1,
    application_schema_range,
    migrate_to_head,
)


def test_v1_0300_creates_empty_provider_system_schema(tmp_path: Path) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)

    view = InspectSchemaCompatibilityV1(
        reference, application_schema_range(), "runtime_read_write"
    )
    assert view.state == "compatible"
    assert view.current_revision == "v1_0504"

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

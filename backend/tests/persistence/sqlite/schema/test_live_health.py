"""DB-M4-HEALTH-001..003: actual migrations/startup/WAL and safe schema failures."""

import asyncio
import importlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    application_schema_range,
    migrate_to_head,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.database_v1 import DatabaseHealthRequestV1


def implementation() -> ModuleType:
    return importlib.import_module(
        "agentmonitor.adapters.persistence._shared.sqlite.schema.live_health"
    )


def request() -> DatabaseHealthRequestV1:
    now = datetime.now(UTC)
    return DatabaseHealthRequestV1(
        now, now + timedelta(seconds=2), OpaqueIdV1("db-health")
    )


def migrated(tmp_path: Path) -> DatabaseRefV1:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    return reference


def test_live_wal_real_schema_and_original_integrity_time(tmp_path: Path) -> None:
    health = implementation()
    reference = migrated(tmp_path)
    application_range = application_schema_range()
    reader = health.LiveDatabaseHealthReaderV1(reference, application_range)
    startup, receipt = health.InspectStartupDatabaseHealthV1(
        reference, application_range, "runtime_read_write"
    )
    assert startup.state == "compatible" and receipt is not None
    reader.bind_startup_receipt(receipt)
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as writer:
            writer.exec_driver_sql("PRAGMA user_version=1")
            writer.commit()
            wal = reference._path.with_name(reference._path.name + "-wal")
            assert wal.is_file()
            original_database = reference._path.read_bytes()
            original_wal = wal.read_bytes()
            result = asyncio.run(reader(request()))
            assert result.reachable and result.compatibility_state == "compatible"
            assert result.schema_revision == application_range.migration_target_revision
            assert result.policy_state == "passed"
            assert result.integrity_state == "passed"
            assert result.integrity_checked_at == startup.checked_at
            assert result.checked_at > startup.checked_at
            assert reference._path.read_bytes() == original_database
            assert wal.read_bytes() == original_wal


def test_missing_binding_never_invents_integrity_or_readiness(tmp_path: Path) -> None:
    health = implementation()
    reference = migrated(tmp_path)
    result = asyncio.run(
        health.LiveDatabaseHealthReaderV1(reference, application_schema_range())(
            request()
        )
    )
    assert result.reachable
    assert (
        result.schema_revision == application_schema_range().migration_target_revision
    )
    assert result.compatibility_state is None
    assert (
        result.integrity_state == "not_checked" and result.integrity_checked_at is None
    )


def test_startup_binding_is_one_time_and_file_bound(tmp_path: Path) -> None:
    health = implementation()
    reference = migrated(tmp_path)
    application_range = application_schema_range()
    _, receipt = health.InspectStartupDatabaseHealthV1(
        reference, application_range, "runtime_read_write"
    )
    assert receipt is not None
    reader = health.LiveDatabaseHealthReaderV1(reference, application_range)
    reader.bind_startup_receipt(receipt)
    with pytest.raises(SqlitePolicyError) as caught:
        reader.bind_startup_receipt(receipt)
    assert caught.value.code == "database_startup_receipt_already_bound"
    reference._path.rename(tmp_path / "preserved.db")
    reference._path.touch(mode=0o600)
    result = asyncio.run(reader(request()))
    assert not result.reachable and result.compatibility_state is None
    assert result.integrity_state == "not_checked"
    assert result.reason_codes == ("database_identity_changed",)


@pytest.mark.parametrize("kind", ["missing", "unsafe", "symlink"])
def test_missing_or_unsafe_reference_does_not_create_or_repair(
    tmp_path: Path, kind: str
) -> None:
    health = implementation()
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    if kind == "unsafe":
        reference._path.touch(mode=0o644)
    elif kind == "symlink":
        outside = tmp_path / "outside.db"
        outside.touch(mode=0o600)
        reference._path.symlink_to(outside)
    result = asyncio.run(
        health.LiveDatabaseHealthReaderV1(reference, application_schema_range())(
            request()
        )
    )
    assert not result.reachable
    assert result.reason_codes == (
        ("database_missing",)
        if kind == "missing"
        else ("database_policy_incompatible",)
    )
    assert str(tmp_path) not in repr(result)
    if kind == "missing":
        assert not reference._path.exists()
    elif kind == "unsafe":
        assert reference._path.stat().st_mode & 0o777 == 0o644
    else:
        assert reference._path.is_symlink()


@pytest.mark.parametrize(
    "marker,state",
    [
        ("private-unknown-marker", "unknown_revision"),
        ("v1_0000", "upgrade_required"),
    ],
)
def test_real_marker_failures_are_safe_and_do_not_migrate(
    tmp_path: Path, marker: str, state: str
) -> None:
    health = implementation()
    reference = migrated(tmp_path)
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql(
                "UPDATE alembic_version SET version_num=?", (marker,)
            )
            connection.commit()
        result = asyncio.run(
            health.LiveDatabaseHealthReaderV1(reference, application_schema_range())(
                request()
            )
        )
        assert result.reachable and result.compatibility_state == state
        assert result.schema_revision == (
            None if state == "unknown_revision" else marker
        )
        assert "private-unknown-marker" not in repr(result)


def test_multiple_actual_schema_heads_are_not_reported_as_current(
    tmp_path: Path,
) -> None:
    health = implementation()
    reference = migrated(tmp_path)
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql(
                "INSERT INTO alembic_version(version_num) VALUES ('v1_0000')"
            )
            connection.commit()
        result = asyncio.run(
            health.LiveDatabaseHealthReaderV1(reference, application_schema_range())(
                request()
            )
        )
        assert (
            result.compatibility_state == "multiple_heads"
            and result.schema_revision is None
        )


def test_changed_actual_technical_schema_invalidates_startup_receipt(
    tmp_path: Path,
) -> None:
    health = implementation()
    reference = migrated(tmp_path)
    application_range = application_schema_range()
    _, receipt = health.InspectStartupDatabaseHealthV1(
        reference, application_range, "runtime_read_write"
    )
    reader = health.LiveDatabaseHealthReaderV1(reference, application_range)
    reader.bind_startup_receipt(receipt)
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE unadmitted_technical_object(value TEXT)"
            )
            connection.commit()
        result = asyncio.run(reader(request()))
        assert result.compatibility_state == "migration_failed"
        assert result.integrity_state == "not_checked"
        assert result.reason_codes == ("database_schema_changed",)


@pytest.mark.parametrize(
    "field,value",
    [
        ("reason_codes", ("private_raw_error",)),
        ("compatibility_state", "private_raw_state"),
        ("reachable", 1),
    ],
)
def test_pure_health_value_rejects_unclosed_states(field: str, value: object) -> None:
    """Constructed immutable values only; this policy test performs no I/O."""
    from agentmonitor.contracts.database_v1 import DatabaseHealthV1

    values: dict[str, Any] = {
        "reachable": False,
        "schema_revision": None,
        "compatibility_state": None,
        "integrity_state": "not_checked",
        "integrity_checked_at": None,
        "policy_state": "not_checked",
        "checked_at": datetime(2026, 9, 29, tzinfo=UTC),
        "reason_codes": ("database_health_unverified",),
    }
    values[field] = value
    with pytest.raises((ValueError, TypeError)):
        DatabaseHealthV1(**values)

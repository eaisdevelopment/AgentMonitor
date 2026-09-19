"""DB-FILE-001..009 / FND-DB-003: actual isolated files and connections."""

import importlib
import os
import sys
import traceback
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "backend/src"))
MODULE = "agentmonitor.adapters.persistence._shared.sqlite.core.policy"


def implementation() -> ModuleType:
    assert (
        (ROOT / "backend/src" / Path(*MODULE.split("."))).with_suffix(".py").is_file()
    ), "DB-FILE-007: production file/connection policy is absent"
    return importlib.import_module(MODULE)


def test_every_connection_and_reopen_enforce_exact_policy(tmp_path: Path) -> None:
    policy = implementation()
    ref = policy.DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    expected = {
        "foreign_keys": 1,
        "journal_mode": "wal",
        "synchronous": 2,
        "busy_timeout": 5000,
        "read_uncommitted": 0,
        "wal_autocheckpoint": 1000,
        "trusted_schema": 0,
    }
    for mode in ("migration_initialize", "runtime_read_write", "runtime_read_only"):
        with policy.open_sqlite_database(ref, mode) as handle:
            with handle.connect() as first, handle.connect() as second:
                for connection in (first, second):
                    actual = {
                        name: connection.exec_driver_sql(f"PRAGMA {name}").scalar()
                        for name in expected
                    }
                    assert actual == expected
                assert (
                    first.exec_driver_sql(
                        "SELECT count(*) FROM sqlite_schema WHERE type='table'"
                    ).scalar()
                    == 0
                )
            with handle.connect() as again:
                assert again.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
        with pytest.raises(policy.SqlitePolicyError) as closed:
            with handle.connect():
                pytest.fail("disposed handle reopened")
        assert closed.value.code == "database_handle_closed"
    assert (tmp_path / "agentmonitor.db").is_file()
    if os.name == "posix":
        assert tmp_path.stat().st_mode & 0o777 == 0o700
        assert (tmp_path / "agentmonitor.db").stat().st_mode & 0o777 == 0o600


def test_normal_open_does_not_create_and_initialization_is_exclusive(
    tmp_path: Path,
) -> None:
    policy = implementation()
    path = tmp_path / "agentmonitor.db"
    ref = policy.DatabaseRefV1(path, tmp_path)
    for mode in ("runtime_read_write", "runtime_read_only", "migration_existing"):
        with pytest.raises(policy.SqlitePolicyError) as caught:
            policy.open_sqlite_database(ref, mode)
        assert caught.value.code == "database_missing"
        assert not path.exists()
    with policy.open_sqlite_database(ref, "migration_initialize"):
        pass
    original = path.read_bytes()
    with pytest.raises(policy.SqlitePolicyError) as caught:
        policy.open_sqlite_database(ref, "migration_initialize")
    assert caught.value.code == "database_already_exists"
    assert path.read_bytes() == original


@pytest.mark.parametrize(
    "invalid",
    [
        ":memory:",
        "file:agentmonitor?mode=memory",
        "file:/tmp/agentmonitor.db",
        "relative.db",
        "../agentmonitor.db",
        "bad\x00path",
    ],
)
def test_invalid_references_have_safe_errors(tmp_path: Path, invalid: str) -> None:
    policy = implementation()
    with pytest.raises(policy.SqlitePolicyError) as caught:
        policy.DatabaseRefV1(Path(invalid), tmp_path)
    assert caught.value.code == "database_reference_invalid"
    assert str(tmp_path) not in repr(caught.value)
    assert invalid not in str(caught.value)


def test_unsafe_files_and_roots_are_rejected_without_mutation(tmp_path: Path) -> None:
    policy = implementation()
    root = tmp_path / "approved"
    root.mkdir(mode=0o700)
    outside = tmp_path / "outside.db"
    outside.touch(mode=0o600)
    with pytest.raises(policy.SqlitePolicyError):
        policy.DatabaseRefV1(outside, root)
    path = root / "agentmonitor.db"
    path.symlink_to(outside)
    with pytest.raises(policy.SqlitePolicyError):
        policy.open_sqlite_database(
            policy.DatabaseRefV1(path, root), "runtime_read_only"
        )
    path.unlink()
    path.hardlink_to(outside)
    with pytest.raises(policy.SqlitePolicyError):
        policy.open_sqlite_database(
            policy.DatabaseRefV1(path, root), "runtime_read_only"
        )
    path.unlink()
    path.touch(mode=0o600)
    path.chmod(0o644)
    with pytest.raises(policy.SqlitePolicyError):
        policy.open_sqlite_database(
            policy.DatabaseRefV1(path, root), "runtime_read_only"
        )
    assert path.stat().st_mode & 0o777 == 0o644
    path.chmod(0o600)
    root.chmod(0o770)
    with pytest.raises(policy.SqlitePolicyError):
        policy.open_sqlite_database(
            policy.DatabaseRefV1(path, root), "runtime_read_only"
        )
    root.chmod(0o700)
    assert outside.stat().st_size == 0


def test_sql_errors_are_sanitized_and_resources_close(tmp_path: Path) -> None:
    policy = implementation()
    ref = policy.DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    with policy.open_sqlite_database(ref, "migration_initialize") as handle:
        with pytest.raises(policy.SqlitePolicyError) as caught:
            with handle.connect() as connection:
                connection.exec_driver_sql("SELECT * FROM private_missing_table")
        assert caught.value.code == "persistence_unavailable"
        output = "".join(traceback.format_exception(caught.value))
        assert "private_missing_table" not in str(caught.value)
        assert "OperationalError" not in output
        assert str(tmp_path) not in str(caught.value)
        with handle.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA quick_check").scalar() == "ok"
    assert str(tmp_path) not in repr(ref) + repr(handle)


def test_read_only_handle_refuses_real_metadata_write(tmp_path: Path) -> None:
    policy = implementation()
    ref = policy.DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    with policy.open_sqlite_database(ref, "migration_initialize"):
        pass
    with policy.open_sqlite_database(ref, "runtime_read_only") as handle:
        with pytest.raises(policy.SqlitePolicyError) as caught:
            with handle.connect() as connection:
                connection.exec_driver_sql("PRAGMA user_version=1")
        assert caught.value.code == "persistence_read_only"


def test_checkout_reasserts_policy_and_sidecars_have_owner_permissions(
    tmp_path: Path,
) -> None:
    policy = implementation()
    path = tmp_path / "agentmonitor.db"
    ref = policy.DatabaseRefV1(path, tmp_path)
    with policy.open_sqlite_database(ref, "migration_initialize") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.exec_driver_sql("PRAGMA synchronous=OFF")
            connection.exec_driver_sql("PRAGMA user_version=1")
            connection.commit()
            if os.name == "posix":
                for suffix in ("-wal", "-shm"):
                    sidecar = path.with_name(path.name + suffix)
                    assert sidecar.is_file()
                    assert sidecar.stat().st_mode & 0o777 == 0o600
        with handle.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
            assert connection.exec_driver_sql("PRAGMA synchronous").scalar() == 2


def test_changed_database_identity_refuses_cached_connection(tmp_path: Path) -> None:
    policy = implementation()
    path = tmp_path / "agentmonitor.db"
    ref = policy.DatabaseRefV1(path, tmp_path)
    with policy.open_sqlite_database(ref, "migration_initialize") as handle:
        # Preserve the real opened empty file, then replace its directory entry.
        path.rename(tmp_path / "preserved.db")
        path.touch(mode=0o600)
        with pytest.raises(policy.SqlitePolicyError) as caught:
            with handle.connect():
                pytest.fail("changed database identity accepted")
        assert caught.value.code == "database_identity_changed"
    assert path.stat().st_size == 0


def test_database_ref_rejects_repository_root_even_when_explicit() -> None:
    policy = implementation()
    with pytest.raises(policy.SqlitePolicyError) as caught:
        policy.DatabaseRefV1(ROOT / "agentmonitor.db", ROOT)
    assert caught.value.code == "database_reference_invalid"

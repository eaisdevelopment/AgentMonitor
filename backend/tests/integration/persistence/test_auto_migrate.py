"""M4 offline schema upgrade against real isolated SQLite and OS locks."""

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend/src"))

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (  # noqa: E402
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (  # noqa: E402
    MIGRATIONS_PATH,
    InspectSchemaCompatibilityV1,
    application_schema_range,
    load_migration_catalog,
)
from agentmonitor.composition.iam_operator import (  # noqa: E402
    exclusive_service_quiescence,
)


def _prior_database(root: Path, revision: str = "v1_0603") -> DatabaseRefV1:
    root.chmod(0o700)
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    catalog = load_migration_catalog()
    with open_sqlite_database(reference, "migration_initialize") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            config = Config()
            config.set_main_option("script_location", str(MIGRATIONS_PATH))
            config.attributes.update(
                connection=connection,
                migrations_path=MIGRATIONS_PATH,
                catalog_digest=catalog.digest,
            )
            command.upgrade(config, revision)
            connection.commit()
    return reference


def _run(root: Path, *, expected: str = "v1_0603") -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["AGENTMONITOR_MIGRATE_DATA_ROOT"] = str(root)
    environment["AGENTMONITOR_MIGRATE_EXPECTED_HEAD"] = expected
    return subprocess.run(
        [sys.executable, "tools/automation/run.py", "AUTO-MIGRATE"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def test_auto_migrate_keeps_verified_prior_backup_and_reaches_exact_m4_head(
    tmp_path: Path,
) -> None:
    reference = _prior_database(tmp_path)
    result = _run(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    view = InspectSchemaCompatibilityV1(
        reference, application_schema_range(), "runtime_read_write"
    )
    assert view.state == "compatible"
    assert view.current_revision == "v1_0712"
    backups = list((tmp_path / "backups").glob("migration-preflight-*/manifest.json"))
    assert len(backups) == 1
    manifest = json.loads(backups[0].read_text())
    assert manifest["source_revision"] == "v1_0603"
    assert manifest["target_revision"] == "v1_0712"
    backup_root = backups[0].parent
    assert (
        manifest["database_sha256"]
        == sha256((backup_root / "agentmonitor.db").read_bytes()).hexdigest()
    )
    copy = DatabaseRefV1(backup_root / "agentmonitor.db", backup_root)
    prior_view = InspectSchemaCompatibilityV1(
        copy, application_schema_range(), "runtime_read_write"
    )
    assert prior_view.state == "upgrade_required"
    assert prior_view.current_revision == "v1_0603"
    retry = _run(tmp_path)
    assert retry.returncode == 0, retry.stdout + retry.stderr
    assert "already at v1_0712" in retry.stdout
    assert len(list((tmp_path / "backups").glob("migration-preflight-*"))) == 1


def test_auto_migrate_upgrades_installed_v1_0707_with_verified_backup(
    tmp_path: Path,
) -> None:
    reference = _prior_database(tmp_path, "v1_0707")

    result = _run(tmp_path, expected="v1_0707")

    assert result.returncode == 0, result.stdout + result.stderr
    view = InspectSchemaCompatibilityV1(
        reference, application_schema_range(), "runtime_read_write"
    )
    assert view.state == "compatible"
    assert view.current_revision == "v1_0712"
    manifests = list((tmp_path / "backups").glob("migration-preflight-*/manifest.json"))
    assert len(manifests) == 1
    manifest = json.loads(manifests[0].read_text())
    assert manifest["source_revision"] == "v1_0707"
    assert manifest["target_revision"] == "v1_0712"
    copy = DatabaseRefV1(manifests[0].parent / "agentmonitor.db", manifests[0].parent)
    prior = InspectSchemaCompatibilityV1(
        copy, application_schema_range(), "runtime_read_write"
    )
    assert prior.state == "upgrade_required"
    assert prior.current_revision == "v1_0707"


def test_auto_migrate_refuses_occupied_service_lock_before_backup(
    tmp_path: Path,
) -> None:
    reference = _prior_database(tmp_path)
    with exclusive_service_quiescence(tmp_path, reference):
        result = _run(tmp_path)
    assert result.returncode == 3, result.stdout + result.stderr
    assert not (tmp_path / "backups").exists()
    view = InspectSchemaCompatibilityV1(
        reference, application_schema_range(), "runtime_read_write"
    )
    assert view.current_revision == "v1_0603"


def test_auto_migrate_backs_up_real_private_m06_settings_file(
    tmp_path: Path,
) -> None:
    _prior_database(tmp_path)
    settings = tmp_path / "owner-process-account-associations-v1.json"
    lock = tmp_path / ".owner-process-account-associations-v1.lock"
    # Valid empty owner settings contain no invented process or account record.
    original = b'{"format":"owner-process-account-associations.v1","records":{}}\n'
    settings.write_bytes(original)
    settings.chmod(0o600)
    lock.touch(mode=0o600)
    result = _run(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    manifests = list((tmp_path / "backups").glob("migration-preflight-*/manifest.json"))
    assert len(manifests) == 1
    backup = manifests[0].parent
    assert (backup / settings.name).read_bytes() == original
    assert (backup / lock.name).read_bytes() == b""
    assert settings.read_bytes() == original
    document = json.loads(manifests[0].read_text())
    assert document["settings_sha256"] is not None
    assert document["settings_lock_sha256"] is not None


def test_auto_migrate_refuses_unsafe_settings_link_without_schema_change(
    tmp_path: Path,
) -> None:
    reference = _prior_database(tmp_path)
    target = tmp_path / "ordinary-metadata"
    target.write_bytes(b"private")
    (tmp_path / "owner-process-account-associations-v1.json").symlink_to(target)
    result = _run(tmp_path)
    assert result.returncode != 0
    assert "ordinary-metadata" not in result.stdout + result.stderr
    view = InspectSchemaCompatibilityV1(
        reference, application_schema_range(), "runtime_read_write"
    )
    assert view.current_revision == "v1_0603"


def test_auto_migrate_refuses_invalid_m06_settings_before_ddl(tmp_path: Path) -> None:
    reference = _prior_database(tmp_path)
    settings = tmp_path / "owner-process-account-associations-v1.json"
    settings.write_bytes(b"invalid settings format")
    settings.chmod(0o600)
    (tmp_path / ".owner-process-account-associations-v1.lock").touch(mode=0o600)
    result = _run(tmp_path)
    assert result.returncode != 0
    view = InspectSchemaCompatibilityV1(
        reference, application_schema_range(), "runtime_read_write"
    )
    assert view.current_revision == "v1_0603"


def test_auto_migrate_refuses_m06_settings_lock_contention_before_backup(
    tmp_path: Path,
) -> None:
    reference = _prior_database(tmp_path)
    lock = tmp_path / ".owner-process-account-associations-v1.lock"
    lock.touch(mode=0o600)
    with lock.open("rb") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = _run(tmp_path)
    assert result.returncode == 3, result.stdout + result.stderr
    assert not (tmp_path / "backups").exists()
    view = InspectSchemaCompatibilityV1(
        reference, application_schema_range(), "runtime_read_write"
    )
    assert view.current_revision == "v1_0603"


def test_auto_migrate_refuses_invalid_nested_m06_record_before_ddl(
    tmp_path: Path,
) -> None:
    reference = _prior_database(tmp_path)
    settings = tmp_path / "owner-process-account-associations-v1.json"
    settings.write_text(
        json.dumps(
            {
                "format": "owner-process-account-associations.v1",
                "records": {"bad-key": {"identity": {}}},
            }
        )
    )
    settings.chmod(0o600)
    (tmp_path / ".owner-process-account-associations-v1.lock").touch(mode=0o600)
    result = _run(tmp_path)
    assert result.returncode == 3, result.stdout + result.stderr
    view = InspectSchemaCompatibilityV1(
        reference, application_schema_range(), "runtime_read_write"
    )
    assert view.current_revision == "v1_0603"


def test_auto_migrate_upgrades_v1_0708_to_binding_schema_with_backup(
    tmp_path: Path,
) -> None:
    reference = _prior_database(tmp_path, "v1_0708")
    result = _run(tmp_path, expected="v1_0708")
    assert result.returncode == 0, result.stdout + result.stderr
    view = InspectSchemaCompatibilityV1(
        reference, application_schema_range(), "runtime_read_write"
    )
    assert view.state == "compatible"
    assert view.current_revision == "v1_0712"
    manifests = list((tmp_path / "backups").glob("migration-preflight-*/manifest.json"))
    assert len(manifests) == 1
    manifest = json.loads(manifests[0].read_text())
    assert manifest["source_revision"] == "v1_0708"
    assert manifest["target_revision"] == "v1_0712"
    copy = DatabaseRefV1(manifests[0].parent / "agentmonitor.db", manifests[0].parent)
    prior = InspectSchemaCompatibilityV1(
        copy, application_schema_range(), "runtime_read_write"
    )
    assert prior.state == "upgrade_required" and prior.current_revision == "v1_0708"


def test_auto_migrate_upgrades_v1_0709_to_source_period_with_backup(
    tmp_path: Path,
) -> None:
    reference = _prior_database(tmp_path, "v1_0709")
    result = _run(tmp_path, expected="v1_0709")
    assert result.returncode == 0, result.stdout + result.stderr
    view = InspectSchemaCompatibilityV1(
        reference, application_schema_range(), "runtime_read_write"
    )
    assert view.state == "compatible" and view.current_revision == "v1_0712"
    manifests = list((tmp_path / "backups").glob("migration-preflight-*/manifest.json"))
    assert len(manifests) == 1
    manifest = json.loads(manifests[0].read_text())
    assert manifest["source_revision"] == "v1_0709"
    assert manifest["target_revision"] == "v1_0712"


def test_auto_migrate_upgrades_v1_0710_to_cloud_journal_with_backup(
    tmp_path: Path,
) -> None:
    reference = _prior_database(tmp_path, "v1_0710")
    result = _run(tmp_path, expected="v1_0710")
    assert result.returncode == 0, result.stdout + result.stderr
    view = InspectSchemaCompatibilityV1(
        reference, application_schema_range(), "runtime_read_write"
    )
    assert view.state == "compatible" and view.current_revision == "v1_0712"
    manifests = list((tmp_path / "backups").glob("migration-preflight-*/manifest.json"))
    assert len(manifests) == 1
    manifest = json.loads(manifests[0].read_text())
    assert manifest["source_revision"] == "v1_0710"
    assert manifest["target_revision"] == "v1_0712"


def test_auto_migrate_upgrades_v1_0711_to_cloud_failure_with_backup(
    tmp_path: Path,
) -> None:
    reference = _prior_database(tmp_path, "v1_0711")
    result = _run(tmp_path, expected="v1_0711")
    assert result.returncode == 0, result.stdout + result.stderr
    view = InspectSchemaCompatibilityV1(
        reference, application_schema_range(), "runtime_read_write"
    )
    assert view.state == "compatible" and view.current_revision == "v1_0712"
    manifests = list((tmp_path / "backups").glob("migration-preflight-*/manifest.json"))
    assert len(manifests) == 1
    manifest = json.loads(manifests[0].read_text())
    assert manifest["source_revision"] == "v1_0711"
    assert manifest["target_revision"] == "v1_0712"

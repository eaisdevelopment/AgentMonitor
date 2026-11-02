"""Real disposable service and empty SQLite migration/restore, no seeded data."""

import json
import subprocess
import uuid
from contextlib import ExitStack
from dataclasses import asdict
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    MIGRATIONS_PATH,
    InspectSchemaCompatibilityV1,
    application_schema_range,
    load_migration_catalog,
)
from agentmonitor.composition.iam_operator import exclusive_service_quiescence
from alembic import command
from alembic.config import Config

from tools.automation.implementations.auto_migrate import (
    _digest_file,
    _hold_settings_lock,
    run_upgrade,
)
from tools.automation.implementations.m6_offline_restore import (
    OfflineRestoreError,
    classify_restore_recovery,
    restore_before_candidate_start,
)
from tools.automation.implementations.m6_quiescent_stop import (
    _process_identity,
    _properties,
    stop_quiescent_unit,
)


@pytest.mark.parametrize("case", ["normal", "corrupt", "aba"])
def test_verified_backup_restores_prior_schema_while_service_stopped(
    tmp_path: Path,
    case: str,
) -> None:
    root = tmp_path / "data"
    root.mkdir(mode=0o700)
    ref = DatabaseRefV1(root / "agentmonitor.db", root)
    catalog = load_migration_catalog()
    with (
        open_sqlite_database(ref, "migration_initialize") as handle,
        handle.connect() as connection,
    ):
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        config = Config()
        config.set_main_option("script_location", str(MIGRATIONS_PATH))
        config.attributes.update(
            connection=connection,
            migrations_path=MIGRATIONS_PATH,
            catalog_digest=catalog.digest,
        )
        command.upgrade(config, "v1_0708")
        connection.commit()
    outcome, backup = run_upgrade(
        root, "v1_0708", planned_backup_id="migration-preflight-" + uuid.uuid4().hex
    )
    assert outcome == "upgraded" and backup is not None
    unit = f"agentmonitor-cutover-test-{uuid.uuid4().hex}.service"
    result = subprocess.run(
        [
            "systemd-run",
            "--user",
            "--unit",
            unit,
            "--property=Restart=no",
            "/bin/sleep",
            "60",
        ],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    directory = Path.home() / ".config/systemd/user" / (unit + ".d")
    directory.mkdir(mode=0o700)
    guard = directory / "90-test.conf"
    guard.write_text("[Unit]\nRefuseManualStart=yes\n[Service]\nRestart=no\n")
    guard.chmod(0o600)
    subprocess.run(
        ["systemctl", "--user", "daemon-reload"], check=True, capture_output=True
    )
    journal = root / ".m6-cutover-journal.json"
    journal.write_text(
        json.dumps(
            {
                "format": "m6-cutover.v1",
                "phase": "candidate_start_attempted",
                "backup_id": backup,
            }
        )
    )
    journal.chmod(0o600)
    stack = ExitStack()
    try:
        props = _properties(unit)
        pid = int(props["MainPID"])
        identity = _process_identity(pid, props["ControlGroup"])
        receipt = stop_quiescent_unit(
            unit,
            expected_pid=pid,
            expected_cgroup=props["ControlGroup"],
            expected_start_ticks=identity[0],
            expected_executable_identity=identity[1:],
            expected_invocation_id=props["InvocationID"],
            expected_start_monotonic=props["ExecMainStartTimestampMonotonic"],
        )
        service_lease = stack.enter_context(exclusive_service_quiescence(root, ref))
        settings_lease = stack.enter_context(_hold_settings_lock(root))
        with pytest.raises(OfflineRestoreError, match="restore_journal_invalid"):
            restore_before_candidate_start(
                root,
                backup,
                receipt=receipt,
                journal=journal,
                service_lease=service_lease,
                settings_lease=settings_lease,
            )
        before = InspectSchemaCompatibilityV1(
            ref, application_schema_range(), "runtime_read_write"
        )
        assert before.current_revision == "v1_0709"
        journal.write_text(
            json.dumps(
                {
                    "format": "m6-cutover.v1",
                    "phase": "migrated",
                    "backup_id": backup,
                    "stop_receipt": asdict(receipt),
                }
            )
        )
        if case == "aba":
            guard.unlink()
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["systemctl", "--user", "start", unit], check=True, capture_output=True
            )
            guard.write_text("[Unit]\nRefuseManualStart=yes\n[Service]\nRestart=no\n")
            guard.chmod(0o600)
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                check=True,
                capture_output=True,
            )
            new_props = _properties(unit)
            new_pid = int(new_props["MainPID"])
            new_identity = _process_identity(new_pid, new_props["ControlGroup"])
            stop_quiescent_unit(
                unit,
                expected_pid=new_pid,
                expected_cgroup=new_props["ControlGroup"],
                expected_start_ticks=new_identity[0],
                expected_executable_identity=new_identity[1:],
                expected_invocation_id=new_props["InvocationID"],
                expected_start_monotonic=new_props["ExecMainStartTimestampMonotonic"],
            )
            assert new_props["InvocationID"] != receipt.invocation_id
            with pytest.raises(
                OfflineRestoreError, match="restore_service_not_blocked"
            ):
                restore_before_candidate_start(
                    root,
                    backup,
                    receipt=receipt,
                    journal=journal,
                    service_lease=service_lease,
                    settings_lease=settings_lease,
                )
            view = InspectSchemaCompatibilityV1(
                ref, application_schema_range(), "runtime_read_write"
            )
            assert view.current_revision == "v1_0709" and view.state == "compatible"
            return
        if case == "corrupt":
            active_before = (root / "agentmonitor.db").stat()
            with (root / "backups" / backup / "agentmonitor.db").open("ab") as stream:
                stream.write(b"\0")
            with pytest.raises(OfflineRestoreError, match="restore_backup_invalid"):
                restore_before_candidate_start(
                    root,
                    backup,
                    receipt=receipt,
                    journal=journal,
                    service_lease=service_lease,
                    settings_lease=settings_lease,
                )
            active_after = (root / "agentmonitor.db").stat()
            assert (active_before.st_dev, active_before.st_ino) == (
                active_after.st_dev,
                active_after.st_ino,
            )
            view = InspectSchemaCompatibilityV1(
                ref, application_schema_range(), "runtime_read_write"
            )
            assert view.current_revision == "v1_0709" and view.state == "compatible"
            return
        assert (
            restore_before_candidate_start(
                root,
                backup,
                receipt=receipt,
                journal=journal,
                service_lease=service_lease,
                settings_lease=settings_lease,
            )
            == "restored"
        )
        view = InspectSchemaCompatibilityV1(
            ref, application_schema_range(), "runtime_read_write"
        )
        assert view.state == "upgrade_required" and view.current_revision == "v1_0708"
        generation = next((root / "restore-generations").iterdir())
        preserved = DatabaseRefV1(
            generation / "preserved/agentmonitor.db", generation / "preserved"
        )
        preserved_view = InspectSchemaCompatibilityV1(
            preserved, application_schema_range(), "runtime_read_write"
        )
        assert (
            preserved_view.current_revision == "v1_0709"
            and preserved_view.state == "compatible"
        )
        assert _digest_file(root / "agentmonitor.db") == _digest_file(
            root / "backups" / backup / "agentmonitor.db"
        )
        receipt = json.loads(journal.read_text())
        assert receipt["phase"] == "restore_activated"
        assert classify_restore_recovery(root, journal) == "activated"
        assert receipt["generation"] == generation.name
        active_stat = (root / "agentmonitor.db").stat()
        retained_stat = (generation / "restored/agentmonitor.db").stat()
        assert [active_stat.st_dev, active_stat.st_ino] == receipt["staged_identity"]
        assert [retained_stat.st_dev, retained_stat.st_ino] == receipt[
            "active_identity"
        ]
        preserved_file = generation / "preserved/agentmonitor.db"
        with preserved_file.open("ab") as stream:
            stream.write(b"\0")
        with pytest.raises(
            OfflineRestoreError, match="restore_recovery_generation_changed"
        ):
            classify_restore_recovery(root, journal)
        with pytest.raises(OfflineRestoreError, match="restore_journal_invalid"):
            restore_before_candidate_start(
                root,
                backup,
                receipt=receipt,
                journal=journal,
                service_lease=service_lease,
                settings_lease=settings_lease,
            )
    finally:
        stack.close()
        subprocess.run(
            ["systemctl", "--user", "stop", unit], capture_output=True, check=False
        )
        guard.unlink(missing_ok=True)
        directory.rmdir()
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"], capture_output=True, check=False
        )

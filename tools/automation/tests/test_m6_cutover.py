"""Run cutover against real disposable systemd service and real empty SQLite."""

import ast
import inspect
import json
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from contextlib import closing
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

from tools.automation.implementations.auto_m6_local_activate import build_override
from tools.automation.implementations.auto_migrate import _hold_settings_lock
from tools.automation.implementations.m6_cutover import (
    CutoverError,
    _cutover_engine,
    cutover,
)
from tools.automation.implementations.m6_migration_recovery import (
    _recover_migration_before_start,
)
from tools.automation.implementations.m6_offline_restore import (
    classify_restore_recovery,
    restore_before_candidate_start,
    resume_prepared_restore,
)
from tools.automation.implementations.m6_quiescent_stop import QuiescentStopReceipt
from tools.automation.implementations.m6_transition_lease import _hold_transition_locks


@pytest.mark.parametrize(
    "case",
    [
        "normal",
        "child",
        "writer",
        "restore",
        "crash_pre",
        "crash_post",
        "real_source_restore",
        "migration_crash_backup",
        "migration_crash_committed",
    ],
)
def test_disposable_unit_and_real_backup_migration(
    tmp_path: Path, case: str, request: pytest.FixtureRequest
) -> None:
    root = tmp_path / "data"
    root.mkdir(mode=0o700)
    if case == "real_source_restore":
        request.addfinalizer(lambda: shutil.rmtree(root) if root.exists() else None)
    ref = DatabaseRefV1(root / "agentmonitor.db", root)
    source_revision = "v1_0707" if case == "real_source_restore" else "v1_0708"
    if case == "real_source_restore":
        live_uri = "file:/home/dev/.local/share/agentmonitor/agentmonitor.db?mode=ro"
        with (
            sqlite3.connect(live_uri, uri=True) as live,
            sqlite3.connect(root / "agentmonitor.db") as private,
        ):
            live.backup(private)
        (root / "agentmonitor.db").chmod(0o600)
        view = InspectSchemaCompatibilityV1(
            ref, application_schema_range(), "runtime_read_write"
        )
        assert view.current_revision == source_revision
    else:
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
    baseline = Path("/home/dev/.local/share/agentmonitor/worktrees/m6-integration")
    candidate = Path("/home/dev/.local/share/agentmonitor/worktrees/m6-next")
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=candidate,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    unit = f"agentmonitor-cutover-test-{uuid.uuid4().hex}.service"
    directory = Path.home() / ".config/systemd/user" / (unit + ".d")
    directory.mkdir(mode=0o700)
    override = directory / "90-m6-local.conf"
    override.write_text(build_override(baseline))
    override.chmod(0o600)
    result = subprocess.run(
        [
            "systemd-run",
            "--user",
            "--unit",
            unit,
            f"--property=WorkingDirectory={baseline}",
            "--property=Restart=on-failure",
            *(
                ["/bin/bash", "-c", "sleep 60 & wait"]
                if case == "child"
                else ["/bin/sleep", "60"]
            ),
        ],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    writer = None
    try:
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"], check=True, capture_output=True
        )
        if case in {"migration_crash_backup", "migration_crash_committed"}:
            worker_code = """
import os,sys
from pathlib import Path
from tools.automation.implementations.m6_cutover import _cutover_engine
print(os.getpid(),flush=True)
_cutover_engine(unit=sys.argv[1], data_root=Path(sys.argv[2]), baseline=Path(sys.argv[3]), candidate=Path(sys.argv[4]), override=Path(sys.argv[5]), source=sys.argv[6], expected_revision=sys.argv[7], expected_executable=Path('/bin/sleep'))
"""
            worker_command = [
                sys.executable,
                "-c",
                worker_code,
                unit,
                str(root),
                str(baseline),
                str(candidate),
                str(override),
                source_revision,
                revision,
            ]
            if case == "migration_crash_committed":
                worker_command = [
                    "/usr/bin/strace",
                    "-q",
                    "-o",
                    str(tmp_path / "trace-migration"),
                    "-e",
                    "trace=rename",
                    "-e",
                    "inject=rename:when=3:delay_enter=10s",
                    *worker_command,
                ]
            worker = subprocess.Popen(
                worker_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            try:
                assert worker.stdout is not None
                pid = int(worker.stdout.readline())
                deadline = time.monotonic() + 20
                journal = root / ".m6-cutover-journal.json"
                while time.monotonic() < deadline:
                    if worker.poll() is not None:
                        raise AssertionError(
                            "migration worker exited before interruption"
                        )
                    try:
                        data = json.loads(journal.read_text())
                        backup = root / "backups" / data["backup_id"]
                        if data["phase"] == "stopped" and backup.is_dir():
                            if case == "migration_crash_backup":
                                break
                            with closing(
                                sqlite3.connect(
                                    f"file:{root / 'agentmonitor.db'}?mode=ro", uri=True
                                )
                            ) as db:
                                marker = db.execute(
                                    "SELECT version_num FROM alembic_version"
                                ).fetchone()[0]
                            if marker == load_migration_catalog().head:
                                break
                    except (
                        FileNotFoundError,
                        KeyError,
                        json.JSONDecodeError,
                        sqlite3.OperationalError,
                    ):
                        pass
                    time.sleep(0.001)
                else:
                    raise AssertionError(
                        "migration worker did not reach the requested boundary"
                    )
                os.kill(pid, signal.SIGKILL)
                worker.wait(timeout=20)
            finally:
                if worker.poll() is None:
                    worker.terminate()
                    worker.wait(timeout=20)
            old_backup = data["backup_id"]
            with (
                _hold_transition_locks(root) as transition_lease,
                exclusive_service_quiescence(root, ref) as service_lease,
                _hold_settings_lock(root) as settings_lease,
            ):
                assert (
                    _recover_migration_before_start(
                        root,
                        transition_lease=transition_lease,
                        service_lease=service_lease,
                        settings_lease=settings_lease,
                    )
                    == "migration_recovered"
                )
            recovered = json.loads(journal.read_text())
            assert recovered["phase"] == "migrated"
            if case == "migration_crash_backup":
                assert old_backup in recovered["prior_backup_ids"]
                assert (root / "backups" / old_backup).is_dir()
            else:
                assert recovered["backup_id"] == old_backup
            view = InspectSchemaCompatibilityV1(
                ref, application_schema_range(), "runtime_read_write"
            )
            assert (
                view.current_revision == load_migration_catalog().head
                and view.state == "compatible"
            )
        elif case in {"restore", "crash_pre", "crash_post", "real_source_restore"}:
            pid = int(
                subprocess.run(
                    ["systemctl", "--user", "show", unit, "-p", "MainPID", "--value"],
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout
            )

            def conflict_after_stop():
                deadline = time.monotonic() + 30
                while Path(f"/proc/{pid}").exists() and time.monotonic() < deadline:
                    time.sleep(0.001)
                os.chmod(override, 0o644)

            conflict = threading.Thread(target=conflict_after_stop)
            conflict.start()
            with pytest.raises(CutoverError):
                _cutover_engine(
                    unit=unit,
                    data_root=root,
                    baseline=baseline,
                    candidate=candidate,
                    override=override,
                    source=source_revision,
                    expected_revision=revision,
                    expected_executable=Path("/bin/sleep"),
                )
            conflict.join(timeout=30)
            assert not conflict.is_alive()
            os.chmod(override, 0o600)
            journal = root / ".m6-cutover-journal.json"
            recorded = json.loads(journal.read_text())
            assert recorded["phase"] == "migrated"
            raw_receipt = recorded["stop_receipt"]
            raw_receipt["executable_identity"] = tuple(
                raw_receipt["executable_identity"]
            )
            receipt = QuiescentStopReceipt(**raw_receipt)
            original = (root / "agentmonitor.db").stat()
            if case in {"crash_pre", "crash_post"}:
                worker_code = """
import json, os, sys
from pathlib import Path
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.composition.iam_operator import exclusive_service_quiescence
from tools.automation.implementations.auto_migrate import _hold_settings_lock
from tools.automation.implementations.m6_offline_restore import restore_before_candidate_start
from tools.automation.implementations.m6_quiescent_stop import QuiescentStopReceipt
from tools.automation.implementations.m6_transition_lease import _hold_transition_locks
root = Path(sys.argv[1])
journal = root / '.m6-cutover-journal.json'
data = json.loads(journal.read_text())
raw = data['stop_receipt']
raw['executable_identity'] = tuple(raw['executable_identity'])
receipt = QuiescentStopReceipt(**raw)
print(os.getpid(), flush=True)
with _hold_transition_locks(root) as transition, exclusive_service_quiescence(root, DatabaseRefV1(root / 'agentmonitor.db', root)) as service, _hold_settings_lock(root) as settings:
    restore_before_candidate_start(root, data['backup_id'], receipt=receipt, journal=journal, transition_lease=transition, service_lease=service, settings_lease=settings)
"""
                delay = "delay_enter" if case == "crash_pre" else "delay_exit"
                tracer = subprocess.Popen(
                    [
                        "/usr/bin/strace",
                        "-q",
                        "-o",
                        str(tmp_path / "trace"),
                        "-e",
                        "trace=renameat2",
                        "-e",
                        f"inject=renameat2:{delay}=10s",
                        sys.executable,
                        "-c",
                        worker_code,
                        str(root),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                try:
                    assert tracer.stdout is not None
                    worker_pid = int(tracer.stdout.readline())
                    deadline = time.monotonic() + 20
                    while time.monotonic() < deadline:
                        if tracer.poll() is not None:
                            raise AssertionError(
                                "restore worker exited before boundary"
                            )
                        try:
                            current = json.loads(journal.read_text())
                            active = (root / "agentmonitor.db").stat()
                            if current["phase"] == "restore_prepared" and (
                                case == "crash_pre"
                                or (active.st_dev, active.st_ino)
                                != (original.st_dev, original.st_ino)
                            ):
                                break
                        except (FileNotFoundError, KeyError, json.JSONDecodeError):
                            pass
                        time.sleep(0.005)
                    else:
                        raise AssertionError("restore worker did not reach boundary")
                    os.kill(worker_pid, signal.SIGKILL)
                    tracer.wait(timeout=20)
                finally:
                    if tracer.poll() is None:
                        tracer.terminate()
                        tracer.wait(timeout=20)
                with (
                    _hold_transition_locks(root) as transition_lease,
                    exclusive_service_quiescence(root, ref) as service_lease,
                    _hold_settings_lock(root) as settings_lease,
                ):
                    assert (
                        resume_prepared_restore(
                            root,
                            transition_lease=transition_lease,
                            service_lease=service_lease,
                            settings_lease=settings_lease,
                        )
                        == "activated"
                    )
                    assert classify_restore_recovery(root, journal) == "activated"
            else:
                with (
                    _hold_transition_locks(root) as transition_lease,
                    exclusive_service_quiescence(root, ref) as service_lease,
                    _hold_settings_lock(root) as settings_lease,
                ):
                    assert (
                        restore_before_candidate_start(
                            root,
                            recorded["backup_id"],
                            receipt=receipt,
                            journal=journal,
                            transition_lease=transition_lease,
                            service_lease=service_lease,
                            settings_lease=settings_lease,
                        )
                        == "restored"
                    )
                    assert classify_restore_recovery(root, journal) == "activated"
                    assert (
                        resume_prepared_restore(
                            root,
                            transition_lease=transition_lease,
                            service_lease=service_lease,
                            settings_lease=settings_lease,
                        )
                        == "already_activated"
                    )
            activated = json.loads(journal.read_text())
            retained = (
                root
                / "restore-generations"
                / activated["generation"]
                / "restored"
                / "agentmonitor.db"
            ).stat()
            assert (retained.st_dev, retained.st_ino) == (
                original.st_dev,
                original.st_ino,
            )
            view = InspectSchemaCompatibilityV1(
                ref, application_schema_range(), "runtime_read_write"
            )
            assert view.current_revision == source_revision
        elif case in {"child", "writer"}:
            if case == "writer":
                writer = sqlite3.connect(root / "agentmonitor.db")
                writer.execute("BEGIN IMMEDIATE")
            pid = int(
                subprocess.run(
                    ["systemctl", "--user", "show", unit, "-p", "MainPID", "--value"],
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout
            )
            if case == "child":
                children = Path(f"/proc/{pid}/task/{pid}/children")
                deadline = time.monotonic() + 3
                while not children.read_text().strip() and time.monotonic() < deadline:
                    time.sleep(0.02)
                assert children.read_text().strip()
            with pytest.raises(CutoverError):
                _cutover_engine(
                    unit=unit,
                    data_root=root,
                    baseline=baseline,
                    candidate=candidate,
                    override=override,
                    source=source_revision,
                    expected_revision=revision,
                    expected_executable=Path(
                        "/bin/bash" if case == "child" else "/bin/sleep"
                    ),
                )
            if writer is not None:
                writer.rollback()
                writer.close()
                writer = None
            state = subprocess.run(
                ["systemctl", "--user", "is-active", unit],
                capture_output=True,
                text=True,
                check=True,
            )
            assert state.stdout.strip() == "active"
            view = InspectSchemaCompatibilityV1(
                ref, application_schema_range(), "runtime_read_write"
            )
            assert view.current_revision == source_revision
            assert not (root / "backups").exists()
            assert not (root / ".m6-cutover-journal.json").exists()
        else:
            assert (
                _cutover_engine(
                    unit=unit,
                    data_root=root,
                    baseline=baseline,
                    candidate=candidate,
                    override=override,
                    source=source_revision,
                    expected_revision=revision,
                    expected_executable=Path(
                        "/bin/bash" if case == "child" else "/bin/sleep"
                    ),
                )
                == "candidate_started_product_verification_required"
            )
            view = InspectSchemaCompatibilityV1(
                ref, application_schema_range(), "runtime_read_write"
            )
            assert view.state == "compatible" and view.current_revision == "v1_0709"
            assert (
                len(
                    list((root / "backups").glob("migration-preflight-*/manifest.json"))
                )
                == 1
            )
        if case in {"child", "writer"}:
            assert not (directory / "95-m6-cutover-restart.conf").exists()
        else:
            assert (directory / "95-m6-cutover-restart.conf").is_file()
            assert (
                subprocess.run(
                    ["systemctl", "--user", "show", unit, "-p", "Restart", "--value"],
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout.strip()
                == "no"
            )

    finally:
        if writer is not None:
            writer.rollback()
            writer.close()
        subprocess.run(
            ["systemctl", "--user", "stop", unit], capture_output=True, check=False
        )
        for item in directory.iterdir():
            item.unlink()
        directory.rmdir()
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"], capture_output=True, check=False
        )
        if case == "real_source_restore":
            shutil.rmtree(root)


def test_public_cutover_target_is_not_caller_selectable() -> None:
    assert not inspect.signature(cutover).parameters
    implementation = Path(__file__).resolve().parents[1] / "implementations"
    callers = []
    for path in implementation.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "_cutover_engine"
            ):
                callers.append(path.name)
    assert callers == ["m6_cutover.py"]

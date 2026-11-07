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
from alembic import command
from alembic.config import Config

from tools.automation.implementations.auto_m6_local_activate import build_override
from tools.automation.implementations.auto_m6_local_update import replace_override
from tools.automation.implementations.m6_cutover import (
    CutoverError,
    _cutover_engine,
    _finish_restored_baseline_engine,
    _recover_migration_engine,
    _recover_same_schema_candidate_attempt,
    _restore_interrupted_migration_engine,
    _start_restored_baseline_engine,
    cutover,
    recover_interrupted_migration,
    restore_interrupted_migration,
    start_restored_baseline,
)
from tools.automation.implementations.m6_offline_restore import (
    classify_restore_recovery,
)
from tools.automation.implementations.m6_transition_lease import _hold_transition_locks


@pytest.mark.parametrize(
    "case",
    [
        "normal",
        "candidate_finalize_process_changed",
        "candidate_finalize",
        "candidate_finalize_interrupted",
        "candidate_finalize_no",
        "child",
        "writer",
        "restore",
        "restore_restart",
        "restore_runtime",
        "restore_restart_interrupted",
        "restore_restart_no",
        "restore_restart_retry",
        "restore_ready_retry",
        "crash_pre",
        "crash_post",
        "real_source_restore",
        "migration_crash_backup",
        "migration_crash_committed",
        "candidate_attempt_recovery",
        "override_installed_restore",
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
    source_revision = {"v1_0719": "v1_0718", "v1_0720": "v1_0719"}[
        load_migration_catalog().head
    ]
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
            command.upgrade(config, source_revision)
            connection.commit()
    baseline = Path("/home/dev/.local/share/agentmonitor/worktrees/m6-integration")
    candidate = Path(
        os.environ.get(
            "AGENTMONITOR_TEST_CANDIDATE",
            "/home/dev/.local/share/agentmonitor/worktrees/m6-cloud-final",
        )
    )
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
    test_executable = Path("/bin/sleep")
    runtime_command = ["/bin/sleep", "60"]
    runtime = None
    if case == "restore_runtime":
        from tools.automation.implementations.m6_cutover import _FIXED_VENV

        runtime = tmp_path / "runtime"
        shutil.copytree(_FIXED_VENV, runtime, symlinks=True)
        test_executable = runtime / "bin/python"
        runtime_command = [
            str(test_executable),
            "-c",
            "import fastapi,time; time.sleep(60)",
        ]
    result = subprocess.run(
        [
            "systemd-run",
            "--user",
            "--unit",
            unit,
            f"--property=WorkingDirectory={baseline}",
            "--property=Restart="
            + (
                "no"
                if case in {"restore_restart_no", "candidate_finalize_no"}
                else "on-failure"
            ),
            *(
                ["/bin/bash", "-c", "sleep 60 & wait"]
                if case == "child"
                else runtime_command
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
        if case == "override_installed_restore":
            worker_code = """
import os,sys
from pathlib import Path
from tools.automation.implementations.m6_cutover import _cutover_engine
print(os.getpid(),flush=True)
_cutover_engine(
    unit=sys.argv[1],
    data_root=Path(sys.argv[2]),
    baseline=Path(sys.argv[3]),
    candidate=Path(sys.argv[4]),
    override=Path(sys.argv[5]),
    source=sys.argv[6],
    expected_revision=sys.argv[7],
    expected_executable=Path('/bin/sleep'),
)
"""
            worker = subprocess.Popen(
                [
                    "/usr/bin/strace",
                    "-q",
                    "-o",
                    str(tmp_path / "trace-override-installed"),
                    "-e",
                    "trace=rename",
                    "-e",
                    "inject=rename:delay_exit=100ms",
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
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            journal = root / ".m6-cutover-journal.json"
            before = build_override(baseline).encode()
            after = build_override(candidate).encode()
            try:
                assert worker.stdout is not None
                worker_pid = int(worker.stdout.readline())
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    if worker.poll() is not None:
                        assert worker.stderr is not None
                        raise AssertionError(
                            "override worker exited before interruption: "
                            + worker.stderr.read()
                        )
                    try:
                        data = json.loads(journal.read_text())
                        if (
                            data["phase"] == "migrated"
                            and override.read_bytes() == after
                        ):
                            break
                    except (FileNotFoundError, json.JSONDecodeError):
                        pass
                    time.sleep(0.005)
                else:
                    raise AssertionError("override-installed boundary not reached")
                os.kill(worker_pid, signal.SIGKILL)
                worker.wait(timeout=20)
            finally:
                if worker.poll() is None:
                    worker.terminate()
                    worker.wait(timeout=20)

            def prepare_restore() -> None:
                current = override.read_bytes()
                if current == after:
                    assert replace_override(override, after, before)
                assert override.read_bytes() == before
                subprocess.run(
                    ["systemctl", "--user", "daemon-reload"],
                    check=True,
                    capture_output=True,
                )

            with _hold_transition_locks(root) as transition_lease:
                assert (
                    _restore_interrupted_migration_engine(
                        root,
                        transition_lease,
                        data,
                        data,
                        prepare_restore=prepare_restore,
                    )
                    == "baseline_restored_service_stopped"
                )
            assert override.read_bytes() == before
            view = InspectSchemaCompatibilityV1(
                ref, application_schema_range(), "runtime_read_write"
            )
            assert view.current_revision == source_revision
        elif case == "candidate_attempt_recovery":
            worker_code = """
import os,sys
from pathlib import Path
from tools.automation.implementations.m6_cutover import _cutover_engine
print(os.getpid(),flush=True)
_cutover_engine(
    unit=sys.argv[1],
    data_root=Path(sys.argv[2]),
    baseline=Path(sys.argv[3]),
    candidate=Path(sys.argv[4]),
    override=Path(sys.argv[5]),
    source=sys.argv[6],
    expected_revision=sys.argv[7],
    expected_executable=Path('/bin/sleep'),
)
"""
            worker = subprocess.Popen(
                [
                    "/usr/bin/strace",
                    "-q",
                    "-o",
                    str(tmp_path / "trace-candidate-attempt"),
                    "-e",
                    "trace=rename",
                    "-e",
                    "inject=rename:delay_exit=100ms",
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
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                assert worker.stdout is not None
                worker_pid = int(worker.stdout.readline())
                journal = root / ".m6-cutover-journal.json"
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    if worker.poll() is not None:
                        assert worker.stderr is not None
                        raise AssertionError(
                            "candidate worker exited before interruption: "
                            + worker.stderr.read()
                        )
                    try:
                        if json.loads(journal.read_text())["phase"] == (
                            "candidate_start_attempted"
                        ):
                            break
                    except (FileNotFoundError, json.JSONDecodeError):
                        pass
                    time.sleep(0.005)
                else:
                    raise AssertionError("candidate boundary not reached")
                os.kill(worker_pid, signal.SIGKILL)
                worker.wait(timeout=20)
            finally:
                if worker.poll() is None:
                    worker.terminate()
                    worker.wait(timeout=20)

            def verify_candidate() -> None:
                properties = subprocess.run(
                    [
                        "systemctl",
                        "--user",
                        "show",
                        unit,
                        "-p",
                        "ActiveState",
                        "-p",
                        "WorkingDirectory",
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout
                assert "ActiveState=active" in properties
                assert f"WorkingDirectory={candidate}" in properties

            with _hold_transition_locks(root) as transition_lease:
                assert (
                    _recover_same_schema_candidate_attempt(
                        root,
                        transition_lease,
                        unit=unit,
                        baseline=baseline,
                        candidate=candidate,
                        override=override,
                        guard=directory / "95-m6-cutover-restart.conf",
                        verify_candidate=verify_candidate,
                    )
                    == "candidate_started_product_verification_required"
                )
            recovered = json.loads(journal.read_text())
            assert recovered["phase"] == "candidate_started"
            assert recovered["backup_id"] is not None
            view = InspectSchemaCompatibilityV1(
                ref, application_schema_range(), "runtime_read_write"
            )
            assert (
                view.current_revision == load_migration_catalog().head
                and view.state == "compatible"
            )
        elif case in {"migration_crash_backup", "migration_crash_committed"}:
            worker_code = """
import os,sys
from pathlib import Path
from tools.automation.implementations.m6_cutover import _cutover_engine
print(os.getpid(),flush=True)
_cutover_engine(
    unit=sys.argv[1],
    data_root=Path(sys.argv[2]),
    baseline=Path(sys.argv[3]),
    candidate=Path(sys.argv[4]),
    override=Path(sys.argv[5]),
    source=sys.argv[6],
    expected_revision=sys.argv[7],
    expected_executable=Path('/bin/sleep'),
)
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
                            if (backup / "manifest.json").is_file() and (
                                root / ".m6-cutover-journal.json.next"
                            ).is_file():
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
            interrupted_journal = root / ".m6-cutover-journal.json.next"
            if case == "migration_crash_committed":
                assert interrupted_journal.is_file()
            with _hold_transition_locks(root) as transition_lease:
                assert (
                    _recover_migration_engine(root, transition_lease, data)
                    == "migration_recovered"
                )
            recovered = json.loads(journal.read_text())
            if case == "migration_crash_committed":
                assert not interrupted_journal.exists()
                assert len(list((root / ".m6-journal-orphans").iterdir())) == 1
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
        elif case in {
            "restore",
            "restore_restart",
            "restore_runtime",
            "restore_restart_interrupted",
            "restore_restart_no",
            "restore_restart_retry",
            "restore_ready_retry",
            "crash_pre",
            "crash_post",
            "real_source_restore",
        }:
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
                    expected_executable=test_executable,
                )
            conflict.join(timeout=30)
            assert not conflict.is_alive()
            os.chmod(override, 0o600)
            journal = root / ".m6-cutover-journal.json"
            recorded = json.loads(journal.read_text())
            assert recorded["phase"] == "migrated"
            original = (root / "agentmonitor.db").stat()
            if case in {"crash_pre", "crash_post"}:
                worker_code = """
import json, os, sys
from pathlib import Path
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.composition.iam_operator import exclusive_service_quiescence
from tools.automation.implementations.auto_migrate import _hold_settings_lock
from tools.automation.implementations.m6_offline_restore import (
    restore_before_candidate_start,
)
from tools.automation.implementations.m6_quiescent_stop import QuiescentStopReceipt
from tools.automation.implementations.m6_transition_lease import _hold_transition_locks
root = Path(sys.argv[1])
journal = root / '.m6-cutover-journal.json'
data = json.loads(journal.read_text())
raw = data['stop_receipt']
raw['executable_identity'] = tuple(raw['executable_identity'])
receipt = QuiescentStopReceipt(**raw)
print(os.getpid(), flush=True)
with (
    _hold_transition_locks(root) as transition,
    exclusive_service_quiescence(
        root, DatabaseRefV1(root / 'agentmonitor.db', root)
    ) as service,
    _hold_settings_lock(root) as settings,
):
    restore_before_candidate_start(
        root,
        data['backup_id'],
        receipt=receipt,
        journal=journal,
        transition_lease=transition,
        service_lease=service,
        settings_lease=settings,
    )
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
                with _hold_transition_locks(root) as transition_lease:
                    current_journal = json.loads(journal.read_text())
                    assert (
                        _restore_interrupted_migration_engine(
                            root, transition_lease, current_journal, recorded
                        )
                        == "baseline_restored_service_stopped"
                    )
                    assert classify_restore_recovery(root, journal) == "activated"
            else:
                with _hold_transition_locks(root) as transition_lease:
                    assert (
                        _restore_interrupted_migration_engine(
                            root, transition_lease, recorded, recorded
                        )
                        == "baseline_restored_service_stopped"
                    )
                    assert classify_restore_recovery(root, journal) == "activated"
                    current_journal = json.loads(journal.read_text())
                    assert (
                        _restore_interrupted_migration_engine(
                            root, transition_lease, current_journal, recorded
                        )
                        == "baseline_restored_service_stopped"
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
            if case in {
                "restore_restart",
                "restore_runtime",
                "restore_restart_interrupted",
                "restore_restart_no",
                "restore_restart_retry",
                "restore_ready_retry",
            }:
                before = build_override(baseline).encode()
                restart_override = before
                if case == "restore_runtime":
                    from tools.automation.implementations.m6_cutover import (
                        _FIXED_BASELINE,
                        _candidate_override,
                    )
                    from tools.automation.implementations.m6_runtime_integrity import (
                        _runtime_digest,
                    )

                    assert runtime is not None
                    for cache in runtime.rglob("__pycache__"):
                        shutil.rmtree(cache)
                    before_digest = _runtime_digest(runtime)
                    environment = next(
                        line
                        for line in _candidate_override(_FIXED_BASELINE).splitlines()
                        if line.startswith("Environment=PYTHONDONTWRITEBYTECODE=")
                    )
                    restart_override += (environment + "\n").encode()
                with _hold_transition_locks(root) as transition_lease:
                    assert (
                        _start_restored_baseline_engine(
                            root,
                            transition_lease,
                            recorded,
                            unit=unit,
                            guard=directory / "95-m6-cutover-restart.conf",
                            override=override,
                            expected_override=before,
                            start_override=restart_override,
                            baseline=baseline,
                            executable=test_executable,
                        )
                        == "baseline_started_readiness_unverified"
                    )
                assert (
                    json.loads(journal.read_text())["phase"]
                    == "baseline_start_attempted"
                )
                if case == "restore_runtime":
                    restarted_pid = int(
                        subprocess.check_output(
                            [
                                "systemctl",
                                "--user",
                                "show",
                                unit,
                                "-p",
                                "MainPID",
                                "--value",
                            ],
                            text=True,
                        ).strip()
                    )
                    deadline = time.monotonic() + 5
                    while time.monotonic() < deadline:
                        if (
                            Path("/proc") / str(restarted_pid) / "wchan"
                        ).read_text().strip() == "hrtimer_nanosleep":
                            break
                        time.sleep(0.05)
                    else:
                        raise AssertionError(
                            "restored Python did not complete its import"
                        )
                    assert _runtime_digest(runtime) == before_digest
                if case == "restore_restart_retry":
                    from tools.automation.implementations import m6_cutover

                    subprocess.run(
                        ["systemctl", "--user", "kill", "--signal=SIGKILL", unit],
                        check=True,
                        capture_output=True,
                    )
                    guard = directory / "95-m6-cutover-restart.conf"
                    guard.write_text(
                        "[Unit]\nRefuseManualStart=yes\n[Service]\nRestart=no\n"
                    )
                    guard.chmod(0o600)
                    subprocess.run(
                        ["systemctl", "--user", "daemon-reload"],
                        check=True,
                        capture_output=True,
                    )
                    deadline = time.monotonic() + 5
                    while time.monotonic() < deadline:
                        state = subprocess.run(
                            [
                                "systemctl",
                                "--user",
                                "show",
                                unit,
                                "-p",
                                "MainPID",
                                "--value",
                            ],
                            capture_output=True,
                            text=True,
                            check=True,
                        ).stdout.strip()
                        if state == "0":
                            break
                        time.sleep(0.05)
                    else:
                        raise AssertionError("disposable service did not stop")
                    with _hold_transition_locks(root) as lease:
                        m6_cutover._retry_stopped_baseline_engine(
                            root,
                            lease,
                            unit=unit,
                            guard=guard,
                            override=override,
                            baseline=baseline,
                            executable=Path("/bin/sleep"),
                        )
                if case in {"restore_restart_interrupted", "restore_ready_retry"}:
                    code = """
import os, sys
from pathlib import Path
from tools.automation.implementations.m6_transition_lease import _hold_transition_locks
from tools.automation.implementations.m6_cutover import _finish_restored_baseline_engine
root, guard = Path(sys.argv[1]), Path(sys.argv[3])
print(os.getpid(), flush=True)
with _hold_transition_locks(root) as lease:
    _finish_restored_baseline_engine(
        root,
        lease,
        unit=sys.argv[2],
        guard=guard,
        expected_restart="on-failure",
    )
"""
                    guard = directory / "95-m6-cutover-restart.conf"
                    tracer = subprocess.Popen(
                        [
                            "/usr/bin/strace",
                            "-q",
                            "-o",
                            str(tmp_path / "finish-trace"),
                            "-e",
                            "trace=unlinkat",
                            "-e",
                            "inject=unlinkat:delay_exit=10s",
                            sys.executable,
                            "-c",
                            code,
                            str(root),
                            unit,
                            str(guard),
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
                            if (
                                not guard.exists()
                                and json.loads(journal.read_text())["phase"]
                                == "baseline_http_ready"
                            ):
                                break
                            if tracer.poll() is not None:
                                raise AssertionError(
                                    "finish worker exited before boundary"
                                )
                            time.sleep(0.05)
                        else:
                            raise AssertionError(
                                "finish interruption boundary not reached"
                            )
                        os.kill(worker_pid, signal.SIGKILL)
                    finally:
                        tracer.communicate(timeout=20)
                    if case == "restore_ready_retry":
                        from tools.automation.implementations import m6_cutover

                        subprocess.run(
                            ["systemctl", "--user", "kill", "--signal=SIGKILL", unit],
                            check=True,
                            capture_output=True,
                        )
                        deadline = time.monotonic() + 5
                        while time.monotonic() < deadline:
                            state = subprocess.run(
                                [
                                    "systemctl",
                                    "--user",
                                    "show",
                                    unit,
                                    "-p",
                                    "MainPID",
                                    "--value",
                                ],
                                capture_output=True,
                                text=True,
                                check=True,
                            ).stdout.strip()
                            if state == "0":
                                break
                            time.sleep(0.05)
                        else:
                            raise AssertionError("disposable service did not stop")
                        with _hold_transition_locks(root) as lease:
                            m6_cutover._retry_stopped_baseline_engine(
                                root,
                                lease,
                                unit=unit,
                                guard=guard,
                                override=override,
                                baseline=baseline,
                                executable=Path("/bin/sleep"),
                            )
                with _hold_transition_locks(root) as transition_lease:
                    assert (
                        _finish_restored_baseline_engine(
                            root,
                            transition_lease,
                            unit=unit,
                            guard=directory / "95-m6-cutover-restart.conf",
                            expected_restart=recorded["baseline_restart"],
                        )
                        == "baseline_ready_restart_restored"
                    )
                assert not journal.exists()
                assert len(list((root / ".m6-completed-journals").iterdir())) == 1
                assert (
                    subprocess.run(
                        ["systemctl", "--user", "is-active", unit],
                        capture_output=True,
                        text=True,
                        check=True,
                    ).stdout.strip()
                    == "active"
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
            assert (
                view.state == "compatible"
                and view.current_revision == load_migration_catalog().head
            )
            assert (
                len(
                    list((root / "backups").glob("migration-preflight-*/manifest.json"))
                )
                == 1
            )
            if case == "candidate_finalize_process_changed":
                original_pid = subprocess.check_output(
                    ["systemctl", "--user", "show", unit, "-p", "MainPID", "--value"],
                    text=True,
                ).strip()

                def stop_during_verification() -> None:
                    subprocess.run(
                        ["systemctl", "--user", "kill", "--signal=SIGKILL", unit],
                        check=True,
                        capture_output=True,
                    )
                    deadline = time.monotonic() + 5
                    while time.monotonic() < deadline:
                        current_pid = subprocess.check_output(
                            [
                                "systemctl",
                                "--user",
                                "show",
                                unit,
                                "-p",
                                "MainPID",
                                "--value",
                            ],
                            text=True,
                        ).strip()
                        if current_pid != original_pid:
                            return
                        time.sleep(0.05)
                    raise AssertionError("disposable process did not change")

                with (
                    _hold_transition_locks(root) as lease,
                    pytest.raises(
                        CutoverError, match="baseline_restart_process_changed"
                    ),
                ):
                    _finish_restored_baseline_engine(
                        root,
                        lease,
                        unit=unit,
                        guard=directory / "95-m6-cutover-restart.conf",
                        expected_restart="on-failure",
                        verify_after=stop_during_verification,
                        candidate=True,
                    )
                assert (root / ".m6-cutover-journal.json").exists()
            if case in {
                "candidate_finalize",
                "candidate_finalize_interrupted",
                "candidate_finalize_no",
            }:
                if case == "candidate_finalize_interrupted":
                    code = """
import os, sys
from pathlib import Path
from tools.automation.implementations.m6_transition_lease import _hold_transition_locks
from tools.automation.implementations.m6_cutover import _finish_restored_baseline_engine
root, guard = Path(sys.argv[1]), Path(sys.argv[3])
print(os.getpid(), flush=True)
with _hold_transition_locks(root) as lease:
    _finish_restored_baseline_engine(
        root,
        lease,
        unit=sys.argv[2],
        guard=guard,
        expected_restart="on-failure",
        candidate=True,
    )
"""
                    guard = directory / "95-m6-cutover-restart.conf"
                    journal = root / ".m6-cutover-journal.json"
                    tracer = subprocess.Popen(
                        [
                            "/usr/bin/strace",
                            "-q",
                            "-o",
                            str(tmp_path / "candidate-finish-trace"),
                            "-e",
                            "trace=unlinkat",
                            "-e",
                            "inject=unlinkat:delay_exit=10s",
                            sys.executable,
                            "-c",
                            code,
                            str(root),
                            unit,
                            str(guard),
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
                            if (
                                not guard.exists()
                                and json.loads(journal.read_text())["phase"]
                                == "candidate_http_ready"
                            ):
                                break
                            if tracer.poll() is not None:
                                raise AssertionError(
                                    "candidate finish worker exited before boundary"
                                )
                            time.sleep(0.05)
                        else:
                            raise AssertionError(
                                "candidate finish interruption boundary not reached"
                            )
                        os.kill(worker_pid, signal.SIGKILL)
                    finally:
                        tracer.communicate(timeout=20)
                with _hold_transition_locks(root) as lease:
                    assert (
                        _finish_restored_baseline_engine(
                            root,
                            lease,
                            unit=unit,
                            guard=directory / "95-m6-cutover-restart.conf",
                            expected_restart="no"
                            if case == "candidate_finalize_no"
                            else "on-failure",
                            candidate=True,
                        )
                        == "candidate_ready_restart_restored"
                    )
                assert not (root / ".m6-cutover-journal.json").exists()
        if case in {
            "child",
            "writer",
            "restore_restart",
            "restore_runtime",
            "restore_restart_interrupted",
            "restore_restart_no",
            "restore_restart_retry",
            "restore_ready_retry",
            "candidate_finalize",
            "candidate_finalize_interrupted",
            "candidate_finalize_no",
            "candidate_finalize_process_changed",
        }:
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
    assert not inspect.signature(recover_interrupted_migration).parameters
    assert not inspect.signature(restore_interrupted_migration).parameters
    assert not inspect.signature(start_restored_baseline).parameters
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
    assert callers and set(callers) == {"m6_cutover.py"}


def test_recovery_command_is_cataloged_and_rejects_target_arguments() -> None:
    root = Path(__file__).resolve().parents[3]
    catalog = subprocess.run(
        ["/usr/bin/python3", "tools/automation/run.py", "--list"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "AUTO-M6-CUTOVER\toperational_limited\t" in catalog.stdout
    assert "AUTO-M6-CURRENT-UPDATE\toperational_limited\t" in catalog.stdout
    assert "AUTO-M6-RECOVER-CURRENT-UPDATE\toperational_limited\t" in catalog.stdout
    assert "AUTO-M6-RECOVER-MIGRATION\toperational_limited\t" in catalog.stdout
    assert "AUTO-M6-RESTORE-PRESTART\toperational_limited\t" in catalog.stdout
    assert "AUTO-M6-START-RESTORED\toperational_limited\t" in catalog.stdout
    assert "AUTO-M6-FINALIZE-CANDIDATE\toperational_limited\t" in catalog.stdout
    for script in ("auto_m6_current_update.py", "auto_m6_recover_current_update.py"):
        rejected_update = subprocess.run(
            [
                "/usr/bin/python3",
                "tools/automation/implementations/" + script,
                "--target",
                "example",
            ],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        assert (
            rejected_update.returncode == 3
            and "no target arguments are accepted" in rejected_update.stdout
        )
    rejected = subprocess.run(
        [
            "/usr/bin/python3",
            "tools/automation/implementations/auto_m6_cutover.py",
            "--target",
            "example",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert (
        rejected.returncode == 3
        and "no target arguments are accepted" in rejected.stdout
    )
    denied = subprocess.run(
        [
            "/usr/bin/python3",
            "tools/automation/implementations/auto_m6_finalize_candidate.py",
            "--target",
            "example",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert (
        denied.returncode == 3 and "no target arguments are accepted" in denied.stdout
    )
    result = subprocess.run(
        [
            "/usr/bin/python3",
            "tools/automation/implementations/auto_m6_recover_migration.py",
            "--target",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 3
    assert "no target arguments are accepted" in result.stdout


def test_candidate_override_selects_existing_credential_file() -> None:
    from pathlib import Path

    from tools.automation.implementations.m6_cutover import (
        _FIXED_BASELINE,
        _candidate_override,
    )

    candidate = _candidate_override(
        Path("/home/dev/.local/share/agentmonitor/releases/example")
    )
    assert (
        "--credential-env-file /home/dev/Nextcloud/Code/AI/AgentMonitor/.env"
        in candidate
    )
    assert "--credential-env-file" not in _candidate_override(_FIXED_BASELINE)
    assert "Environment=PYTHONDONTWRITEBYTECODE=1" in candidate
    assert "Environment=PYTHONDONTWRITEBYTECODE=1" in _candidate_override(
        _FIXED_BASELINE
    )

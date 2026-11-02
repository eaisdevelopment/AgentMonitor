"""Real isolated dashboard cutover and candidate finalization, without keys."""

import json
import os
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    MIGRATIONS_PATH,
    load_migration_catalog,
)
from alembic import command
from alembic.config import Config

from tools.automation.implementations.auto_m6_local_activate import build_override
from tools.automation.implementations.m6_cutover import (
    _cutover_engine,
    _finish_restored_baseline_engine,
    _recover_same_schema_candidate_attempt,
    _recover_same_schema_update_engine,
    _verify_candidate_runtime,
)
from tools.automation.implementations.m6_transition_lease import _hold_transition_locks


@pytest.mark.parametrize(
    "interrupted",
    [
        False,
        True,
        "frozen",
        "killed",
        "candidate",
        "preparing",
        "guard_relaxed",
        "readiness_failure",
        "guard_removed",
    ],
)
def test_real_same_schema_dashboard_update_and_finalization(
    tmp_path: Path, interrupted: bool | str
) -> None:
    root = tmp_path / "data"
    root.mkdir(mode=0o700)
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    catalog = load_migration_catalog()
    with (
        open_sqlite_database(reference, "migration_initialize") as handle,
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
        command.upgrade(config, "v1_0717")
        connection.commit()
    config_path = root / "config.toml"
    config_path.write_text("")
    config_path.chmod(0o600)
    repo = Path(__file__).resolve().parents[3]
    baseline = tmp_path / "baseline"
    subprocess.run(
        ["git", "clone", "--quiet", "--shared", str(repo), str(baseline)], check=True
    )
    shutil.copytree(repo / "frontend/dist", baseline / "frontend/dist")
    candidate = tmp_path / "candidate"
    subprocess.run(
        ["git", "clone", "--quiet", "--shared", str(repo), str(candidate)], check=True
    )
    shutil.copytree(repo / "frontend/dist", candidate / "frontend/dist")
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=candidate, text=True
    ).strip()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    argv = [
        sys.executable,
        "-m",
        "agentmonitor.composition.bootstrap",
        "--config",
        str(config_path),
        "--data-root",
        str(root),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--authenticated-dashboard",
    ]
    unit = f"agentmonitor-update-test-{uuid.uuid4().hex}.service"
    directory = Path.home() / ".config/systemd/user" / (unit + ".d")
    directory.mkdir(mode=0o700)
    override = directory / "90-m6-local.conf"
    override.write_text(build_override(baseline))
    override.chmod(0o600)
    started = subprocess.run(
        [
            "systemd-run",
            "--user",
            "--unit",
            unit,
            f"--property=WorkingDirectory={baseline}",
            "--property=Restart=on-failure",
            "--setenv=PYTHONDONTWRITEBYTECODE=1",
            *argv,
        ],
        capture_output=True,
        check=False,
    )
    assert started.returncode == 0
    try:
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"], check=True, capture_output=True
        )
        deadline = time.monotonic() + 30
        while True:
            try:
                with urllib.request.urlopen(origin + "/login", timeout=1) as response:
                    assert response.status == 200
                break
            except (OSError, urllib.error.URLError):
                if time.monotonic() >= deadline:
                    raise AssertionError("baseline readiness unavailable") from None
                time.sleep(0.1)
        if interrupted:
            code = """
import os,sys
from pathlib import Path
from tools.automation.implementations.m6_cutover import _cutover_engine
print(os.getpid(), flush=True)
_cutover_engine(unit=sys.argv[1],data_root=Path(sys.argv[2]),baseline=Path(sys.argv[3]),candidate=Path(sys.argv[4]),override=Path(sys.argv[5]),source="v1_0717",same_schema_update=True,expected_revision=sys.argv[6],expected_executable=Path(sys.executable))
"""
            worker = subprocess.Popen(
                [
                    "/usr/bin/strace",
                    "-q",
                    "-o",
                    str(tmp_path / "trace"),
                    "-e",
                    "trace=pidfd_send_signal"
                    if interrupted in {"frozen", "killed"}
                    else "trace=fsync"
                    if interrupted == "preparing"
                    else "trace=rename",
                    "-e",
                    (
                        "inject=pidfd_send_signal:when=1:delay_exit=10s"
                        if interrupted == "frozen"
                        else "inject=pidfd_send_signal:when=2:delay_exit=10s"
                    )
                    if interrupted in {"frozen", "killed"}
                    else "inject=fsync:delay_exit=100ms"
                    if interrupted == "preparing"
                    else (
                        "inject=rename:when=7:delay_enter=10s"
                        if interrupted == "candidate"
                        else "inject=rename:when=3:delay_enter=10s"
                    ),
                    sys.executable,
                    "-c",
                    code,
                    unit,
                    str(root),
                    str(baseline),
                    str(candidate),
                    str(override),
                    revision,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                assert worker.stdout is not None
                worker_pid = int(worker.stdout.readline())
                deadline = time.monotonic() + 20
                journal = root / ".m6-cutover-journal.json"
                while time.monotonic() < deadline:
                    if worker.poll() is not None:
                        assert worker.stderr is not None
                        raise AssertionError(
                            "update worker exited before interruption: "
                            + worker.stderr.read()
                        )
                    try:
                        data = json.loads(journal.read_text())
                        if interrupted == "preparing" and data["phase"] == "preparing":
                            break
                        if (
                            interrupted == "frozen"
                            and data["phase"] == "stop_attempted"
                        ):
                            status = (
                                Path("/proc") / str(data["pid"]) / "status"
                            ).read_text()
                            if any(
                                line.startswith("State:")
                                and line.split()[1] in {"T", "t"}
                                for line in status.splitlines()
                            ):
                                break
                        if (
                            interrupted == "killed"
                            and data["phase"] == "stop_attempted"
                        ):
                            value = subprocess.check_output(
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
                            if value == "0":
                                break
                        if (
                            interrupted == "guard_relaxed"
                            and data["phase"] == "candidate_start_attempted"
                        ):
                            guard = directory / "95-m6-cutover-restart.conf"
                            if guard.read_bytes() == b"[Service]\nRestart=no\n":
                                break
                        if (
                            interrupted == "candidate"
                            and data["phase"] == "candidate_start_attempted"
                            and (root / ".m6-cutover-journal.json.next").is_file()
                        ):
                            break
                        if (
                            (
                                interrupted is True
                                or interrupted in {"readiness_failure", "guard_removed"}
                            )
                            and data["phase"] == "stopped"
                            and (root / ".m6-cutover-journal.json.next").is_file()
                        ):
                            break
                    except (FileNotFoundError, json.JSONDecodeError):
                        pass
                    time.sleep(0.01)
                else:
                    raise AssertionError("stopped update boundary not reached")
                os.kill(worker_pid, signal.SIGKILL)
                worker.wait(timeout=20)
            finally:
                if worker.poll() is None:
                    worker.terminate()
                    worker.wait(timeout=20)

            if interrupted in {"candidate", "guard_relaxed"}:

                def verify_candidate() -> None:
                    _verify_candidate_runtime(
                        root=root,
                        unit=unit,
                        checkout=candidate,
                        origin=origin,
                        executable=Path(sys.executable),
                        expected_command=argv,
                    )

                with _hold_transition_locks(root) as lease:
                    assert (
                        _recover_same_schema_candidate_attempt(
                            root,
                            lease,
                            unit=unit,
                            baseline=baseline,
                            candidate=candidate,
                            override=override,
                            guard=directory / "95-m6-cutover-restart.conf",
                            verify_candidate=verify_candidate,
                        )
                        == "candidate_started_product_verification_required"
                    )
                    assert (
                        _finish_restored_baseline_engine(
                            root,
                            lease,
                            unit=unit,
                            guard=directory / "95-m6-cutover-restart.conf",
                            expected_restart="on-failure",
                            verify_ready=verify_candidate,
                            verify_after=verify_candidate,
                            candidate=True,
                        )
                        == "candidate_ready_restart_restored"
                    )
                assert not journal.exists()
                return

            def verify_baseline() -> None:
                if interrupted == "readiness_failure":
                    subprocess.run(
                        ["systemctl", "--user", "stop", unit],
                        capture_output=True,
                        check=False,
                        timeout=10,
                    )
                _verify_candidate_runtime(
                    root=root,
                    unit=unit,
                    checkout=baseline,
                    origin=origin,
                    executable=Path(sys.executable),
                    expected_command=argv,
                )

            if interrupted == "guard_removed":
                recovery_code = """
import os,sys
from pathlib import Path
from tools.automation.implementations.m6_transition_lease import _hold_transition_locks
from tools.automation.implementations.m6_cutover import _recover_same_schema_update_engine,_verify_candidate_runtime
root,unit,baseline,candidate,override,guard,origin=Path(sys.argv[1]),sys.argv[2],Path(sys.argv[3]),Path(sys.argv[4]),Path(sys.argv[5]),Path(sys.argv[6]),sys.argv[7]
argv=[sys.executable,"-m","agentmonitor.composition.bootstrap","--config",str(root/"config.toml"),"--data-root",str(root),"--host","127.0.0.1","--port",origin.rsplit(":",1)[1],"--authenticated-dashboard"]
def verify(): _verify_candidate_runtime(root=root,unit=unit,checkout=baseline,origin=origin,executable=Path(sys.executable),expected_command=argv)
print(os.getpid(),flush=True)
with _hold_transition_locks(root) as lease: _recover_same_schema_update_engine(root,lease,unit=unit,baseline=baseline,candidate=candidate,override=override,guard=guard,verify_baseline=verify,expected_executable=Path(sys.executable))
"""
                guard = directory / "95-m6-cutover-restart.conf"
                tracer = subprocess.Popen(
                    [
                        "/usr/bin/strace",
                        "-q",
                        "-o",
                        str(tmp_path / "recovery-trace"),
                        "-e",
                        "trace=unlinkat",
                        "-e",
                        "inject=unlinkat:when=1:delay_exit=10s",
                        sys.executable,
                        "-c",
                        recovery_code,
                        str(root),
                        unit,
                        str(baseline),
                        str(candidate),
                        str(override),
                        str(guard),
                        origin,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                try:
                    assert tracer.stdout is not None
                    recovery_pid = int(tracer.stdout.readline())
                    deadline = time.monotonic() + 25
                    while time.monotonic() < deadline:
                        if (
                            not guard.exists()
                            and json.loads(journal.read_text())["phase"]
                            == "baseline_http_ready"
                        ):
                            break
                        if tracer.poll() is not None:
                            assert tracer.stderr is not None
                            raise AssertionError(
                                "recovery exited before guard boundary: "
                                + tracer.stderr.read()
                            )
                        time.sleep(0.02)
                    else:
                        raise AssertionError("guard unlink boundary not reached")
                    os.kill(recovery_pid, signal.SIGKILL)
                    tracer.wait(timeout=20)
                finally:
                    if tracer.poll() is None:
                        tracer.terminate()
                        tracer.wait(timeout=20)
            if interrupted == "readiness_failure":
                from tools.automation.implementations.m6_cutover import CutoverError

                with (
                    _hold_transition_locks(root) as lease,
                    pytest.raises(
                        CutoverError, match="update_recovery_readiness_unavailable"
                    ),
                ):
                    _recover_same_schema_update_engine(
                        root,
                        lease,
                        unit=unit,
                        baseline=baseline,
                        candidate=candidate,
                        override=override,
                        guard=directory / "95-m6-cutover-restart.conf",
                        verify_baseline=verify_baseline,
                        expected_executable=Path(sys.executable),
                    )
                assert (
                    (directory / "95-m6-cutover-restart.conf").read_bytes()
                    == b"[Unit]\nRefuseManualStart=yes\n[Service]\nRestart=no\n"
                )
                assert journal.exists()
                return
            with _hold_transition_locks(root) as lease:
                assert (
                    _recover_same_schema_update_engine(
                        root,
                        lease,
                        unit=unit,
                        baseline=baseline,
                        candidate=candidate,
                        override=override,
                        guard=directory / "95-m6-cutover-restart.conf",
                        verify_baseline=verify_baseline,
                        expected_executable=Path(sys.executable),
                    )
                    == "baseline_ready_restart_restored"
                )
            assert not journal.exists()
            return
        assert (
            _cutover_engine(
                unit=unit,
                data_root=root,
                baseline=baseline,
                candidate=candidate,
                override=override,
                source="v1_0717",
                same_schema_update=True,
                expected_revision=revision,
                expected_executable=Path(sys.executable),
            )
            == "candidate_started_product_verification_required"
        )
        deadline = time.monotonic() + 30
        while True:
            try:
                with urllib.request.urlopen(origin + "/login", timeout=1) as response:
                    assert response.status == 200
                break
            except (OSError, urllib.error.URLError):
                if time.monotonic() >= deadline:
                    raise AssertionError("candidate readiness unavailable") from None
                time.sleep(0.1)
        with sqlite3.connect(root / "agentmonitor.db") as reader:
            reader.execute("BEGIN")
            reader.execute("SELECT count(*) FROM sqlite_schema").fetchone()
            assert (root / "agentmonitor.db-wal").exists()

            from tools.automation.implementations import m6_cutover

            pid = int(
                subprocess.check_output(
                    ["systemctl", "--user", "show", unit, "-p", "MainPID", "--value"],
                    text=True,
                ).strip()
            )
            m6_cutover._verify_loopback_listener(pid, origin)
            with pytest.raises(
                m6_cutover.CutoverError, match="candidate_listener_unverified"
            ):
                m6_cutover._verify_loopback_listener(os.getpid(), origin)

            def verify() -> None:
                _verify_candidate_runtime(
                    root=root,
                    unit=unit,
                    checkout=candidate,
                    origin=origin,
                    executable=Path(sys.executable),
                    expected_command=argv,
                )

            with _hold_transition_locks(root) as lease:
                assert (
                    _finish_restored_baseline_engine(
                        root,
                        lease,
                        unit=unit,
                        guard=directory / "95-m6-cutover-restart.conf",
                        expected_restart="on-failure",
                        verify_ready=verify,
                        verify_after=verify,
                        candidate=True,
                    )
                    == "candidate_ready_restart_restored"
                )
        assert not (root / ".m6-cutover-journal.json").exists()
        props = subprocess.check_output(
            ["systemctl", "--user", "show", unit, "-p", "ActiveState", "-p", "Restart"],
            text=True,
        )
        assert "ActiveState=active" in props and "Restart=on-failure" in props
    finally:
        subprocess.run(
            ["systemctl", "--user", "stop", unit],
            capture_output=True,
            check=False,
            timeout=10,
        )
        shutil.rmtree(directory)
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            capture_output=True,
            check=False,
            timeout=10,
        )

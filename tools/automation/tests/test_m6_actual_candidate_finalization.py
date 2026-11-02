"""Real isolated dashboard cutover and candidate finalization, without keys."""

import os
import shutil
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
    _verify_candidate_runtime,
)
from tools.automation.implementations.m6_transition_lease import _hold_transition_locks


def test_real_dashboard_cutover_and_finalization(tmp_path: Path) -> None:
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
        command.upgrade(config, "v1_0707")
        connection.commit()
    config_path = root / "config.toml"
    config_path.write_text("")
    config_path.chmod(0o600)
    repo = Path(__file__).resolve().parents[3]
    baseline = Path("/home/dev/.local/share/agentmonitor/worktrees/m6-integration")
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
    unit = f"agentmonitor-finalize-test-{uuid.uuid4().hex}.service"
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
        assert (
            _cutover_engine(
                unit=unit,
                data_root=root,
                baseline=baseline,
                candidate=candidate,
                override=override,
                source="v1_0707",
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

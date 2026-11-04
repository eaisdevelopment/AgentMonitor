"""Exercise the real unadmitted local worker without a provider request."""

import asyncio
import fcntl
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.composition.ollama_cloud_worker import OllamaCloudWorkerSupervisorV1


def _test_runtime_environment() -> dict[str, str]:
    runtime_dir = f"/run/user/{os.getuid()}"
    return {
        "PATH": "/usr/bin:/bin",
        "PYTHONPATH": str(Path(__file__).resolve().parents[4] / "src"),
        "XDG_RUNTIME_DIR": runtime_dir,
        "DBUS_SESSION_BUS_ADDRESS": f"unix:path={runtime_dir}/bus",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def test_real_unadmitted_worker_does_not_create_database(tmp_path: Path) -> None:
    worker = OllamaCloudWorkerSupervisorV1(tmp_path)
    assert asyncio.run(worker.run_once()) == "not_admitted"
    assert not (tmp_path / "agentmonitor.db").exists()


def test_real_lock_contention_is_busy_and_recovers_without_restart(
    tmp_path: Path,
) -> None:
    worker = OllamaCloudWorkerSupervisorV1(tmp_path)
    lock = tmp_path / ".ollama-cloud-worker.lock"
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert not worker.is_available()
        assert asyncio.run(worker.run_once()) == "worker_busy"
        assert asyncio.run(worker.run_once()) == "worker_busy"
        assert worker.last_unit == ""
        assert worker._lock_fd is None and worker._root_fd is None
        assert not worker._running
    finally:
        os.close(descriptor)

    assert worker.is_available()
    assert lock.stat().st_size == 0
    assert not (tmp_path / "agentmonitor.db").exists()


def test_real_unsafe_contended_lock_still_quarantines(tmp_path: Path) -> None:
    worker = OllamaCloudWorkerSupervisorV1(tmp_path)
    lock = tmp_path / ".ollama-cloud-worker.lock"
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
    try:
        os.fchmod(descriptor, 0o644)
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert asyncio.run(worker.run_once()) == "quarantined"
        assert worker.last_unit == ""
        assert worker._lock_fd is None and worker._root_fd is None
        os.fchmod(descriptor, 0o600)
    finally:
        os.close(descriptor)

    assert not worker.is_available()
    assert asyncio.run(worker.run_once()) == "quarantined"
    assert not (tmp_path / "agentmonitor.db").exists()


def test_cancelled_real_worker_start_is_recovered_before_reuse(tmp_path: Path) -> None:
    async def exercise() -> None:
        worker = OllamaCloudWorkerSupervisorV1(tmp_path)
        task = asyncio.create_task(worker.run_once())
        while not worker.last_unit and not task.done():
            await asyncio.sleep(0.001)
        assert worker.last_unit
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert await worker.run_once() == "recovered"
        assert await worker.run_once() == "not_admitted"

    asyncio.run(exercise())
    assert not (tmp_path / "agentmonitor.db").exists()


def test_worker_requires_parent_start_authority_before_database_access(
    tmp_path: Path,
) -> None:
    """A late worker gets EOF, not permission to inspect SQLite or credentials."""
    token = uuid.uuid4().hex
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "agentmonitor.composition.ollama_cloud_worker",
            "--data-root",
            str(tmp_path),
            "--start-authority",
            token,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        env=_test_runtime_environment(),
    )
    assert process.stdin is not None
    process.stdin.close()
    assert process.wait(timeout=5) == 5
    assert not (tmp_path / "agentmonitor.db").exists()


def test_cancelled_start_replayed_late_is_revoked_before_worker_io(
    tmp_path: Path,
) -> None:
    async def interrupt() -> str:
        worker = OllamaCloudWorkerSupervisorV1(tmp_path)
        task = asyncio.create_task(worker.run_once())
        while not worker.last_unit and not task.done():
            await asyncio.sleep(0.001)
        assert worker.last_unit
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return worker.last_unit

    unit = asyncio.run(interrupt())
    token = unit.removesuffix(".service").rsplit("-", 1)[1]
    database_path = tmp_path / "agentmonitor.db"
    reference = DatabaseRefV1(database_path, tmp_path)
    migrate_to_head(reference)
    assert os.geteuid() != 0
    database_path.chmod(0)
    environment = _test_runtime_environment()
    command = [
        "/usr/bin/systemd-run",
        "--user",
        "--quiet",
        "--pipe",
        "--unit=" + unit,
        "--description=AgentMonitor cloud worker " + token,
        "--property=KillMode=control-group",
        "--property=RuntimeMaxSec=30s",
        "--property=LimitCORE=0",
        "--property=TimeoutStopSec=3s",
        "--property=RemainAfterExit=yes",
    ]
    command += ["--setenv=" + key + "=" + value for key, value in environment.items()]
    command += [
        sys.executable,
        "-m",
        "agentmonitor.composition.ollama_cloud_worker",
        "--data-root",
        str(tmp_path),
        "--start-authority",
        token,
    ]
    try:
        replay = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=_test_runtime_environment(),
            check=False,
            timeout=8,
        )
        assert replay.returncode == 5
        status = subprocess.run(
            [
                "/usr/bin/systemctl",
                "--user",
                "show",
                unit,
                "--property=ExecMainStatus",
                "--value",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert status.stdout.strip() == "5"
        assert not Path(str(database_path) + "-wal").exists()
        assert not Path(str(database_path) + "-shm").exists()
        assert not any(tmp_path.glob(".ollama-env*"))
    finally:
        database_path.chmod(0o600)
        subprocess.run(
            ["/usr/bin/systemctl", "--user", "stop", unit],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=8,
        )
        subprocess.run(
            ["/usr/bin/systemctl", "--user", "reset-failed", unit],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=8,
        )

    restarted = OllamaCloudWorkerSupervisorV1(tmp_path)
    assert asyncio.run(restarted.run_once()) == "recovered"


def test_real_worker_uses_private_transient_unit_and_cleans_it(tmp_path: Path) -> None:
    worker = OllamaCloudWorkerSupervisorV1(tmp_path)
    assert asyncio.run(worker.run_once()) == "not_admitted"
    unit = worker.last_unit
    assert unit.startswith("agentmonitor-cloud-worker-") and unit.endswith(".service")
    result = subprocess.run(
        ["systemctl", "--user", "show", unit, "--property=LoadState", "--value"],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.stdout.strip() == "not-found"
    assert not (tmp_path / "agentmonitor.db").exists()


def test_real_transient_start_interruption_leaves_no_owned_unit(tmp_path: Path) -> None:
    async def exercise() -> str:
        worker = OllamaCloudWorkerSupervisorV1(tmp_path)
        task = asyncio.create_task(worker.run_once())
        while not worker.last_unit and not task.done():
            await asyncio.sleep(0.001)
        unit = worker.last_unit
        assert unit
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert await worker.run_once() == "recovered"
        return unit

    unit = asyncio.run(exercise())
    result = subprocess.run(
        ["systemctl", "--user", "show", unit, "--property=LoadState", "--value"],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.stdout.strip() == "not-found"


def test_real_supervisor_death_recovers_recorded_unit(tmp_path: Path) -> None:
    program = (
        "import asyncio,sys; "
        "from pathlib import Path; "
        "from agentmonitor.composition.ollama_cloud_worker import "
        "OllamaCloudWorkerSupervisorV1; "
        "asyncio.run(OllamaCloudWorkerSupervisorV1(Path(sys.argv[1])).run_once())"
    )
    process = subprocess.Popen(
        [sys.executable, "-B", "-c", program, str(tmp_path)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        env=_test_runtime_environment(),
    )
    marker = tmp_path / ".ollama-cloud-worker.lock"
    unit = ""
    try:
        for _ in range(5000):
            try:
                unit = marker.read_text(encoding="ascii").strip()
            except FileNotFoundError:
                pass
            if unit or process.poll() is not None:
                break
            # This observes a real fsynced marker; it does not delay production I/O.
            time.sleep(0.0005)
        assert unit
        assert process.poll() is None
        process.kill()
        assert process.wait(timeout=5) < 0

        restarted = OllamaCloudWorkerSupervisorV1(tmp_path)
        assert asyncio.run(restarted.run_once()) == "recovered"
        assert asyncio.run(restarted.run_once()) == "not_admitted"
        result = subprocess.run(
            [
                "/usr/bin/systemctl",
                "--user",
                "show",
                unit,
                "--property=LoadState",
                "--value",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.stdout.strip() == "not-found"
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        if unit:
            subprocess.run(
                ["/usr/bin/systemctl", "--user", "stop", unit],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=8,
            )
            subprocess.run(
                ["/usr/bin/systemctl", "--user", "reset-failed", unit],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=8,
            )


def test_real_supervisors_serialize_unit_startup(tmp_path: Path) -> None:
    async def exercise() -> None:
        first = OllamaCloudWorkerSupervisorV1(tmp_path)
        second = OllamaCloudWorkerSupervisorV1(tmp_path)
        results = await asyncio.gather(first.run_once(), second.run_once())
        assert sorted(results) == ["not_admitted", "worker_busy"]
        assert bool(first.last_unit) != bool(second.last_unit)

    asyncio.run(exercise())


def test_real_supervisors_in_different_roots_do_not_quarantine_each_other(
    tmp_path: Path,
) -> None:
    """A second private installation may start while the first real unit exists."""
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir(mode=0o700)
    second_root.mkdir(mode=0o700)

    async def exercise() -> None:
        first = OllamaCloudWorkerSupervisorV1(first_root)
        second = OllamaCloudWorkerSupervisorV1(second_root)
        first_task = asyncio.create_task(first.run_once())
        try:
            deadline = asyncio.get_running_loop().time() + 8
            observed = False
            while (
                asyncio.get_running_loop().time() < deadline and not first_task.done()
            ):
                if first.last_unit:
                    properties = await first._show(first.last_unit)
                    if properties.get("LoadState") == "loaded":
                        observed = True
                        break
                await asyncio.sleep(0.001)
            assert observed, "first actual private worker was not observed"
            assert not first_task.done()
            second_status = await second.run_once()
            first_status = await first_task
            assert first_status == "not_admitted"
            assert second_status == "not_admitted"
            assert first.is_available() and second.is_available()
        finally:
            if not first_task.done():
                first_task.cancel()
                try:
                    await first_task
                except asyncio.CancelledError:
                    pass

    asyncio.run(exercise())
    assert not (first_root / "agentmonitor.db").exists()
    assert not (second_root / "agentmonitor.db").exists()


def test_exact_legacy_marker_recovers_only_its_own_real_unit(tmp_path: Path) -> None:
    first_root = tmp_path / "legacy"
    second_root = tmp_path / "other"
    first_root.mkdir(mode=0o700)
    second_root.mkdir(mode=0o700)
    worker = OllamaCloudWorkerSupervisorV1(first_root)
    token = uuid.uuid4().hex
    unit = "agentmonitor-cloud-worker-" + token + ".service"
    descriptor = worker._acquire_lock()
    try:
        worker._mark_start(unit)
    finally:
        os.close(descriptor)
        worker._lock_fd = None
        assert worker._root_fd is not None
        os.close(worker._root_fd)
        worker._root_fd = None
    command = [
        "/usr/bin/systemd-run",
        "--user",
        "--quiet",
        "--pipe",
        "--unit=" + unit,
        "--description=AgentMonitor cloud worker " + token,
        "--property=KillMode=control-group",
        "--property=RuntimeMaxSec=30s",
        "--property=LimitCORE=0",
        "--property=TimeoutStopSec=3s",
        "--property=RemainAfterExit=yes",
    ]
    command += [
        "--setenv=" + key + "=" + value
        for key, value in _test_runtime_environment().items()
    ]
    command += [
        sys.executable,
        "-m",
        "agentmonitor.composition.ollama_cloud_worker",
        "--data-root",
        str(first_root),
        "--start-authority",
        token,
    ]
    try:
        actual = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=12,
        )
        assert actual.returncode == 5
        other = OllamaCloudWorkerSupervisorV1(second_root)
        assert asyncio.run(other.run_once()) == "not_admitted"
        # The other root neither quarantines nor stops this real legacy unit.
        properties = asyncio.run(worker._show(unit))
        assert properties["LoadState"] == "loaded"
        assert properties["ExecMainStatus"] == "5"
        assert asyncio.run(worker.run_once()) == "recovered"
        assert asyncio.run(worker.run_once()) == "not_admitted"
        assert asyncio.run(worker._show(unit))["LoadState"] == "not-found"
    finally:
        # Exact owned identity is checked before cleanup; never stop a global match.
        asyncio.run(worker._recover_recorded_start(unit, allow_legacy=True))
    assert not (first_root / "agentmonitor.db").exists()
    assert not (second_root / "agentmonitor.db").exists()


def test_oversized_or_foreign_root_marker_is_rejected(tmp_path: Path) -> None:
    own = tmp_path / "own"
    other = tmp_path / "other"
    own.mkdir(mode=0o700)
    other.mkdir(mode=0o700)
    worker = OllamaCloudWorkerSupervisorV1(own)
    foreign = OllamaCloudWorkerSupervisorV1(other)
    marker = own / ".ollama-cloud-worker.lock"
    unit = worker._unit_prefix + uuid.uuid4().hex + ".service\n"
    marker.write_text(unit + "\n", encoding="ascii")
    marker.chmod(0o600)
    assert asyncio.run(worker.run_once()) == "quarantined"
    assert worker.last_unit == ""
    marker.write_text(
        foreign._unit_prefix + uuid.uuid4().hex + ".service\n", encoding="ascii"
    )
    restarted = OllamaCloudWorkerSupervisorV1(own)
    assert asyncio.run(restarted.run_once()) == "quarantined"
    assert restarted.last_unit == ""


def test_data_root_namespace_rejects_noncanonical_alias(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir(mode=0o700)
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(ValueError, match="ollama_cloud_data_root_invalid"):
        OllamaCloudWorkerSupervisorV1(alias)


def test_independent_real_processes_serialize_unit_startup(tmp_path: Path) -> None:
    async def exercise() -> None:
        program = (
            "import asyncio,sys; "
            "from pathlib import Path; "
            "from agentmonitor.composition.ollama_cloud_worker import "
            "OllamaCloudWorkerSupervisorV1; "
            "print('ready',flush=True); sys.stdin.buffer.read(1); "
            "print(asyncio.run(OllamaCloudWorkerSupervisorV1(Path(sys.argv[1])).run_once()),flush=True)"
        )
        processes = [
            await asyncio.create_subprocess_exec(
                sys.executable,
                "-c",
                program,
                str(tmp_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=_test_runtime_environment(),
            )
            for _ in range(2)
        ]
        try:
            for process in processes:
                assert process.stdout is not None
                assert (
                    await asyncio.wait_for(process.stdout.readline(), 5) == b"ready\n"
                )
            for process in processes:
                assert process.stdin is not None
                process.stdin.write(b"x")
                await process.stdin.drain()
            results = []
            for process in processes:
                assert process.stdout is not None
                results.append(
                    (await asyncio.wait_for(process.stdout.readline(), 15))
                    .decode()
                    .strip()
                )
                assert await asyncio.wait_for(process.wait(), 5) == 0
            assert sorted(results) == ["not_admitted", "worker_busy"]
        finally:
            for process in processes:
                if process.returncode is None:
                    process.kill()
                    await process.wait()

    asyncio.run(exercise())


def test_real_anonymous_provider_helper_is_contained_by_transient_unit() -> None:
    """Interrupt the real fixed anonymous source, with no account or secret."""
    unit = "agentmonitor-cloud-helper-proof-" + uuid.uuid4().hex + ".service"
    source = str(Path(__file__).resolve().parents[4] / "src")
    script = (
        "from agentmonitor.adapters.providers.ollama.cloud_balance.source "
        "import probe_cloud_balance_endpoint_v1; probe_cloud_balance_endpoint_v1()"
    )
    command = [
        "/usr/bin/systemd-run",
        "--user",
        "--quiet",
        "--unit=" + unit,
        "--property=KillMode=control-group",
        "--property=RuntimeMaxSec=5s",
        "--property=StandardOutput=null",
        "--property=StandardError=null",
        "--setenv=PYTHONPATH=" + source,
        sys.executable,
        "-c",
        script,
    ]
    started = subprocess.run(command, capture_output=True, timeout=5, check=False)
    assert started.returncode == 0
    child_seen = False
    cgroup = ""
    try:
        for _ in range(100):
            result = subprocess.run(
                [
                    "/usr/bin/systemctl",
                    "--user",
                    "show",
                    unit,
                    "--property=MainPID,ControlGroup",
                    "--no-pager",
                ],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            properties = dict(
                line.split("=", 1) for line in result.stdout.splitlines() if "=" in line
            )
            pid = int(properties.get("MainPID", "0"))
            cgroup = properties.get("ControlGroup", "")
            if pid > 0 and cgroup:
                children = Path(f"/proc/{pid}/task/{pid}/children")
                try:
                    child_seen = bool(children.read_text().strip())
                except FileNotFoundError:
                    pass
                if child_seen:
                    break
            time.sleep(0.01)
        assert child_seen, "real provider helper did not remain observable"
        stopped = subprocess.run(
            ["/usr/bin/systemctl", "--user", "stop", unit],
            capture_output=True,
            timeout=8,
            check=False,
        )
        assert stopped.returncode == 0
        group = Path("/sys/fs/cgroup") / cgroup.lstrip("/")
        assert (
            not group.exists() or "populated 0" in (group / "cgroup.events").read_text()
        )
    finally:
        subprocess.run(
            ["/usr/bin/systemctl", "--user", "stop", unit],
            capture_output=True,
            timeout=8,
            check=False,
        )
        subprocess.run(
            ["/usr/bin/systemctl", "--user", "reset-failed", unit],
            capture_output=True,
            timeout=8,
            check=False,
        )


def test_ambiguous_systemd_arguments_quarantine_space_path(tmp_path: Path) -> None:
    data_root = tmp_path / "data directory"
    data_root.mkdir(mode=0o700)
    worker = OllamaCloudWorkerSupervisorV1(data_root)
    assert asyncio.run(worker.run_once()) == "quarantined"
    assert worker.last_unit == ""
    assert not (data_root / "agentmonitor.db").exists()


def test_real_lookalike_unit_is_never_stopped(tmp_path: Path) -> None:
    worker = OllamaCloudWorkerSupervisorV1(tmp_path)
    unit = worker._unit_prefix + uuid.uuid4().hex + ".service"
    started = subprocess.run(
        [
            "/usr/bin/systemd-run",
            "--user",
            "--quiet",
            "--unit=" + unit,
            "/usr/bin/sleep",
            "30",
        ],
        check=False,
        capture_output=True,
        timeout=8,
    )
    assert started.returncode == 0
    try:
        assert asyncio.run(worker.run_once()) == "quarantined"
        state = subprocess.run(
            [
                "/usr/bin/systemctl",
                "--user",
                "show",
                unit,
                "--property=ActiveState",
                "--value",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert state.stdout.strip() == "active"
    finally:
        subprocess.run(
            ["/usr/bin/systemctl", "--user", "stop", unit],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=8,
        )
        subprocess.run(
            ["/usr/bin/systemctl", "--user", "reset-failed", unit],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=8,
        )


def test_real_replaced_lock_inode_is_rejected(tmp_path: Path) -> None:
    worker = OllamaCloudWorkerSupervisorV1(tmp_path)
    descriptor = worker._acquire_lock()
    worker._lock_fd = descriptor
    try:
        original = tmp_path / ".ollama-cloud-worker.lock"
        original.rename(tmp_path / "displaced-lock")
        replacement = os.open(original, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        os.close(replacement)
        try:
            worker._verify_lock()
        except ValueError:
            pass
        else:
            raise AssertionError("replaced lock was accepted")
    finally:
        os.close(descriptor)
        worker._lock_fd = None
        if worker._root_fd is not None:
            os.close(worker._root_fd)
            worker._root_fd = None

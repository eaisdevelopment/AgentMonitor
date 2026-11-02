"""Exercise the real unadmitted local worker without a provider request."""

import asyncio
from pathlib import Path

from agentmonitor.composition.ollama_cloud_worker import OllamaCloudWorkerSupervisorV1


def test_real_unadmitted_worker_does_not_create_database(tmp_path: Path) -> None:
    worker = OllamaCloudWorkerSupervisorV1(tmp_path)
    assert asyncio.run(worker.run_once()) == "not_admitted"
    assert not (tmp_path / "agentmonitor.db").exists()


def test_cancelled_real_worker_is_quarantined(tmp_path: Path) -> None:
    async def exercise() -> None:
        worker = OllamaCloudWorkerSupervisorV1(tmp_path)
        task = asyncio.create_task(worker.run_once())
        await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert await worker.run_once() == "quarantined"

    asyncio.run(exercise())
    assert not (tmp_path / "agentmonitor.db").exists()


def test_real_worker_uses_private_transient_unit_and_cleans_it(tmp_path: Path) -> None:
    import subprocess

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
    import subprocess

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
        assert await worker.run_once() == "quarantined"
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


def test_real_supervisors_serialize_unit_startup(tmp_path: Path) -> None:
    async def exercise() -> None:
        first = OllamaCloudWorkerSupervisorV1(tmp_path)
        second = OllamaCloudWorkerSupervisorV1(tmp_path)
        results = await asyncio.gather(first.run_once(), second.run_once())
        assert sorted(results) == ["not_admitted", "quarantined"]
        assert bool(first.last_unit) != bool(second.last_unit)

    asyncio.run(exercise())


def test_independent_real_processes_serialize_unit_startup(tmp_path: Path) -> None:
    import sys

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
            assert sorted(results) == ["not_admitted", "quarantined"]
        finally:
            for process in processes:
                if process.returncode is None:
                    process.kill()
                    await process.wait()

    asyncio.run(exercise())


def test_real_anonymous_provider_helper_is_contained_by_transient_unit() -> None:
    """Interrupt the real fixed anonymous source, with no account or secret."""
    import subprocess
    import sys
    import time
    import uuid

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

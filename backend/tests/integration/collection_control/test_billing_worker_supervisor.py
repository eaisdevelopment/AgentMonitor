"""Real isolated worker locks and units; no credentials or provider traffic."""

import asyncio
import os
import sys
import uuid
from pathlib import Path

import pytest
from agentmonitor.composition.billing_worker_supervisor import BillingWorkerSupervisorV1
from agentmonitor.composition.ollama_cloud_worker import OllamaCloudWorkerSupervisorV1


def test_billing_lock_does_not_claim_ollama_worker(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    billing = BillingWorkerSupervisorV1(tmp_path)
    billing_contender = BillingWorkerSupervisorV1(tmp_path)
    ollama = OllamaCloudWorkerSupervisorV1(tmp_path)
    descriptor = billing._acquire_lock()
    try:
        assert (tmp_path / ".billing-worker.lock").stat().st_size == 0
        assert not (tmp_path / ".ollama-cloud-worker.lock").exists()
        assert not billing_contender.is_available()
        assert asyncio.run(billing_contender.run_once()) == "worker_busy"
        assert billing_contender.last_unit == ""
        assert ollama.is_available()
    finally:
        os.close(descriptor)
        assert billing._root_fd is not None
        os.close(billing._root_fd)
        billing._lock_fd = billing._root_fd = None
    assert billing_contender.is_available()
    assert not (tmp_path / "agentmonitor.db").exists()


def test_ollama_lock_does_not_claim_billing_worker(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    ollama = OllamaCloudWorkerSupervisorV1(tmp_path)
    billing = BillingWorkerSupervisorV1(tmp_path)
    descriptor = ollama._acquire_lock()
    try:
        assert (tmp_path / ".ollama-cloud-worker.lock").stat().st_size == 0
        assert not (tmp_path / ".billing-worker.lock").exists()
        assert billing.is_available()
    finally:
        os.close(descriptor)
        assert ollama._root_fd is not None
        os.close(ollama._root_fd)
        ollama._lock_fd = ollama._root_fd = None
    assert not (tmp_path / "agentmonitor.db").exists()


def test_actual_billing_entrypoint_refuses_missing_database(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    worker = BillingWorkerSupervisorV1(tmp_path)
    assert asyncio.run(worker.run_once()) == "not_admitted"
    assert worker.last_unit.startswith("agentmonitor-billing-worker-")
    assert (tmp_path / ".billing-worker.lock").stat().st_size == 0
    assert not (tmp_path / ".ollama-cloud-worker.lock").exists()
    assert not (tmp_path / "agentmonitor.db").exists()
    properties = asyncio.run(worker._show(worker.last_unit))
    assert properties["LoadState"] == "not-found"


def test_real_billing_unit_identity_and_revoked_start(tmp_path: Path) -> None:
    """Inspect an actual fixed-module unit before granting any worker I/O."""
    tmp_path.chmod(0o700)

    async def exercise() -> None:
        worker = BillingWorkerSupervisorV1(tmp_path)
        token = uuid.uuid4().hex
        unit = worker._unit_prefix + token + ".service"
        description = "AgentMonitor billing worker " + token
        reader, writer = os.pipe2(os.O_CLOEXEC)
        source = Path(__file__).resolve().parents[3] / "src"
        command = [
            "/usr/bin/systemd-run",
            "--user",
            "--quiet",
            "--pipe",
            "--unit=" + unit,
            "--description=" + description,
            "--property=KillMode=control-group",
            "--property=RuntimeMaxSec=120s",
            "--property=LimitCORE=0",
            "--property=TimeoutStopSec=3s",
            "--property=RemainAfterExit=yes",
            "--setenv=PYTHONPATH=" + str(source),
            "--setenv=PYTHONDONTWRITEBYTECODE=1",
            sys.executable,
            "-m",
            "agentmonitor.composition.billing_worker",
            "--data-root",
            str(tmp_path),
            "--start-authority",
            token,
        ]
        launcher = asyncio.create_task(worker._start_command(reader, *command))
        invocation = ""
        try:
            deadline = asyncio.get_running_loop().time() + 5
            while asyncio.get_running_loop().time() < deadline:
                properties = await worker._show(unit)
                if properties["LoadState"] != "not-found":
                    invocation = worker._identity(unit, description, token, properties)
                    break
                await asyncio.sleep(0.02)
            assert invocation, "billing_unit_not_observed"
            assert properties["RuntimeMaxUSec"] == "2min"
            assert properties["ActiveState"] == "active"
            assert worker._unit_token(unit) == token
            other = OllamaCloudWorkerSupervisorV1(tmp_path)
            with pytest.raises(ValueError, match="unit_identity_invalid"):
                other._identity(unit, description, token, properties)
            with pytest.raises(ValueError, match="unit_identity_invalid"):
                other._unit_token(unit, allow_legacy=True)
            os.close(writer)
            writer = -1
            assert await asyncio.wait_for(launcher, timeout=5) == 5
            assert not (tmp_path / "agentmonitor.db").exists()
            assert not (tmp_path / ".billing-worker.lock").exists()
            assert await worker._stop_owned(unit, description, token, invocation)
            invocation = ""
        finally:
            if writer >= 0:
                os.close(writer)
            os.close(reader)
            if invocation:
                await worker._stop_owned(unit, description, token, invocation)
            if not launcher.done():
                launcher.cancel()
                try:
                    await launcher
                except asyncio.CancelledError:
                    pass
            # This exact random unit was created by this test, even if an
            # assertion about the production identity checker failed.
            await worker._command("/usr/bin/systemctl", "--user", "stop", unit)
            await worker._command("/usr/bin/systemctl", "--user", "reset-failed", unit)

    asyncio.run(exercise())


def test_billing_wake_runs_again_without_waiting_for_periodic_tick(
    tmp_path: Path,
) -> None:
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
    )
    from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
        migrate_to_head,
    )

    migrate_to_head(DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path))
    worker = BillingWorkerSupervisorV1(tmp_path)

    async def exercise() -> None:
        task = asyncio.create_task(worker.run())
        try:
            async with asyncio.timeout(10):
                while not worker.last_unit or worker._running:
                    await asyncio.sleep(0.02)
            previous = worker.last_unit
            worker.wake()
            async with asyncio.timeout(10):
                while worker.last_unit == previous:
                    await asyncio.sleep(0.02)
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        assert not worker._lifecycle_running
        assert not worker._running

    asyncio.run(exercise())

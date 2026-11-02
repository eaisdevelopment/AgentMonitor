"""Bounded, owned process supervisor for optional Ollama cloud work."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.providers.ollama.cloud_balance.keyring_command import (
    secret_tool_environment,
)
from agentmonitor.composition.ollama_cloud_collection import (
    OllamaCloudCollectionV1,
    require_cloud_manifest,
    require_source_admitted,
)

# Leaves time for bounded termination inside the dashboard's 45-second drain.
_WORKER_TIMEOUT_SECONDS = 30
_TERMINATION_TIMEOUT_SECONDS = 2


class OllamaCloudWorkerSupervisorV1:
    """Supervise only the explicitly spawned AgentMonitor process, never agents."""

    def __init__(self, data_root: Path) -> None:
        if not data_root.is_absolute() or data_root in {Path("/"), Path.home()}:
            raise ValueError("ollama_cloud_data_root_invalid")
        self._data_root = data_root
        self._quarantined = False
        self._running = False

    async def run_once(self) -> str:
        if self._quarantined:
            return "quarantined"
        if self._running:
            return "worker_busy"
        self._running = True
        try:
            return await self._run_owned_process()
        finally:
            self._running = False

    async def _run_owned_process(self) -> str:
        environment = secret_tool_environment(os.environ)
        environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
        spawn = asyncio.create_task(
            asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "agentmonitor.composition.ollama_cloud_worker",
                "--data-root",
                str(self._data_root),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                env=environment,
            )
        )
        try:
            process = await asyncio.shield(spawn)
        except asyncio.CancelledError:
            self._quarantined = True
            try:
                process = await spawn
                await self._stop(process)
            except (OSError, RuntimeError):
                pass
            raise
        try:
            try:
                code = await asyncio.wait_for(process.wait(), _WORKER_TIMEOUT_SECONDS)
            except TimeoutError:
                self._quarantined = True
                await self._stop(process)
                return "worker_timeout"
            return (
                "not_admitted"
                if code == 3
                else "completed"
                if code == 0
                else "unavailable"
            )
        except asyncio.CancelledError:
            self._quarantined = True
            await self._stop(process)
            raise

    @staticmethod
    async def _stop(process: asyncio.subprocess.Process) -> None:
        if process.returncode is not None:
            return
        try:
            process.terminate()
        except ProcessLookupError:
            pass
        try:
            await asyncio.wait_for(process.wait(), _TERMINATION_TIMEOUT_SECONDS)
        except TimeoutError:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(process.wait(), _TERMINATION_TIMEOUT_SECONDS)
            except TimeoutError:
                # SIGKILL remains pending; the durable gate stays unresolved.
                pass

    async def run(self) -> None:
        while True:
            try:
                await self.run_once()
            except Exception:  # noqa: BLE001 - optional lane, no provider details.
                pass
            await asyncio.sleep(60)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True, type=Path)
    args = parser.parse_args()
    if not args.data_root.is_absolute() or args.data_root in {Path("/"), Path.home()}:
        return 2
    try:
        require_source_admitted()
        require_cloud_manifest()
    except ValueError:
        return 3
    try:
        collector = OllamaCloudCollectionV1(
            DatabaseRefV1(args.data_root / "agentmonitor.db", args.data_root)
        )
        now = datetime.now(UTC)
        rate, _, _ = collector.recover_journals(
            as_of=now,
            owner_stale_before=now - timedelta(minutes=2),
            recovery_lease_expires_at=now + timedelta(seconds=45),
        )
        if rate not in {
            "outcome_unknown",
            "legacy_unresolved",
            "owner_active_or_unverified",
        }:
            collector.tick()
        return 0
    except Exception:  # noqa: BLE001 - the process returns only a closed status.
        return 1


if __name__ == "__main__":
    sys.exit(main())

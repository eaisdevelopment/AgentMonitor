"""Fixed billing worker identity over the existing supervised-unit lifecycle."""

import asyncio
from pathlib import Path
from typing import final

from agentmonitor.composition.ollama_cloud_worker import OllamaCloudWorkerSupervisorV1


@final
class BillingWorkerSupervisorV1(OllamaCloudWorkerSupervisorV1):
    """Run only the billing entrypoint; never accept a caller-selected command."""

    _name_prefix = "agentmonitor-billing-worker-"
    _lock_name = ".billing-worker.lock"
    _worker_module = "agentmonitor.composition.billing_worker"
    _description_prefix = "AgentMonitor billing worker "
    _runtime_seconds = 120
    _runtime_identity = "2min"
    _allow_legacy_marker = False

    def __init__(
        self, data_root: Path, *, credential_env_file: Path | None = None
    ) -> None:
        super().__init__(data_root, credential_env_file=credential_env_file)
        self._wake = asyncio.Event()
        self._loop: asyncio.AbstractEventLoop | None = None

    def wake(self) -> None:
        """Hint after durable admission; the database remains the work authority."""
        loop = self._loop
        if loop is None:
            self._wake.set()
        elif not loop.is_closed():
            loop.call_soon_threadsafe(self._wake.set)

    async def run(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._lifecycle_running = True
        try:
            while True:
                self._wake.clear()
                try:
                    await self.run_once(recovery_only=self._credential_env_file is None)
                except Exception:  # noqa: BLE001 - optional lane; no raw source error.
                    self._quarantined = True
                try:
                    await asyncio.wait_for(self._wake.wait(), timeout=60)
                except TimeoutError:
                    pass
        finally:
            self._loop = None
            self._lifecycle_running = False

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

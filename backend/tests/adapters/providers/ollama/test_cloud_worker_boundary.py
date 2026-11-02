"""Exercise the real unadmitted local worker without a provider request."""

import asyncio
from pathlib import Path

from agentmonitor.composition.ollama_cloud_worker import OllamaCloudWorkerSupervisorV1


def test_real_unadmitted_worker_does_not_create_database(tmp_path: Path) -> None:
    worker = OllamaCloudWorkerSupervisorV1(tmp_path)
    assert asyncio.run(worker.run_once()) == "not_admitted"
    assert not (tmp_path / "agentmonitor.db").exists()

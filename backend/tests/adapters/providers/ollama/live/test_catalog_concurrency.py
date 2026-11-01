"""Concurrent real-source catalog reads do not queue or overlap."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from agentmonitor.adapters.providers.ollama.local_catalog.source import (
    read_local_catalog,
)


def test_real_concurrent_reads_return_busy_without_waiting_for_collection():
    gate = Barrier(12)

    def read_once():
        gate.wait(timeout=5)
        return read_local_catalog()

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = tuple(pool.map(lambda _: read_once(), range(12)))
    assert any(result.outcome == "success" for result in results)
    busy = [r for r in results if r.installed_reason == "collection_in_progress"]
    assert busy, "concurrent_real_read_not_observed"
    assert all(
        r.outcome == "provider_unavailable"
        and r.installed is None
        and r.loaded is None
        and r.loaded_reason == "collection_in_progress"
        for r in busy
    )

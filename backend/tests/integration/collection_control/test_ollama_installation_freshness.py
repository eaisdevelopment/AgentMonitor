"""Real installed Ollama observations stay current on due collection ticks."""

from datetime import UTC, datetime
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.composition.ollama_installation_reconciliation import (
    reconcile_ollama_installation_v1,
)
from agentmonitor.composition.ollama_runtime_collection import OllamaRuntimeCollectorV1


def test_due_collection_refreshes_real_existing_installation_once(
    tmp_path: Path,
) -> None:
    """M6-A02/A06/A09: current process collection includes fresh CLI discovery."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    reconcile_ollama_installation_v1(reference)
    registry = SqliteRegistryRepositoryV1(reference)
    before = registry.list_provider_installations("ollama")
    assert len(before) == 1
    started_at = datetime.now(UTC)
    assert before[0].last_seen_at < started_at

    collector = OllamaRuntimeCollectorV1(reference, data_root=tmp_path)
    assert collector.tick() in {"ollama_runtime_collected", "ollama_runtime_partial"}

    refreshed = registry.list_provider_installations("ollama")
    assert len(refreshed) == 1
    assert refreshed[0].provider_installation_id == before[0].provider_installation_id
    assert started_at <= refreshed[0].last_seen_at <= datetime.now(UTC)
    assert refreshed[0].presence_state == "present"
    assert refreshed[0].version == before[0].version

    assert collector.tick() == "ollama_runtime_waiting"
    assert registry.list_provider_installations("ollama") == refreshed

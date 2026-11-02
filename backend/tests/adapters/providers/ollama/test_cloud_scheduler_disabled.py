"""Real unconfigured scheduler cannot start or create a database."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.composition.ollama_cloud_collection import OllamaCloudCollectionV1


def test_unadmitted_source_does_not_acquire_or_create_database(tmp_path: Path) -> None:
    path = tmp_path / "agentmonitor.db"
    collector = OllamaCloudCollectionV1(DatabaseRefV1(path, tmp_path))
    with pytest.raises(ValueError, match="ollama_cloud_source_not_admitted"):
        collector.acquire_next(datetime.now(UTC))
    assert not path.exists()

"""Real-service acceptance for the planned Ollama local catalog source."""

from datetime import UTC, datetime

from agentmonitor.adapters.providers.ollama.local_catalog.source import (
    read_local_catalog,
)

from tools.discovery.m6_local_inventory import read_json


def test_real_loopback_catalog_distinguishes_installed_and_loaded_models():
    before = (
        len(read_json("/api/tags")["models"]),
        len(read_json("/api/ps")["models"]),
    )
    started = datetime.now(UTC)
    result = read_local_catalog()
    completed = datetime.now(UTC)
    after = (
        len(read_json("/api/tags")["models"]),
        len(read_json("/api/ps")["models"]),
    )
    assert before == after, "local_model_state_changed_during_test"
    assert result.outcome == "success"
    assert result.daemon_version == "0.24.0"
    assert result.source == "ollama.local.catalog.v1"
    assert result.observed_at.tzinfo is not None
    assert started <= result.observed_at <= completed
    assert isinstance(result.installed, tuple)
    assert isinstance(result.loaded, tuple)
    assert (len(result.installed), len(result.loaded)) == before

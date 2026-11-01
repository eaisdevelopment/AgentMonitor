"""Real-service acceptance for the planned Ollama local catalog source."""

from agentmonitor.adapters.providers.ollama.local_catalog.source import (
    read_local_catalog,
)


def test_real_loopback_catalog_distinguishes_installed_and_loaded_models():
    result = read_local_catalog()
    assert result.outcome == "success"
    assert result.daemon_version == "0.24.0"
    assert result.source == "ollama.local.catalog.v1"
    assert result.observed_at.tzinfo is not None
    assert isinstance(result.installed, tuple)
    assert isinstance(result.loaded, tuple)

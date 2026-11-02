"""Real-service acceptance for the planned Ollama local catalog source."""

from datetime import UTC, datetime

from agentmonitor.adapters.providers.ollama.local_catalog.source import (
    read_local_catalog,
)

from tools.discovery.m6_local_inventory import read_json


def _model_count(path: str) -> int:
    models = read_json(path).get("models")
    assert isinstance(models, list)
    return len(models)


def test_real_loopback_catalog_distinguishes_installed_and_loaded_models() -> None:
    before = (
        _model_count("/api/tags"),
        _model_count("/api/ps"),
    )
    started = datetime.now(UTC)
    result = read_local_catalog()
    completed = datetime.now(UTC)
    after = (
        _model_count("/api/tags"),
        _model_count("/api/ps"),
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

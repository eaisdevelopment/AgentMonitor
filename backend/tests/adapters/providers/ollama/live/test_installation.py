"""Installation discovery uses the actual local Ollama executable."""

from datetime import UTC, datetime

from agentmonitor.adapters.providers.ollama.installation import discover_installation


def test_real_local_cli_version_is_independent_of_daemon():
    started = datetime.now(UTC)
    result = discover_installation()
    completed = datetime.now(UTC)
    assert result.outcome == "success"
    assert result.cli_version == "0.24.0"
    assert result.platform_id == "linux-x86_64"
    assert started <= result.observed_at <= completed

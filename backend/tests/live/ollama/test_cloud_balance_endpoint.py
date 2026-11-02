"""Real anonymous request to Ollama's one approved cloud balance endpoint."""

import time

from agentmonitor.adapters.providers.ollama.cloud_balance.source import (
    probe_cloud_balance_endpoint_v1,
)


def test_real_official_balance_endpoint_rejects_anonymous_access() -> None:
    """OLL-NET-002: production TLS transport reaches the official endpoint once."""
    result = probe_cloud_balance_endpoint_v1(
        deadline_monotonic=time.monotonic() + 10.0,
    )

    assert result.state == "unauthorized"
    assert result.reason_code == "ollama_cloud_unauthorized"
    assert result.http_status == 401
    assert result.balance is None
    assert result.retry_after_seconds is None
    assert result.retry_after_state == "not_applicable"


def test_probe_deadline_stops_the_isolated_network_process() -> None:
    started = time.monotonic()

    result = probe_cloud_balance_endpoint_v1(
        deadline_monotonic=started + 0.001,
    )

    assert result.state == "deadline_exceeded"
    assert result.reason_code == "ollama_cloud_deadline_exceeded"
    assert time.monotonic() - started < 2.0

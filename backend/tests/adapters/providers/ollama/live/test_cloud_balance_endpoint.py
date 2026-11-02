"""Real anonymous request to Ollama's one approved cloud balance endpoint."""

import time

from agentmonitor.adapters.providers.ollama.cloud_balance.source import (
    read_cloud_balance_once_v1,
)


def test_real_official_balance_endpoint_rejects_anonymous_access() -> None:
    """OLL-NET-002: production TLS transport reaches the official endpoint once."""
    result = read_cloud_balance_once_v1(
        authorization=None,
        deadline_monotonic=time.monotonic() + 10.0,
    )

    assert result.state == "unauthorized"
    assert result.reason_code == "ollama_cloud_unauthorized"
    assert result.http_status == 401
    assert result.balance is None
    assert result.retry_after_seconds is None

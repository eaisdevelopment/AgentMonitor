"""Pure policy checks for the fixed Ollama cloud balance source."""

from inspect import signature

from agentmonitor.adapters.providers.ollama.cloud_balance.source import (
    CLOUD_BALANCE_POLICY_V1,
    read_cloud_balance_once_v1,
)


def test_cloud_balance_source_is_one_fixed_bounded_request() -> None:
    """M6-A09/OLL-SEC-012: callers cannot choose the network destination."""
    policy = CLOUD_BALANCE_POLICY_V1

    assert policy.scheme == "https"
    assert policy.host == "ollama.com"
    assert policy.port == 443
    assert policy.method == "GET"
    assert policy.path == "/api/balance"
    assert policy.request_count == 1
    assert policy.automatic_retry_count == 0
    assert not policy.follow_redirects
    assert not policy.use_environment_proxy
    assert policy.connect_timeout_seconds < policy.operation_timeout_seconds
    assert policy.read_timeout_seconds < policy.operation_timeout_seconds
    assert 0 < policy.maximum_header_count <= 100
    assert 0 < policy.maximum_header_bytes <= 64 * 1024
    assert 0 < policy.maximum_body_bytes <= 256 * 1024
    assert tuple(signature(read_cloud_balance_once_v1).parameters) == (
        "authorization",
        "deadline_monotonic",
    )

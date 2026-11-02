"""Pure classification of Ollama balance HTTP status codes."""

from agentmonitor.adapters.providers.ollama.cloud_balance.status import classify_status


def test_balance_statuses_remain_distinct():
    assert classify_status(200) == "success"
    assert classify_status(401) == "unauthorized"
    assert classify_status(403) == "access_denied"
    assert classify_status(429) == "rate_limited"
    assert classify_status(503) == "provider_unavailable"
    assert classify_status(302) == "unexpected_response"

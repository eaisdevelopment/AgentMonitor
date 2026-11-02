"""V2 no-request terminal state has a terminal time, not a response time."""

from datetime import UTC, datetime

import pytest
from agentmonitor.contracts.collection_control_v1 import (
    OllamaCloudNoResponseCompletionV2,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def test_no_response_completion_does_not_claim_response() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    terminal = OllamaCloudNoResponseCompletionV2(
        OpaqueIdV1("attempt"),
        OpaqueIdV1("owner"),
        OpaqueIdV1("schedule"),
        1,
        now,
        now,
        "store_unavailable",
        "authorization_unavailable",
    )
    assert terminal.terminal_at == now
    assert terminal.dispatch_certainty == "not_started"
    assert not hasattr(terminal, "response_received_at")
    with pytest.raises(ValueError):
        OllamaCloudNoResponseCompletionV2(
            OpaqueIdV1("attempt"),
            OpaqueIdV1("owner"),
            OpaqueIdV1("schedule"),
            1,
            now,
            now,
            "store_unavailable",
            "provider_unavailable",
        )


def test_credential_update_contention_is_a_distinct_no_request_terminal() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    terminal = OllamaCloudNoResponseCompletionV2(
        OpaqueIdV1("attempt"),
        OpaqueIdV1("owner"),
        OpaqueIdV1("schedule"),
        1,
        now,
        now,
        "credential_update_in_progress",
        "authorization_unavailable",
    )
    assert terminal.CONTRACT_VERSION == "1.1.0"
    assert terminal.reason_code == "credential_update_in_progress"
    with pytest.raises(ValueError):
        OllamaCloudNoResponseCompletionV2(
            OpaqueIdV1("attempt"),
            OpaqueIdV1("owner"),
            OpaqueIdV1("schedule"),
            1,
            now,
            now,
            "credential_update_in_progress",
            "provider_unavailable",
        )

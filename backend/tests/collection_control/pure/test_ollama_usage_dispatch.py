"""Pure no-request classification; constructed outcomes never enter I/O."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from agentmonitor.adapters.providers.ollama.api.source import OllamaUsageResultV1
from agentmonitor.contracts.collection_control_v1 import OllamaCloudRequestLeaseV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1

NOW = datetime(2026, 11, 11, tzinfo=UTC)


def _lease() -> OllamaCloudRequestLeaseV1:
    return OllamaCloudRequestLeaseV1(
        OpaqueIdV1("admission"),
        OpaqueIdV1("worker"),
        OpaqueIdV1("schedule"),
        OpaqueIdV1("account"),
        1,
        NOW,
        NOW + timedelta(seconds=60),
        NOW + timedelta(seconds=120),
        1,
    )


def _terminal(result: OllamaUsageResultV1) -> Any:
    from agentmonitor.composition import ollama_usage_dispatch

    return ollama_usage_dispatch.usage_no_response_terminal(
        result, _lease(), completed_at=NOW + timedelta(seconds=1)
    )


@pytest.mark.parametrize(
    "state,attempts,source_state,reason",
    [
        (
            "authorization_unavailable",
            0,
            "authorization_unavailable",
            "store_unavailable",
        ),
        (
            "authorization_unavailable",
            1,
            "authorization_unavailable",
            "store_unavailable",
        ),
        ("worker_required", 0, "internal_adapter_error", "source_not_started"),
        ("deadline_exceeded", 0, "deadline_exceeded", "source_not_started"),
    ],
)
def test_only_proven_pre_send_failure_yields_no_response_terminal(
    state: Any,
    attempts: int,
    source_state: str,
    reason: str,
) -> None:
    terminal = _terminal(
        OllamaUsageResultV1(state, "ollama_usage_" + state, None, attempts)
    )
    assert terminal is not None
    assert terminal.admission_id == _lease().admission_id
    assert terminal.scheduler_instance_id == _lease().scheduler_instance_id
    assert terminal.schedule_id == _lease().schedule_id
    assert terminal.fencing_token == _lease().fencing_token
    assert terminal.started_at == NOW
    assert terminal.terminal_at == NOW + timedelta(seconds=1)
    assert terminal.dispatch_certainty == "not_started"
    assert terminal.source_state == source_state
    assert terminal.reason_code == reason
    assert not hasattr(terminal, "response_received_at")


@pytest.mark.parametrize(
    "state,attempts,status",
    [
        ("deadline_exceeded", 1, None),
        ("provider_unavailable", 1, None),
        ("invalid_provider_data", 1, None),
        ("internal_error", 1, None),
        ("worker_required", 1, None),
        ("rate_limited", 1, 429),
        ("success", 1, 200),
        ("unauthorized", 1, 401),
        ("authorization_unavailable", 1, 200),
    ],
)
def test_possible_dispatch_or_response_never_becomes_no_request(
    state: Any,
    attempts: int,
    status: int | None,
) -> None:
    assert (
        _terminal(
            OllamaUsageResultV1(
                state,
                "ollama_usage_" + state,
                None,
                attempts,
                http_status=status,
            )
        )
        is None
    )


@pytest.mark.parametrize(
    "change",
    [
        {"requests_made": -1},
        {"requests_made": 2},
        {"requests_made": True},
        {"retry_after_seconds": 60},
        {"money_availability": "not_reported"},
    ],
)
def test_inconsistent_pre_send_metadata_cannot_release_gate(
    change: dict[str, Any],
) -> None:
    result = OllamaUsageResultV1(
        "authorization_unavailable", "ollama_usage_authorization_unavailable", None, 1
    )
    assert _terminal(replace(result, **change)) is None

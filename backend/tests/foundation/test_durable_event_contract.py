"""Pure CTR-EVT-001 validation, with no I/O or provider observations."""

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from agentmonitor.contracts.common_v1 import (
    EventEnvelopeV1,
    OpaqueIdV1,
    TechnicalValueV1,
)


@dataclass(frozen=True, slots=True)
class Notice(TechnicalValueV1):
    count: int


def _envelope() -> EventEnvelopeV1:
    now = datetime(2026, 9, 29, tzinfo=UTC)
    return EventEnvelopeV1(
        OpaqueIdV1("event"),
        "capacity.committed.v1",
        now,
        now,
        "M05",
        "1.0.0",
        OpaqueIdV1("correlation"),
        None,
        OpaqueIdV1("subject"),
    )


def test_durable_event_retains_typed_notice_and_rejects_invalid_sequence() -> None:
    from agentmonitor.contracts.events_v1 import DurableEventV1

    payload = Notice(1)
    event = DurableEventV1(_envelope(), 1, "capacity:subject", 1, payload, "a" * 64)
    assert event.payload == payload
    with pytest.raises(ValueError, match="durable_event_invalid"):
        DurableEventV1(_envelope(), 1, "capacity:subject", 0, payload, "a" * 64)


@pytest.mark.parametrize("digest", ["x" * 64, "a" * 63, "A" * 64])
def test_durable_event_rejects_noncanonical_digest(digest: str) -> None:
    from agentmonitor.contracts.events_v1 import DurableEventV1

    with pytest.raises(ValueError, match="durable_event_invalid"):
        DurableEventV1(_envelope(), 1, "capacity:subject", 1, Notice(1), digest)

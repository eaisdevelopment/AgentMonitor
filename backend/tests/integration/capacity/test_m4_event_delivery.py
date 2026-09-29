"""Actual event/committed-consumer-receipt verification; never seed a receipt."""

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    CapacityRepositoryErrorV1,
    SqliteCapacityRepositoryV1,
)
from agentmonitor.contracts.capacity_v1 import CapacityCommittedNoticeV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.events_v1 import DurableEventV1
from agentmonitor.modules.capacity.application.queries import (
    AcknowledgeCapacityEventV1,
    ReadCapacityEventsV1,
)


def _selected_actual_receipt() -> tuple[DatabaseRefV1, OpaqueIdV1, OpaqueIdV1, str]:
    if os.environ.get("AGENTMONITOR_RUN_CAPACITY_EVENT_ACK") != "1":
        pytest.skip(
            "NOT RUN: actual committed consumer receipt acknowledgement not selected"
        )
    # Root supplies these exact references only after the consumer commit.
    names = (
        "AGENTMONITOR_TEST_DATA_ROOT",
        "AGENTMONITOR_TEST_CAPACITY_ACK_EVENT_ID",
        "AGENTMONITOR_TEST_CAPACITY_ACK_RECEIPT_ID",
        "AGENTMONITOR_TEST_CAPACITY_ACK_CONSUMER",
    )
    values = tuple(os.environ.get(name) for name in names)
    assert all(values), (
        "actual committed event, receipt and consumer selectors are required"
    )
    root_value, event_value, receipt_value, consumer = values
    assert root_value is not None
    assert event_value is not None
    assert receipt_value is not None
    assert consumer is not None
    root = Path(root_value)
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    return reference, OpaqueIdV1(event_value), OpaqueIdV1(receipt_value), consumer


def _events(
    repository: SqliteCapacityRepositoryV1, consumer: str, as_of: datetime
) -> Iterator[DurableEventV1[CapacityCommittedNoticeV1]]:
    cursor = None
    for _ in range(100):
        page = ReadCapacityEventsV1(repository)(consumer, cursor, as_of, 200)
        yield from page.events
        if not page.events:
            return
        assert page.next_cursor != cursor
        cursor = page.next_cursor
    pytest.fail("actual event verification exceeded bounded read budget")


def test_actual_consumer_ack_is_exact_idempotent_and_survives_reopen() -> None:
    reference, event_id, receipt_id, consumer = _selected_actual_receipt()
    repository = SqliteCapacityRepositoryV1(reference)
    as_of = datetime.now(UTC)
    observed = next(
        (
            event
            for event in _events(repository, "m4-capacity-ack-observer", as_of)
            if event.envelope.event_id == event_id
        ),
        None,
    )
    assert observed is not None, "selected actual committed event must exist"
    digest = observed.payload_digest
    wrong_digest = digest[:-1] + ("0" if digest[-1] != "0" else "1")
    with pytest.raises(
        CapacityRepositoryErrorV1, match="capacity_event_digest_mismatch"
    ):
        AcknowledgeCapacityEventV1(repository)(
            consumer, event_id, wrong_digest, receipt_id, as_of
        )
    AcknowledgeCapacityEventV1(repository)(
        consumer, event_id, digest, receipt_id, as_of
    )
    AcknowledgeCapacityEventV1(repository)(
        consumer, event_id, digest, receipt_id, as_of
    )
    reopened = SqliteCapacityRepositoryV1(reference)
    assert all(
        event.envelope.event_id != event_id
        for event in _events(reopened, consumer, as_of)
    )
    assert any(
        event.envelope.event_id == event_id
        for event in _events(reopened, "m4-capacity-ack-observer", as_of)
    ), "acknowledgement must preserve the actual outbox record"

"""Actual event/committed-consumer-receipt verification; never seed a receipt."""

import json
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    _ACKNOWLEDGED_CAPACITY_EVENT_EVIDENCE_SQL,
    CapacityRepositoryErrorV1,
    SqliteCapacityRepositoryV1,
)
from agentmonitor.contracts.capacity_v1 import CapacityCommittedNoticeV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.events_v1 import DurableEventV1
from agentmonitor.modules.capacity.application.queries import (
    AcknowledgeCapacityEventV1,
    CapacityEventEvidenceErrorV1,
    ReadAcknowledgedCapacityEventsV1,
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

    acknowledged = ReadAcknowledgedCapacityEventsV1(reopened)(
        consumer,
        (event_id,),
        as_of,
    )
    assert len(acknowledged) == 1
    assert acknowledged[0].event == observed
    assert acknowledged[0].acknowledgement_receipt_id == receipt_id
    assert acknowledged[0].acknowledged_at <= as_of


def test_acknowledged_event_evidence_selector_bounds_fail_closed(
    tmp_path: Path,
) -> None:
    """M5-CDX-ALERT-008: the compatible M05 query has closed selectors."""

    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    reader = ReadAcknowledgedCapacityEventsV1(SqliteCapacityRepositoryV1(reference))
    as_of = datetime.now(UTC)
    first = OpaqueIdV1("event-one")
    invalid: tuple[tuple[object, object, object], ...] = (
        ("bad consumer", (first,), as_of),
        ("consumer", (), as_of),
        ("consumer", (first, first), as_of),
        (
            "consumer",
            tuple(OpaqueIdV1(f"event-{index}") for index in range(201)),
            as_of,
        ),
        ("consumer", [first], as_of),
        ("consumer", ("event-one",), as_of),
        ("consumer", (first,), datetime.now()),
    )

    for consumer, event_ids, selected_as_of in invalid:
        with pytest.raises(CapacityEventEvidenceErrorV1) as raised:
            reader(
                cast(str, consumer),
                cast(tuple[OpaqueIdV1, ...], event_ids),
                cast(datetime, selected_as_of),
            )
        assert raised.value.code == "capacity_event_evidence_selector_invalid"

    with pytest.raises(CapacityEventEvidenceErrorV1) as missing:
        reader("consumer", (first,), as_of)
    assert missing.value.code == "capacity_event_evidence_event_missing"

    opaque = OpaqueIdV1("opaque selector / " + "x" * 80)
    with pytest.raises(CapacityEventEvidenceErrorV1) as opaque_missing:
        reader("consumer", (opaque,), as_of)
    assert opaque_missing.value.code == "capacity_event_evidence_event_missing"

    exact_limit = tuple(
        OpaqueIdV1(f"opaque selector {index} / " + "x" * 80) for index in range(200)
    )
    with pytest.raises(CapacityEventEvidenceErrorV1) as limit_missing:
        reader("consumer", exact_limit, as_of)
    assert limit_missing.value.code == "capacity_event_evidence_event_missing"

    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            plan = tuple(
                str(row[3])
                for row in connection.exec_driver_sql(
                    "EXPLAIN QUERY PLAN " + _ACKNOWLEDGED_CAPACITY_EVENT_EVIDENCE_SQL,
                    (
                        json.dumps([first.value], separators=(",", ":")),
                        "consumer",
                    ),
                ).all()
            )
    assert any(
        "SEARCH e USING INDEX sqlite_autoindex_capacity_event_outbox_1" in step
        for step in plan
    )
    assert any(
        "SEARCH d USING INDEX sqlite_autoindex_capacity_event_delivery_1" in step
        for step in plan
    )
    assert all("SCAN e" not in step and "SCAN d" not in step for step in plan)

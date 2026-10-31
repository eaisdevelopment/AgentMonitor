"""CTR-EVT-001: immutable delivery records; storage remains producer-owned."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Protocol

from agentmonitor.contracts.common_v1 import (
    EventEnvelopeV1,
    OpaqueIdV1,
    QueryAvailabilityV1,
    TechnicalValueV1,
)

_STREAM = re.compile(r"[A-Za-z0-9_.:/-]{1,128}\Z")
_DIGEST = re.compile(r"[a-f0-9]{64}\Z")


@dataclass(frozen=True, slots=True)
class DurableEventV1[PayloadT: TechnicalValueV1](TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-EVT-001"
    OWNER: ClassVar[str] = "PLAN-INT"
    envelope: EventEnvelopeV1
    event_schema_major: int
    stream_key: str
    stream_sequence: int
    payload: PayloadT
    payload_digest: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.event_schema_major) is not int
            or self.event_schema_major < 1
            or type(self.stream_sequence) is not int
            or self.stream_sequence < 1
            or not _STREAM.fullmatch(self.stream_key)
            or not _DIGEST.fullmatch(self.payload_digest)
            or not isinstance(self.payload, TechnicalValueV1)
            or self.envelope.recorded_at < self.envelope.occurred_at
        ):
            raise ValueError("durable_event_invalid")


@dataclass(frozen=True, slots=True)
class DurableEventBatchV1[PayloadT: TechnicalValueV1](TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-EVT-001"
    OWNER: ClassVar[str] = "PLAN-INT"
    events: tuple[DurableEventV1[PayloadT], ...]
    next_cursor: str | None
    availability: QueryAvailabilityV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            len(self.events) > 200
            or len({item.envelope.event_id for item in self.events}) != len(self.events)
            or self.next_cursor is not None
            and not _STREAM.fullmatch(self.next_cursor)
        ):
            raise ValueError("durable_event_batch_invalid")


class ReadEventBatchV1[PayloadT: TechnicalValueV1](Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-EVT-001"
    OWNER: ClassVar[str] = "PLAN-INT"

    def __call__(
        self,
        consumer_key: str,
        after_cursor: str | None,
        as_of: datetime,
        limit: int = 200,
    ) -> DurableEventBatchV1[PayloadT]: ...


class AcknowledgeEventDeliveryV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-EVT-001"
    OWNER: ClassVar[str] = "PLAN-INT"

    def __call__(
        self,
        consumer_key: str,
        event_id: OpaqueIdV1,
        payload_digest: str,
        receipt_id: OpaqueIdV1,
        as_of: datetime,
    ) -> None: ...

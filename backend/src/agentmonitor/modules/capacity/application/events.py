"""M05's public delivery facades over its exclusively owned event storage."""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import ClassVar, Literal, Protocol, cast

from agentmonitor.contracts.capacity_v1 import (
    CapacityCommittedNoticeV1,
    CapacityProjectionEventPayloadV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1, TechnicalValueV1
from agentmonitor.contracts.events_v1 import DurableEventBatchV1, DurableEventV1

CapacityEventEvidenceErrorCodeV1 = Literal[
    "capacity_event_evidence_selector_invalid",
    "capacity_event_evidence_event_missing",
    "capacity_event_evidence_delivery_unacknowledged",
    "capacity_event_evidence_invalid",
]
_CAPACITY_EVENT_EVIDENCE_ERROR_CODES = frozenset(
    (
        "capacity_event_evidence_selector_invalid",
        "capacity_event_evidence_event_missing",
        "capacity_event_evidence_delivery_unacknowledged",
        "capacity_event_evidence_invalid",
    )
)
_EVENT_EVIDENCE_CONSUMER = re.compile(r"[A-Za-z0-9_.-]{1,64}\Z")


class CapacityEventEvidenceErrorV1(ValueError):
    """Closed M05 evidence failure without stored values or SQL detail."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-004"
    OWNER: ClassVar[str] = "PLAN-M05"

    def __init__(self, code: CapacityEventEvidenceErrorCodeV1) -> None:
        if code not in _CAPACITY_EVENT_EVIDENCE_ERROR_CODES:
            raise ValueError("capacity_event_evidence_error_code_invalid")
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class AcknowledgedCapacityEventV1(TechnicalValueV1):
    """One exact capacity event and its durable consumer acknowledgement."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-004"
    OWNER: ClassVar[str] = "PLAN-M05"
    event: DurableEventV1[CapacityCommittedNoticeV1]
    acknowledgement_receipt_id: OpaqueIdV1
    acknowledged_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not isinstance(self.event, DurableEventV1)
            or not isinstance(self.acknowledgement_receipt_id, OpaqueIdV1)
            or not isinstance(self.acknowledged_at, datetime)
        ):
            raise TypeError("capacity_event_evidence_value_invalid")


def _validate_capacity_event_evidence_selector_v1(
    consumer_key: str,
    event_ids: tuple[OpaqueIdV1, ...],
    as_of: datetime,
) -> None:
    if (
        type(consumer_key) is not str
        or _EVENT_EVIDENCE_CONSUMER.fullmatch(consumer_key) is None
        or type(event_ids) is not tuple
        or not 1 <= len(event_ids) <= 200
        or any(not isinstance(event_id, OpaqueIdV1) for event_id in event_ids)
        or len(set(event_ids)) != len(event_ids)
        or not isinstance(as_of, datetime)
        or as_of.utcoffset() != timedelta(0)
    ):
        raise CapacityEventEvidenceErrorV1("capacity_event_evidence_selector_invalid")


class CapacityEventRepositoryV1(Protocol):
    def read_capacity_events(
        self,
        consumer_key: str,
        after_cursor: str | None,
        as_of: datetime,
        limit: int,
    ) -> DurableEventBatchV1[CapacityCommittedNoticeV1]: ...

    def acknowledge_capacity_event(
        self,
        consumer_key: str,
        event_id: OpaqueIdV1,
        payload_digest: str,
        receipt_id: OpaqueIdV1,
        as_of: datetime,
    ) -> None: ...


class ReadCapacityEventsV1:
    def __init__(self, repository: CapacityEventRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self,
        consumer_key: str,
        after_cursor: str | None,
        as_of: datetime,
        limit: int = 200,
    ) -> DurableEventBatchV1[CapacityCommittedNoticeV1]:
        return self._repository.read_capacity_events(
            consumer_key, after_cursor, as_of, limit
        )


class AcknowledgeCapacityEventV1:
    """Composition calls only after its consumer receipt has durably committed."""

    def __init__(self, repository: CapacityEventRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self,
        consumer_key: str,
        event_id: OpaqueIdV1,
        payload_digest: str,
        receipt_id: OpaqueIdV1,
        as_of: datetime,
    ) -> None:
        self._repository.acknowledge_capacity_event(
            consumer_key, event_id, payload_digest, receipt_id, as_of
        )


class CapacityEventEvidenceRepositoryV1(Protocol):
    def read_acknowledged_capacity_events(
        self,
        consumer_key: str,
        event_ids: tuple[OpaqueIdV1, ...],
        as_of: datetime,
    ) -> tuple[
        tuple[DurableEventV1[CapacityCommittedNoticeV1], OpaqueIdV1, datetime], ...
    ]: ...


class ReadAcknowledgedCapacityEventsV1:
    """Read bounded exact-ID acknowledgement evidence without outbox paging."""

    CONTRACT_ID = "CTR-CAP-004"
    OWNER = "PLAN-M05"

    def __init__(self, repository: CapacityEventEvidenceRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self,
        consumer_key: str,
        event_ids: tuple[OpaqueIdV1, ...],
        as_of: datetime,
    ) -> tuple[AcknowledgedCapacityEventV1, ...]:
        _validate_capacity_event_evidence_selector_v1(consumer_key, event_ids, as_of)
        try:
            records = self._repository.read_acknowledged_capacity_events(
                consumer_key, event_ids, as_of
            )
        except (TypeError, ValueError) as error:
            code = getattr(error, "code", None)
            if code in _CAPACITY_EVENT_EVIDENCE_ERROR_CODES:
                raise CapacityEventEvidenceErrorV1(
                    cast(CapacityEventEvidenceErrorCodeV1, code)
                ) from None
            raise CapacityEventEvidenceErrorV1(
                "capacity_event_evidence_invalid"
            ) from None
        try:
            if len(records) != len(event_ids):
                raise ValueError
            results = tuple(
                AcknowledgedCapacityEventV1(event, receipt_id, acknowledged_at)
                for event, receipt_id, acknowledged_at in records
            )
            if any(
                result.event.envelope.event_id != event_id
                for result, event_id in zip(results, event_ids, strict=True)
            ):
                raise ValueError
            return results
        except (TypeError, ValueError):
            raise CapacityEventEvidenceErrorV1(
                "capacity_event_evidence_invalid"
            ) from None


class CapacityProjectionEventRepositoryV1(Protocol):
    def read_capacity_projection_events(
        self,
        consumer_key: str,
        after_cursor: str | None,
        as_of: datetime,
        limit: int,
    ) -> DurableEventBatchV1[CapacityProjectionEventPayloadV1]: ...

    def acknowledge_capacity_projection_event(
        self,
        consumer_key: str,
        event_id: OpaqueIdV1,
        payload_digest: str,
        receipt_id: OpaqueIdV1,
        as_of: datetime,
    ) -> None: ...


class ReadCapacityProjectionEventsV1:
    CONTRACT_ID = "CTR-CAP-008"
    OWNER = "PLAN-M05"

    def __init__(self, repository: CapacityProjectionEventRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self,
        consumer_key: str,
        after_cursor: str | None,
        as_of: datetime,
        limit: int = 200,
    ) -> DurableEventBatchV1[CapacityProjectionEventPayloadV1]:
        return self._repository.read_capacity_projection_events(
            consumer_key, after_cursor, as_of, limit
        )


class AcknowledgeCapacityProjectionEventV1:
    CONTRACT_ID = "CTR-CAP-008"
    OWNER = "PLAN-M05"

    def __init__(self, repository: CapacityProjectionEventRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self,
        consumer_key: str,
        event_id: OpaqueIdV1,
        payload_digest: str,
        receipt_id: OpaqueIdV1,
        as_of: datetime,
    ) -> None:
        self._repository.acknowledge_capacity_projection_event(
            consumer_key, event_id, payload_digest, receipt_id, as_of
        )

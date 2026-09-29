"""M05's public delivery facades over its exclusively owned event storage."""

from datetime import datetime
from typing import Protocol

from agentmonitor.contracts.capacity_v1 import (
    CapacityCommittedNoticeV1,
    CapacityProjectionEventPayloadV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.events_v1 import DurableEventBatchV1


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

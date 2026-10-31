"""Public M04 current-condition facade, delegating only typed owned ports."""

from datetime import datetime
from typing import Protocol

from agentmonitor.contracts.collection_control_v1 import (
    CollectorAlertConditionV1,
    CollectorAlertQueryV1,
    CollectorHealthChangedV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1, QueryPageV1
from agentmonitor.contracts.events_v1 import DurableEventBatchV1


class CollectorAlertRepositoryV1(Protocol):
    async def get_current(
        self, query: CollectorAlertQueryV1
    ) -> QueryPageV1[CollectorAlertConditionV1]: ...
    async def refresh(
        self, query: CollectorAlertQueryV1
    ) -> QueryPageV1[CollectorAlertConditionV1]: ...
    def read_events(
        self,
        consumer_key: str,
        after_cursor: str | None,
        as_of: datetime,
        limit: int = 200,
    ) -> DurableEventBatchV1[CollectorHealthChangedV1]: ...
    def acknowledge_event(
        self,
        consumer_key: str,
        event_id: OpaqueIdV1,
        payload_digest: str,
        receipt_id: OpaqueIdV1,
        as_of: datetime,
    ) -> None: ...


class CollectorAlertConditionServiceV1:
    def __init__(self, repository: CollectorAlertRepositoryV1) -> None:
        self._repository = repository

    async def get_current(
        self, query: CollectorAlertQueryV1
    ) -> QueryPageV1[CollectorAlertConditionV1]:
        return await self._repository.get_current(query)

    async def refresh(
        self, query: CollectorAlertQueryV1
    ) -> QueryPageV1[CollectorAlertConditionV1]:
        return await self._repository.refresh(query)

    def read_events(
        self,
        consumer_key: str,
        after_cursor: str | None,
        as_of: datetime,
        limit: int = 200,
    ) -> DurableEventBatchV1[CollectorHealthChangedV1]:
        return self._repository.read_events(consumer_key, after_cursor, as_of, limit)

    def acknowledge_event(
        self,
        consumer_key: str,
        event_id: OpaqueIdV1,
        payload_digest: str,
        receipt_id: OpaqueIdV1,
        as_of: datetime,
    ) -> None:
        self._repository.acknowledge_event(
            consumer_key, event_id, payload_digest, receipt_id, as_of
        )

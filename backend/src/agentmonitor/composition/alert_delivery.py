"""Service-owned delivery from M05's durable outbox to M07's consumer."""

import asyncio
import json
from datetime import UTC, datetime

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.alerting.sqlite.capacity_consumer import (
    SqliteCapacityAlertRepositoryV1,
)
from agentmonitor.adapters.persistence.alerting.sqlite.repository import (
    SqliteAlertingRepositoryV1,
)
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.contracts.alerting_v1 import AlertSignalReceiptV1
from agentmonitor.contracts.capacity_v1 import CapacityCommittedNoticeV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.events_v1 import DurableEventV1
from agentmonitor.modules.alerting.application.consume import (
    ConsumeCapacityAlertEventV1,
    DeliverCapacityAlertEventV1,
)
from agentmonitor.modules.alerting.application.rules import ResolveEffectiveAlertRuleV1
from agentmonitor.modules.capacity.application.events import (
    AcknowledgeCapacityEventV1,
    ReadCapacityEventsV1,
)
from agentmonitor.modules.capacity.application.queries import (
    ListCapacityAlertConditionsV1,
)
from agentmonitor.modules.registry.application.accounts import (
    AlertScopeAndSubjectQueryV1,
    ListAccountResourcesV1,
    ListAccountsV1,
    ResolveAlertSubjectScopeV1,
)


class CapacityAlertDeliveryV1:
    """Compose published M02/M05/M07 ports without reading foreign tables."""

    def __init__(self, reference: DatabaseRefV1) -> None:
        registry = SqliteRegistryRepositoryV1(reference)
        capacity = SqliteCapacityRepositoryV1(reference)
        rules = SqliteAlertingRepositoryV1(reference)
        consume = ConsumeCapacityAlertEventV1(
            SqliteCapacityAlertRepositoryV1(reference),
            ListCapacityAlertConditionsV1(capacity),
            ResolveAlertSubjectScopeV1(registry),
            ListAccountResourcesV1(registry),
            ResolveEffectiveAlertRuleV1(
                rules,
                ResolveAlertSubjectScopeV1(registry),
                AlertScopeAndSubjectQueryV1(registry),
            ),
        )
        self._deliver = DeliverCapacityAlertEventV1(
            consume, AcknowledgeCapacityEventV1(capacity)
        )
        self._read = ReadCapacityEventsV1(capacity)
        self._accounts = ListAccountsV1(registry)
        self._resources = ListAccountResourcesV1(registry)

    def deliver_one(
        self,
        event: DurableEventV1[CapacityCommittedNoticeV1],
        account_id: OpaqueIdV1,
        *,
        as_of: datetime,
    ) -> AlertSignalReceiptV1:
        return self._deliver(event, account_id, as_of=as_of)

    def deliver_next(self, *, as_of: datetime) -> str:
        batch = self._read(
            DeliverCapacityAlertEventV1.CONSUMER_KEY, None, as_of, limit=1
        )
        if not batch.events:
            return "capacity_alert_delivery_idle"
        event = batch.events[0]
        accounts = self._accounts.page("claude", as_of=as_of, limit=200)
        if accounts.has_more:
            raise ValueError("capacity_alert_registry_scope_incomplete")
        matches = tuple(
            account.account_id
            for account in accounts.items
            if any(
                resource.resource_id == event.envelope.subject_id
                for resource in self._resources(account.account_id)
            )
        )
        if len(matches) != 1:
            raise ValueError("capacity_alert_subject_unresolved")
        self.deliver_one(event, matches[0], as_of=as_of)
        return "capacity_alert_delivered"

    async def run(self) -> None:
        previous: str | None = None
        while True:
            work = asyncio.create_task(
                asyncio.to_thread(self.deliver_next, as_of=datetime.now(UTC))
            )
            try:
                status = await asyncio.shield(work)
            except asyncio.CancelledError:
                await work
                raise
            except (OSError, RuntimeError, ValueError):
                status = "capacity_alert_delivery_unavailable"
            if status != previous:
                print(json.dumps({"event": status}), flush=True)
                previous = status
            await asyncio.sleep(5)

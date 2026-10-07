"""Service-owned delivery from M05's durable outbox to M07's consumer."""

import asyncio
import json
from datetime import UTC, datetime, timedelta

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


def _next_registry_cursor_v1(
    *,
    has_more: bool,
    next_key: str | None,
    after_key: str | None,
    seen_cursors: frozenset[str],
    item_count: int,
    last_account_id: str | None,
) -> str | None:
    """Accept only a complete, advancing account-page continuation."""

    invalid_shape = (
        type(has_more) is not bool
        or type(item_count) is not int
        or not 0 <= item_count <= 200
        or (item_count == 0) != (last_account_id is None)
    )
    if invalid_shape:
        raise ValueError("capacity_alert_registry_scope_incomplete")
    if not has_more:
        if next_key is not None:
            raise ValueError("capacity_alert_registry_scope_incomplete")
        return None
    if (
        item_count == 0
        or type(next_key) is not str
        or not next_key
        or next_key != last_account_id
        or next_key == after_key
        or next_key in seen_cursors
    ):
        raise ValueError("capacity_alert_registry_scope_incomplete")
    return next_key


def _unique_registry_account_ids_v1(
    account_ids: tuple[OpaqueIdV1, ...],
    seen_account_ids: frozenset[OpaqueIdV1],
) -> frozenset[OpaqueIdV1]:
    """Reject duplicate Registry identities within or across pages."""

    current = frozenset(account_ids)
    if len(current) != len(account_ids) or not current.isdisjoint(seen_account_ids):
        raise ValueError("capacity_alert_registry_scope_incomplete")
    return seen_account_ids | current


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
        self._registry_scope = AlertScopeAndSubjectQueryV1(registry)

    def deliver_one(
        self,
        event: DurableEventV1[CapacityCommittedNoticeV1],
        account_id: OpaqueIdV1,
        *,
        as_of: datetime,
    ) -> AlertSignalReceiptV1:
        return self._deliver(event, account_id, as_of=as_of)

    def _account_for_subject(
        self,
        subject_id: OpaqueIdV1,
        *,
        as_of: datetime,
    ) -> OpaqueIdV1:
        if as_of.utcoffset() != timedelta(0):
            raise ValueError("capacity_alert_registry_scope_incomplete")
        snapshot = self._registry_scope("global")
        if snapshot.completeness_state != "complete":
            raise ValueError("capacity_alert_registry_scope_incomplete")
        expected_revision = snapshot.registry_revision
        expected_account_ids = frozenset(snapshot.account_ids)
        expected_resource_ids = frozenset(snapshot.resource_ids)
        after_key: str | None = None
        seen_cursors: frozenset[str] = frozenset()
        seen_page_account_ids: frozenset[OpaqueIdV1] = frozenset()
        seen_account_ids: frozenset[OpaqueIdV1] = frozenset()
        seen_resource_ids: frozenset[OpaqueIdV1] = frozenset()
        matches: list[OpaqueIdV1] = []
        while True:
            page = self._accounts.page(
                None,
                as_of=as_of,
                limit=200,
                after_key=after_key,
            )
            if (
                page.availability.state != "available"
                or page.availability.as_of != as_of
                or any(
                    account.registry_revision != expected_revision
                    for account in page.items
                )
            ):
                raise ValueError("capacity_alert_registry_scope_incomplete")
            account_ids = tuple(account.account_id for account in page.items)
            seen_page_account_ids = _unique_registry_account_ids_v1(
                account_ids, seen_page_account_ids
            )
            for account in page.items:
                if account.lifecycle == "archived":
                    continue
                seen_account_ids = _unique_registry_account_ids_v1(
                    (account.account_id,), seen_account_ids
                )
                resources = self._resources(account.account_id)
                if any(
                    resource.registry_revision != expected_revision
                    or resource.account_id != account.account_id
                    for resource in resources
                ):
                    raise ValueError("capacity_alert_registry_scope_incomplete")
                active_resource_ids = tuple(
                    resource.resource_id
                    for resource in resources
                    if resource.lifecycle == "active"
                )
                seen_resource_ids = _unique_registry_account_ids_v1(
                    active_resource_ids, seen_resource_ids
                )
                if subject_id in active_resource_ids:
                    matches.append(account.account_id)
            last_account_id = account_ids[-1].value if account_ids else None
            next_key = _next_registry_cursor_v1(
                has_more=page.has_more,
                next_key=page.next_key,
                after_key=after_key,
                seen_cursors=seen_cursors,
                item_count=len(page.items),
                last_account_id=last_account_id,
            )
            if next_key is None:
                break
            seen_cursors = seen_cursors | frozenset((next_key,))
            after_key = next_key
        if (
            seen_account_ids != expected_account_ids
            or seen_resource_ids != expected_resource_ids
            or self._registry_scope("global") != snapshot
        ):
            raise ValueError("capacity_alert_registry_scope_incomplete")
        if len(matches) != 1:
            raise ValueError("capacity_alert_subject_unresolved")
        return matches[0]

    def deliver_next(self, *, as_of: datetime) -> str:
        batch = self._read(
            DeliverCapacityAlertEventV1.CONSUMER_KEY, None, as_of, limit=1
        )
        if not batch.events:
            return "capacity_alert_delivery_idle"
        event = batch.events[0]
        account_id = self._account_for_subject(
            event.envelope.subject_id,
            as_of=as_of,
        )
        self.deliver_one(event, account_id, as_of=as_of)
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

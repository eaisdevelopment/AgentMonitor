"""M07 typed capacity consumption through published M05/M02 ports only."""

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Protocol

from agentmonitor.contracts.alerting_v1 import (
    AlertConditionTypeV1,
    AlertSignalReceiptV1,
    AlertSubjectV1,
    EffectiveAlertRuleViewV1,
)
from agentmonitor.contracts.capacity_v1 import (
    CapacityAlertConditionQueryV1,
    CapacityAlertConditionV1,
    CapacityCommittedNoticeV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1, QueryPageV1
from agentmonitor.contracts.events_v1 import DurableEventV1
from agentmonitor.contracts.registry_v1 import (
    AccountResourceViewV1,
    AlertSubjectScopeV1,
)
from agentmonitor.modules.alerting.application.ports import (
    CapacityAlertReceiptRepositoryV1,
    PreparedCapacityAlertV1,
)
from agentmonitor.modules.alerting.domain.policy import map_capacity_alert_condition


class ResolveCapacityAlertRuleV1(Protocol):
    def __call__(
        self,
        subject: AlertSubjectV1,
        condition_type: AlertConditionTypeV1,
        *,
        as_of: datetime,
    ) -> EffectiveAlertRuleViewV1: ...


class AcknowledgeCapacityEventPortV1(Protocol):
    def __call__(
        self,
        consumer_key: str,
        event_id: OpaqueIdV1,
        payload_digest: str,
        receipt_id: OpaqueIdV1,
        as_of: datetime,
    ) -> None: ...


class ConsumeCapacityAlertEventV1:
    """Only a real current M05 fact can cause an M07 state transition."""

    def __init__(
        self,
        repository: CapacityAlertReceiptRepositoryV1,
        current_conditions: Callable[
            [CapacityAlertConditionQueryV1], QueryPageV1[CapacityAlertConditionV1]
        ],
        subject_scope: Callable[[OpaqueIdV1], AlertSubjectScopeV1 | None],
        resources: Callable[[OpaqueIdV1], tuple[AccountResourceViewV1, ...]],
        resolve_rule: ResolveCapacityAlertRuleV1,
    ) -> None:
        self._repository = repository
        self._current_conditions = current_conditions
        self._subject_scope = subject_scope
        self._resources = resources
        self._resolve_rule = resolve_rule

    def __call__(
        self,
        event: DurableEventV1[CapacityCommittedNoticeV1],
        account_id: OpaqueIdV1,
        *,
        as_of: datetime,
    ) -> AlertSignalReceiptV1:
        if (
            event.envelope.producer != "capacity"
            or event.envelope.event_type != "capacity.committed.v1"
            or event.event_schema_major != 1
            or as_of.utcoffset() != timedelta(0)
            or as_of < event.envelope.recorded_at
        ):
            raise ValueError("alert_capacity_trigger_invalid")
        replay = self._repository.lookup_capacity_event(event)
        if replay is not None:
            return replay

        def current() -> tuple[
            AlertSubjectScopeV1,
            AccountResourceViewV1,
            tuple[CapacityAlertConditionV1, ...],
        ]:
            scope = self._subject_scope(account_id)
            if scope is None or not scope.eligible:
                raise ValueError("alert_capacity_subject_unavailable")
            matches = tuple(
                resource
                for resource in self._resources(account_id)
                if resource.resource_id == event.envelope.subject_id
                and resource.account_id == account_id
                and resource.lifecycle == "active"
                and resource.registry_revision == scope.registry_revision
            )
            if len(matches) != 1:
                raise ValueError("alert_capacity_resource_unavailable")
            page = self._current_conditions(
                CapacityAlertConditionQueryV1(
                    account_id, event.envelope.subject_id, None, as_of, 100
                )
            )
            if (
                page.availability.state != "available"
                or page.has_more
                or not page.items
                or len({item.window_id for item in page.items}) != len(page.items)
                or any(
                    item.account_id != account_id
                    or item.resource_id != event.envelope.subject_id
                    or item.provider_key != scope.provider_key
                    for item in page.items
                )
            ):
                raise ValueError("alert_capacity_current_unavailable")
            return scope, matches[0], page.items

        scope, resource, facts = current()
        prepared: list[PreparedCapacityAlertV1] = []
        for fact in facts:
            subject = AlertSubjectV1(
                "resource",
                fact.resource_id,
                "quota_window",
                fact.window_id.value,
                fact.account_id,
                fact.provider_key,
                scope.organization_id,
                scope.registry_revision,
            )
            for condition in ("capacity_remaining", "capacity_exhausted"):
                effective = self._resolve_rule(subject, condition, as_of=as_of)
                if effective.registry_revision != scope.registry_revision:
                    raise ValueError("alert_capacity_rule_changed")
                prepared.append(
                    PreparedCapacityAlertV1(
                        map_capacity_alert_condition(
                            fact,
                            scope,
                            event.envelope.event_id,
                            effective.selected,
                            as_of=as_of,
                        ),
                        effective,
                    )
                )

        def recheck_current() -> None:
            if current() != (scope, resource, facts):
                raise ValueError("alert_capacity_current_changed")
            for item in prepared:
                if (
                    self._resolve_rule(
                        item.signal.subject,
                        item.signal.condition_type,
                        as_of=as_of,
                    )
                    != item.effective_rule
                ):
                    raise ValueError("alert_capacity_rule_changed")

        return self._repository.commit_capacity_event(
            event, tuple(prepared), as_of=as_of, recheck_current=recheck_current
        )


class DeliverCapacityAlertEventV1:
    """Acknowledge the producer only after M07's owned receipt commits."""

    CONSUMER_KEY = "m07-alert-capacity-v1"

    def __init__(
        self,
        consume: ConsumeCapacityAlertEventV1,
        acknowledge: AcknowledgeCapacityEventPortV1,
    ) -> None:
        self._consume = consume
        self._acknowledge = acknowledge

    def __call__(
        self,
        event: DurableEventV1[CapacityCommittedNoticeV1],
        account_id: OpaqueIdV1,
        *,
        as_of: datetime,
    ) -> AlertSignalReceiptV1:
        receipt = self._consume(event, account_id, as_of=as_of)
        self._acknowledge(
            self.CONSUMER_KEY,
            event.envelope.event_id,
            event.payload_digest,
            receipt.receipt_id,
            as_of,
        )
        return receipt

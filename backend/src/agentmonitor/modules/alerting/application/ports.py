"""M07 persistence ports: no driver/session or foreign-module repository escape."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from agentmonitor.contracts.alerting_v1 import (
    AcknowledgeAlertCommandV1,
    AlertCommandResultV1,
    AlertConditionTypeV1,
    AlertHistoryEntryV1,
    AlertHistoryQueryV1,
    AlertListQueryV1,
    AlertRuleCommandResultV1,
    AlertRuleListQueryV1,
    AlertRuleViewV1,
    AlertSignalReceiptV1,
    AlertSubjectV1,
    AlertViewV1,
    ArchiveAlertRuleCommandV1,
    CreateAlertRuleCommandV1,
    DashboardNotificationCountsV1,
    DashboardNotificationViewV1,
    EffectiveAlertRuleViewV1,
    MarkAlertReadCommandV1,
    SnoozeAlertCommandV1,
    UnsnoozeAlertCommandV1,
    UpdateAlertRuleCommandV1,
)
from agentmonitor.contracts.capacity_v1 import CapacityCommittedNoticeV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1, QueryPageV1
from agentmonitor.contracts.events_v1 import DurableEventV1
from agentmonitor.contracts.registry_v1 import RegistryScopeSnapshotV1
from agentmonitor.modules.alerting.domain.signals import NormalizedAlertSignalV1

RuleCommandV1 = (
    CreateAlertRuleCommandV1 | UpdateAlertRuleCommandV1 | ArchiveAlertRuleCommandV1
)
AlertUserCommandV1 = (
    AcknowledgeAlertCommandV1
    | SnoozeAlertCommandV1
    | UnsnoozeAlertCommandV1
    | MarkAlertReadCommandV1
)


class AlertRuleRepositoryV1(Protocol):
    def lookup_rule_command(
        self, command: RuleCommandV1
    ) -> AlertRuleCommandResultV1 | None: ...
    def create_rule(
        self, command: CreateAlertRuleCommandV1, snapshot: RegistryScopeSnapshotV1
    ) -> AlertRuleCommandResultV1: ...
    def update_rule(
        self, command: UpdateAlertRuleCommandV1, snapshot: RegistryScopeSnapshotV1
    ) -> AlertRuleCommandResultV1: ...
    def archive_rule(
        self, command: ArchiveAlertRuleCommandV1, snapshot: RegistryScopeSnapshotV1
    ) -> AlertRuleCommandResultV1: ...
    def get_rule(self, rule_id: OpaqueIdV1) -> AlertRuleViewV1 | None: ...
    def list_rules(
        self, query: AlertRuleListQueryV1
    ) -> QueryPageV1[AlertRuleViewV1]: ...
    def list_rule_candidates(
        self, subject: AlertSubjectV1, condition_type: AlertConditionTypeV1
    ) -> tuple[AlertRuleViewV1, ...]: ...


@dataclass(frozen=True, slots=True)
class PreparedCapacityAlertV1:
    signal: NormalizedAlertSignalV1
    effective_rule: EffectiveAlertRuleViewV1


class CapacityAlertReceiptRepositoryV1(Protocol):
    def lookup_capacity_event(
        self, event: DurableEventV1[CapacityCommittedNoticeV1]
    ) -> AlertSignalReceiptV1 | None: ...

    def commit_capacity_event(
        self,
        event: DurableEventV1[CapacityCommittedNoticeV1],
        prepared: tuple[PreparedCapacityAlertV1, ...],
        *,
        as_of: datetime,
        recheck_current: Callable[[], None],
    ) -> AlertSignalReceiptV1: ...


class AlertActionRepositoryV1(Protocol):
    def get_alert(self, alert_id: OpaqueIdV1) -> AlertViewV1 | None: ...

    def list_alerts(self, query: AlertListQueryV1) -> QueryPageV1[AlertViewV1]: ...

    def list_history(
        self, query: AlertHistoryQueryV1
    ) -> QueryPageV1[AlertHistoryEntryV1]: ...

    def list_notifications(
        self, query: AlertListQueryV1
    ) -> QueryPageV1[DashboardNotificationViewV1]: ...

    def notification_counts(
        self, query: AlertListQueryV1
    ) -> DashboardNotificationCountsV1: ...

    def lookup_alert_command(
        self, command: AlertUserCommandV1
    ) -> AlertCommandResultV1 | None: ...

    def apply_alert_command(
        self, command: AlertUserCommandV1
    ) -> AlertCommandResultV1: ...

"""Closed P01 rule and notification wire declarations."""

from datetime import datetime
from typing import Literal

from agentmonitor.api.v1.schemas.registry import AvailabilityV1, PageMetaV1
from agentmonitor.contracts.alerting_v1 import AlertConditionTypeV1
from pydantic import BaseModel, ConfigDict, Field


class _ClosedV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RemainingRuleConfigurationWireV1(_ClosedV1):
    schema_major: Literal[1]
    warning_remaining_basis_points: int = Field(ge=0, le=10000)
    critical_remaining_basis_points: int = Field(ge=0, le=10000)


class ConditionRuleConfigurationWireV1(_ClosedV1):
    schema_major: Literal[1]


RuleConfigurationWireV1 = (
    RemainingRuleConfigurationWireV1 | ConditionRuleConfigurationWireV1
)


class AlertScopeWireV1(_ClosedV1):
    scope_kind: Literal["global", "organization", "provider", "account"]
    scope_id: str | None


class AlertRuleInputV1(_ClosedV1):
    condition_type: AlertConditionTypeV1
    scope_kind: Literal["global", "organization", "provider", "account"]
    scope_id: str | None = Field(default=None, max_length=128)
    enabled: bool
    configuration: RuleConfigurationWireV1


class AlertRuleWireV1(_ClosedV1):
    rule_id: str | None
    condition_type: AlertConditionTypeV1
    scope: AlertScopeWireV1
    enabled: bool
    configuration: RuleConfigurationWireV1
    record_version: int
    created_at: datetime | None
    updated_at: datetime | None
    archived_at: datetime | None
    actor_id: str | None
    is_builtin: bool
    builtin_policy_version: str | None


class AlertRuleCommandWireV1(_ClosedV1):
    receipt_id: str
    rule: AlertRuleWireV1


class AlertRulePageV1(_ClosedV1):
    items: tuple[AlertRuleWireV1, ...]
    page: PageMetaV1
    availability: AvailabilityV1


class AlertWireV1(_ClosedV1):
    alert_id: str
    account_id: str | None
    organization_id: str | None
    provider_key: str | None
    subject_kind: Literal["account", "resource", "profile", "collector", "session"]
    subject_id: str
    dimension_kind: str
    dimension_id: str
    condition_type: AlertConditionTypeV1
    severity: Literal["information", "warning", "critical"]
    lifecycle: Literal["open", "recovered", "closed_by_configuration"]
    occurrence_count: int
    record_version: int
    notification_revision: int
    opened_at: datetime
    last_seen_at: datetime
    recovered_at: datetime | None
    unread: bool
    acknowledged_at: datetime | None
    snoozed_until: datetime | None
    decision_reason_code: str
    truth_state: str
    remaining_basis_points: str | None
    warning_remaining_basis_points: int | None
    critical_remaining_basis_points: int | None
    reset_at: datetime | None
    forecast_exhaustion_at: datetime | None
    source_event_id: str
    source_observed_at: datetime | None
    source_recorded_at: datetime
    source_freshness_deadline: datetime | None
    rule_scope_kind: Literal["global", "organization", "provider", "account"]
    rule_scope_id: str | None


class AlertPageV1(_ClosedV1):
    items: tuple[AlertWireV1, ...]
    page: PageMetaV1
    availability: AvailabilityV1


class AlertHistoryWireV1(_ClosedV1):
    event_id: str
    alert_id: str
    aggregate_sequence: int
    transition: str
    occurred_at: datetime
    previous_lifecycle: str | None
    current_lifecycle: str
    previous_severity: str | None
    current_severity: str
    reason_code: str
    source_event_id: str | None


class AlertHistoryPageV1(_ClosedV1):
    items: tuple[AlertHistoryWireV1, ...]
    page: PageMetaV1
    availability: AvailabilityV1


class AlertNotificationWireV1(_ClosedV1):
    alert: AlertWireV1
    rank: int
    is_visible_unread: bool


class AlertNotificationPageV1(_ClosedV1):
    items: tuple[AlertNotificationWireV1, ...]
    page: PageMetaV1
    availability: AvailabilityV1


class AlertNotificationCountsWireV1(_ClosedV1):
    active_critical: int
    active_warning: int
    visible_unread: int
    total_unread: int
    acknowledged: int
    snoozed: int
    recovered: int


class AlertCommandWireV1(_ClosedV1):
    receipt_id: str
    alert: AlertWireV1


class SnoozeAlertInputV1(_ClosedV1):
    duration_seconds: int = Field(ge=60, le=2592000)

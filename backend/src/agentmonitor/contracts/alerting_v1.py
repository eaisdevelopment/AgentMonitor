"""M07-owned immutable CTR-ALERT-001..005 V1; no I/O or provider payloads.

Capacity consumption uses the synchronized M05 current-fact and CTR-EVT-001
ports. Normalized domain decisions are not a source-of-truth integration contract.
"""

import re
from dataclasses import dataclass, fields
from datetime import datetime, timedelta
from types import UnionType
from typing import (
    ClassVar,
    Literal,
    Protocol,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from agentmonitor.contracts.capacity_v1 import CapacityCommittedNoticeV1
from agentmonitor.contracts.common_provenance_v1 import ConfidenceV1, PrecisionV1
from agentmonitor.contracts.common_quantity_v1 import CanonicalDecimalV1
from agentmonitor.contracts.common_v1 import (
    EventEnvelopeV1,
    OpaqueIdV1,
    QueryPageV1,
    TechnicalValueV1,
)
from agentmonitor.contracts.events_v1 import DurableEventV1

AlertConditionTypeV1 = Literal[
    "capacity_remaining",
    "capacity_exhausted",
    "capacity_unavailable",
    "forecasted_exhaustion",
    "authentication_attention",
    "data_stale",
    "collector_failure",
    "possible_stall",
]
AlertSeverityV1 = Literal["information", "warning", "critical"]
AlertLifecycleV1 = Literal["open", "recovered", "closed_by_configuration"]
AlertRuleScopeV1 = Literal["global", "organization", "provider", "account"]
AlertTransitionV1 = Literal[
    "opened",
    "repeated",
    "escalated",
    "deescalated",
    "recovered",
    "reopened",
    "closed_by_configuration",
    "marked_read",
    "acknowledged",
    "snoozed",
    "unsnoozed",
    "snooze_expired",
]
AlertDimensionKindV1 = Literal[
    "quota_window",
    "capacity_resource",
    "forecast",
    "monitoring_profile",
    "collector_target",
    "session",
]
AlertTruthStateV1 = Literal["current", "stale", "unknown", "unsupported", "unavailable"]
AlertReasonCodeV1 = Literal[
    "quota_remaining",
    "capacity_current",
    "capacity_exhausted",
    "capacity_unavailable",
    "forecast_before_reset",
    "authentication_required",
    "authentication_expiring",
    "authentication_healthy",
    "collector_stale",
    "collector_failure",
    "collector_healthy",
    "possible_stall",
    "runtime_progress",
    "runtime_waiting",
    "source_not_evaluable",
    "source_recovery",
    "window_reset",
    "rule_disabled",
    "subject_ineligible",
    "acknowledged",
    "marked_read",
    "snoozed",
    "unsnoozed",
    "snooze_expired",
    "severity_changed",
    "condition_repeated",
    "condition_opened",
    "condition_reopened",
    "configuration_changed",
    "capacity_ratio_current",
    "capacity_used_percent_current",
    "capacity_reading_stale",
    "capacity_reading_conflicted",
    "capacity_reading_partial",
    "capacity_freshness_unknown",
    "capacity_ratio_unsupported",
    "capacity_ratio_unavailable",
    "capacity_ratio_unknown",
    "capacity_nonconstraining",
]
_TOKEN = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")


class InvalidAlertContractV1(ValueError):
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-002"
    OWNER: ClassVar[str] = "PLAN-M07"
    """Bounded safe validation code; never includes submitted values."""


def _valid_type(annotation: object, value: object) -> bool:
    origin = get_origin(annotation)
    arguments = get_args(annotation)
    if origin is Literal:
        return any(type(value) is type(item) and value == item for item in arguments)
    if origin in (UnionType, Union):
        return any(_valid_type(item, value) for item in arguments)
    if origin is tuple:
        return (
            isinstance(value, tuple)
            and len(value) <= 200
            and all(_valid_type(arguments[0], item) for item in value)
        )
    if annotation is type(None):
        return value is None
    if annotation in (int, bool, str):
        return type(value) is annotation
    if isinstance(annotation, type):
        return isinstance(value, annotation)
    return False


def _token(value: str) -> bool:
    return _TOKEN.fullmatch(value) is not None


def _positive(value: int) -> None:
    if type(value) is not int or value < 1:
        raise InvalidAlertContractV1("alert_positive_version_required")


@dataclass(frozen=True, slots=True)
class AlertValueV1(TechnicalValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        annotations = get_type_hints(type(self))
        for item in fields(self):
            value = getattr(self, item.name)
            if not _valid_type(annotations[item.name], value):
                raise InvalidAlertContractV1("alert_field_type_invalid")
            if isinstance(value, str) and not _token(value):
                raise InvalidAlertContractV1("alert_safe_token_required")
            if isinstance(value, OpaqueIdV1) and not _token(value.value):
                raise InvalidAlertContractV1("alert_opaque_id_invalid")


@dataclass(frozen=True, slots=True)
class AlertScopeRefV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-001"
    scope_kind: AlertRuleScopeV1
    scope_id: str | None

    def __post_init__(self) -> None:
        AlertValueV1.__post_init__(self)
        if (self.scope_kind == "global") != (self.scope_id is None):
            raise InvalidAlertContractV1("alert_scope_invalid")
        if self.scope_kind != "global" and self.scope_id == "global":
            raise InvalidAlertContractV1("alert_scope_invalid")


@dataclass(frozen=True, slots=True)
class CapacityRemainingRuleConfigurationV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-001"
    schema_major: Literal[1]
    warning_remaining_basis_points: int
    critical_remaining_basis_points: int

    def __post_init__(self) -> None:
        AlertValueV1.__post_init__(self)
        if (
            not 0
            <= self.critical_remaining_basis_points
            <= self.warning_remaining_basis_points
            <= 10000
        ):
            raise InvalidAlertContractV1("alert_thresholds_invalid")


@dataclass(frozen=True, slots=True)
class ConditionRuleConfigurationV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-001"
    schema_major: Literal[1]


AlertRuleConfigurationV1 = (
    CapacityRemainingRuleConfigurationV1 | ConditionRuleConfigurationV1
)


def _configuration_matches(
    condition: AlertConditionTypeV1, configuration: AlertRuleConfigurationV1
) -> None:
    if (condition == "capacity_remaining") != isinstance(
        configuration, CapacityRemainingRuleConfigurationV1
    ):
        raise InvalidAlertContractV1("alert_rule_configuration_mismatch")


@dataclass(frozen=True, slots=True)
class AlertRuleViewV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-001"
    rule_id: OpaqueIdV1 | None
    condition_type: AlertConditionTypeV1
    scope: AlertScopeRefV1
    enabled: bool
    configuration: AlertRuleConfigurationV1
    record_version: int
    created_at: datetime | None
    updated_at: datetime | None
    archived_at: datetime | None
    actor_id: OpaqueIdV1 | None
    is_builtin: bool
    builtin_policy_version: str | None

    def __post_init__(self) -> None:
        AlertValueV1.__post_init__(self)
        _configuration_matches(self.condition_type, self.configuration)
        if self.is_builtin:
            if (
                self.rule_id is not None
                or self.record_version != 0
                or self.builtin_policy_version is None
                or any(
                    item is not None
                    for item in (
                        self.created_at,
                        self.updated_at,
                        self.archived_at,
                        self.actor_id,
                    )
                )
                or self.scope.scope_kind != "global"
            ):
                raise InvalidAlertContractV1("alert_builtin_rule_invalid")
        else:
            _positive(self.record_version)
            if (
                self.rule_id is None
                or self.actor_id is None
                or self.created_at is None
                or self.updated_at is None
                or self.builtin_policy_version is not None
            ):
                raise InvalidAlertContractV1("alert_persisted_rule_invalid")
            if self.updated_at < self.created_at or (
                self.archived_at is not None and self.archived_at != self.updated_at
            ):
                raise InvalidAlertContractV1("alert_rule_time_invalid")


@dataclass(frozen=True, slots=True)
class EffectiveAlertRuleViewV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-001"
    selected: AlertRuleViewV1
    candidates: tuple[AlertRuleViewV1, ...]
    registry_revision: int
    explanation_code: Literal[
        "account_override",
        "provider_override",
        "organization_override",
        "global_override",
        "builtin_default",
    ]

    def __post_init__(self) -> None:
        AlertValueV1.__post_init__(self)
        if (
            not 1 <= len(self.candidates) <= 5
            or self.selected != self.candidates[0]
            or self.registry_revision < 0
        ):
            raise InvalidAlertContractV1("alert_rule_resolution_invalid")


@dataclass(frozen=True, slots=True)
class AlertSubjectV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-002"
    subject_kind: Literal["account", "resource", "profile", "collector", "session"]
    subject_id: OpaqueIdV1
    dimension_kind: AlertDimensionKindV1
    dimension_id: str
    account_id: OpaqueIdV1 | None
    provider_key: str | None
    organization_id: OpaqueIdV1 | None
    registry_revision: int

    def __post_init__(self) -> None:
        AlertValueV1.__post_init__(self)
        if self.registry_revision < 0 or (
            self.account_id is None and self.organization_id is not None
        ):
            raise InvalidAlertContractV1("alert_subject_scope_invalid")
        if self.subject_kind == "account" and self.account_id != self.subject_id:
            raise InvalidAlertContractV1("alert_subject_account_invalid")


@dataclass(frozen=True, slots=True)
class AlertSourceReferenceV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-002"
    producer_key: Literal[
        "registry", "collection_control", "capacity", "runtime_observation"
    ]
    condition_stream_key: str
    source_generation: int
    event_id: OpaqueIdV1
    observation_ids: tuple[OpaqueIdV1, ...]
    evidence_ids: tuple[OpaqueIdV1, ...]
    observed_at: datetime | None
    recorded_at: datetime
    freshness_deadline: datetime | None
    precision: PrecisionV1
    confidence: ConfidenceV1
    reason_code: AlertReasonCodeV1

    def __post_init__(self) -> None:
        AlertValueV1.__post_init__(self)
        _positive(self.source_generation)
        if (
            len(self.observation_ids) > 64
            or len(self.evidence_ids) > 64
            or len(set(self.observation_ids)) != len(self.observation_ids)
            or len(set(self.evidence_ids)) != len(self.evidence_ids)
        ):
            raise InvalidAlertContractV1("alert_source_references_invalid")
        if self.observed_at is not None and self.recorded_at < self.observed_at:
            raise InvalidAlertContractV1("alert_source_time_invalid")
        if self.freshness_deadline is not None and (
            self.observed_at is None or self.freshness_deadline < self.observed_at
        ):
            raise InvalidAlertContractV1("alert_source_freshness_invalid")
        if any(
            not _token(item.value) for item in self.observation_ids + self.evidence_ids
        ):
            raise InvalidAlertContractV1("alert_source_references_invalid")


@dataclass(frozen=True, slots=True)
class AlertDecisionSummaryV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-002"
    reason_code: AlertReasonCodeV1
    truth_state: AlertTruthStateV1
    remaining_basis_points: CanonicalDecimalV1 | None
    warning_remaining_basis_points: int | None
    critical_remaining_basis_points: int | None
    reset_at: datetime | None
    forecast_exhaustion_at: datetime | None
    source: AlertSourceReferenceV1

    def __post_init__(self) -> None:
        AlertValueV1.__post_init__(self)
        if (
            self.remaining_basis_points is not None
            and not 0 <= self.remaining_basis_points.as_decimal() <= 10000
        ):
            raise InvalidAlertContractV1("alert_remaining_out_of_range")
        if (self.warning_remaining_basis_points is None) != (
            self.critical_remaining_basis_points is None
        ):
            raise InvalidAlertContractV1("alert_decision_thresholds_invalid")
        if (
            self.warning_remaining_basis_points is not None
            and self.critical_remaining_basis_points is not None
        ):
            CapacityRemainingRuleConfigurationV1(
                1,
                self.warning_remaining_basis_points,
                self.critical_remaining_basis_points,
            )
        if (
            self.truth_state in ("unknown", "unsupported", "unavailable")
            and self.remaining_basis_points is not None
        ):
            raise InvalidAlertContractV1("alert_decision_value_unavailable")


@dataclass(frozen=True, slots=True)
class AlertViewV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-002"
    alert_id: OpaqueIdV1
    fingerprint_version: Literal[1]
    condition_type: AlertConditionTypeV1
    subject: AlertSubjectV1
    severity: AlertSeverityV1
    lifecycle: AlertLifecycleV1
    occurrence_generation: int
    occurrence_count: int
    record_version: int
    opened_at: datetime
    last_seen_at: datetime
    recovered_at: datetime | None
    closed_at: datetime | None
    latest_notification_at: datetime
    notification_revision: int
    unread: bool
    acknowledged_at: datetime | None
    acknowledged_by: OpaqueIdV1 | None
    snoozed_until: datetime | None
    rule: AlertRuleViewV1
    decision: AlertDecisionSummaryV1
    aggregate_sequence: int

    def __post_init__(self) -> None:
        AlertValueV1.__post_init__(self)
        for value in (
            self.occurrence_generation,
            self.occurrence_count,
            self.record_version,
            self.notification_revision,
            self.aggregate_sequence,
        ):
            _positive(value)
        if self.rule.condition_type != self.condition_type or (
            self.acknowledged_at is None
        ) != (self.acknowledged_by is None):
            raise InvalidAlertContractV1("alert_projection_invalid")
        if (
            self.last_seen_at < self.opened_at
            or self.latest_notification_at < self.opened_at
        ):
            raise InvalidAlertContractV1("alert_projection_time_invalid")
        if self.lifecycle == "open":
            if (
                self.recovered_at is not None
                or self.closed_at is not None
                or self.severity == "information"
            ):
                raise InvalidAlertContractV1("alert_open_projection_invalid")
        elif (
            self.snoozed_until is not None
            or ((self.lifecycle == "recovered") != (self.recovered_at is not None))
            or (
                (self.lifecycle == "closed_by_configuration")
                != (self.closed_at is not None)
            )
        ):
            raise InvalidAlertContractV1("alert_terminal_projection_invalid")
        for timestamp in (self.recovered_at, self.closed_at, self.acknowledged_at):
            if timestamp is not None and timestamp < self.opened_at:
                raise InvalidAlertContractV1("alert_projection_time_invalid")


@dataclass(frozen=True, slots=True)
class AlertHistoryEntryV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-004"
    event_id: OpaqueIdV1
    alert_id: OpaqueIdV1
    aggregate_sequence: int
    transition: AlertTransitionV1
    occurred_at: datetime
    previous_lifecycle: AlertLifecycleV1 | None
    current_lifecycle: AlertLifecycleV1
    previous_severity: AlertSeverityV1 | None
    current_severity: AlertSeverityV1
    actor_id: OpaqueIdV1 | None
    reason_code: AlertReasonCodeV1
    source_event_id: OpaqueIdV1 | None
    command_id: OpaqueIdV1 | None

    def __post_init__(self) -> None:
        AlertValueV1.__post_init__(self)
        _positive(self.aggregate_sequence)
        if (self.previous_lifecycle is None) != (self.previous_severity is None):
            raise InvalidAlertContractV1("alert_history_prior_invalid")
        if self.transition == "opened" and self.previous_lifecycle is not None:
            raise InvalidAlertContractV1("alert_history_open_invalid")


@dataclass(frozen=True, slots=True)
class AlertOpenedV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-003"
    envelope: EventEnvelopeV1
    alert: AlertViewV1
    aggregate_sequence: int

    def __post_init__(self) -> None:
        AlertValueV1.__post_init__(self)
        if (
            self.alert.lifecycle != "open"
            or self.alert.occurrence_generation != 1
            or self.aggregate_sequence != self.alert.aggregate_sequence
            or self.envelope.subject_id != self.alert.alert_id
        ):
            raise InvalidAlertContractV1("alert_opened_event_invalid")


@dataclass(frozen=True, slots=True)
class AlertStateChangedV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-004"
    envelope: EventEnvelopeV1
    history: AlertHistoryEntryV1
    alert: AlertViewV1

    def __post_init__(self) -> None:
        AlertValueV1.__post_init__(self)
        if (
            self.history.alert_id != self.alert.alert_id
            or self.history.aggregate_sequence != self.alert.aggregate_sequence
            or self.history.event_id != self.envelope.event_id
            or self.envelope.subject_id != self.alert.alert_id
            or self.history.current_lifecycle != self.alert.lifecycle
            or self.history.current_severity != self.alert.severity
        ):
            raise InvalidAlertContractV1("alert_changed_event_invalid")


@dataclass(frozen=True, slots=True)
class DashboardNotificationViewV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-005"
    alert: AlertViewV1
    rank: int
    is_visible_unread: bool

    def __post_init__(self) -> None:
        AlertValueV1.__post_init__(self)
        if not 0 <= self.rank <= 3 or (
            self.is_visible_unread and not self.alert.unread
        ):
            raise InvalidAlertContractV1("alert_notification_invalid")


@dataclass(frozen=True, slots=True)
class DashboardNotificationCountsV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-005"
    active_critical: int
    active_warning: int
    visible_unread: int
    total_unread: int
    acknowledged: int
    snoozed: int
    recovered: int

    def __post_init__(self) -> None:
        AlertValueV1.__post_init__(self)
        if (
            any(getattr(self, item.name) < 0 for item in fields(self))
            or self.visible_unread > self.total_unread
        ):
            raise InvalidAlertContractV1("alert_notification_counts_invalid")


@dataclass(frozen=True, slots=True)
class CreateAlertRuleCommandV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-001"
    command_id: OpaqueIdV1
    actor_id: OpaqueIdV1
    condition_type: AlertConditionTypeV1
    scope: AlertScopeRefV1
    enabled: bool
    configuration: AlertRuleConfigurationV1
    as_of: datetime

    def __post_init__(self) -> None:
        AlertValueV1.__post_init__(self)
        _configuration_matches(self.condition_type, self.configuration)


@dataclass(frozen=True, slots=True)
class UpdateAlertRuleCommandV1(CreateAlertRuleCommandV1):
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-001"
    OWNER: ClassVar[str] = "PLAN-M07"
    rule_id: OpaqueIdV1
    expected_record_version: int

    def __post_init__(self) -> None:
        CreateAlertRuleCommandV1.__post_init__(self)
        _positive(self.expected_record_version)


@dataclass(frozen=True, slots=True)
class ArchiveAlertRuleCommandV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-001"
    command_id: OpaqueIdV1
    actor_id: OpaqueIdV1
    rule_id: OpaqueIdV1
    expected_record_version: int
    as_of: datetime

    def __post_init__(self) -> None:
        AlertValueV1.__post_init__(self)
        _positive(self.expected_record_version)


@dataclass(frozen=True, slots=True)
class AlertRuleCommandResultV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-001"
    receipt_id: OpaqueIdV1
    rule: AlertRuleViewV1


@dataclass(frozen=True, slots=True)
class AlertRuleListQueryV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-001"
    as_of: datetime
    condition_type: AlertConditionTypeV1 | None = None
    scope: AlertScopeRefV1 | None = None
    include_archived: bool = False
    limit: int = 50
    after_key: str | None = None

    def __post_init__(self) -> None:
        AlertValueV1.__post_init__(self)
        if not 1 <= self.limit <= 200:
            raise InvalidAlertContractV1("alert_page_limit_invalid")


@dataclass(frozen=True, slots=True)
class AcknowledgeAlertCommandV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-002"
    command_id: OpaqueIdV1
    actor_id: OpaqueIdV1
    alert_id: OpaqueIdV1
    expected_record_version: int
    as_of: datetime

    def __post_init__(self) -> None:
        AlertValueV1.__post_init__(self)
        _positive(self.expected_record_version)


@dataclass(frozen=True, slots=True)
class SnoozeAlertCommandV1(AcknowledgeAlertCommandV1):
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-002"
    OWNER: ClassVar[str] = "PLAN-M07"
    duration_seconds: int

    def __post_init__(self) -> None:
        AcknowledgeAlertCommandV1.__post_init__(self)
        if not 60 <= self.duration_seconds <= 2592000:
            raise InvalidAlertContractV1("alert_snooze_duration_invalid")


@dataclass(frozen=True, slots=True)
class UnsnoozeAlertCommandV1(AcknowledgeAlertCommandV1):
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-002"
    OWNER: ClassVar[str] = "PLAN-M07"
    pass


@dataclass(frozen=True, slots=True)
class MarkAlertReadCommandV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-005"
    command_id: OpaqueIdV1
    actor_id: OpaqueIdV1
    alert_id: OpaqueIdV1
    expected_notification_revision: int
    as_of: datetime

    def __post_init__(self) -> None:
        AlertValueV1.__post_init__(self)
        _positive(self.expected_notification_revision)


@dataclass(frozen=True, slots=True)
class AlertCommandResultV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-002"
    receipt_id: OpaqueIdV1
    alert: AlertViewV1


@dataclass(frozen=True, slots=True)
class AlertListQueryV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-002"
    as_of: datetime
    condition_type: AlertConditionTypeV1 | None = None
    scope: AlertScopeRefV1 | None = None
    lifecycle: AlertLifecycleV1 | None = None
    severity: AlertSeverityV1 | None = None
    unread: bool | None = None
    snoozed: bool | None = None
    range_start: datetime | None = None
    range_before: datetime | None = None
    limit: int = 50
    after_key: str | None = None

    def __post_init__(self) -> None:
        AlertValueV1.__post_init__(self)
        if not 1 <= self.limit <= 200 or (self.range_start is None) != (
            self.range_before is None
        ):
            raise InvalidAlertContractV1("alert_query_invalid")
        if (
            self.range_start is not None
            and self.range_before is not None
            and not timedelta(0)
            < self.range_before - self.range_start
            <= timedelta(days=365)
        ):
            raise InvalidAlertContractV1("alert_query_range_invalid")


@dataclass(frozen=True, slots=True)
class AlertHistoryQueryV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-002"
    alert_id: OpaqueIdV1
    as_of: datetime
    limit: int = 50
    after_key: str | None = None

    def __post_init__(self) -> None:
        AlertValueV1.__post_init__(self)
        if not 1 <= self.limit <= 200:
            raise InvalidAlertContractV1("alert_page_limit_invalid")


@dataclass(frozen=True, slots=True)
class AlertSignalReceiptV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-002"
    receipt_id: OpaqueIdV1
    event_id: OpaqueIdV1
    disposition: Literal[
        "applied", "duplicate", "stale_ignored", "not_evaluable", "rejected"
    ]
    alert_ids: tuple[OpaqueIdV1, ...]
    source_generation: int
    processed_at: datetime

    def __post_init__(self) -> None:
        AlertValueV1.__post_init__(self)
        _positive(self.source_generation)


@dataclass(frozen=True, slots=True)
class AlertRetentionResultV1(AlertValueV1):
    OWNER: ClassVar[str] = "PLAN-M07"
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-002"
    job_id: OpaqueIdV1
    cutoff_at: datetime
    examined_count: int
    deleted_alert_count: int
    deleted_history_count: int
    has_more: bool
    completed_at: datetime

    def __post_init__(self) -> None:
        AlertValueV1.__post_init__(self)
        if (
            any(
                value < 0
                for value in (
                    self.examined_count,
                    self.deleted_alert_count,
                    self.deleted_history_count,
                )
            )
            or self.cutoff_at >= self.completed_at
        ):
            raise InvalidAlertContractV1("alert_retention_result_invalid")


class CreateAlertRuleV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-001"
    OWNER: ClassVar[str] = "PLAN-M07"

    def __call__(
        self, command: CreateAlertRuleCommandV1
    ) -> AlertRuleCommandResultV1: ...


class UpdateAlertRuleV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-001"
    OWNER: ClassVar[str] = "PLAN-M07"

    def __call__(
        self, command: UpdateAlertRuleCommandV1
    ) -> AlertRuleCommandResultV1: ...


class ArchiveAlertRuleOverrideV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-001"
    OWNER: ClassVar[str] = "PLAN-M07"

    def __call__(
        self, command: ArchiveAlertRuleCommandV1
    ) -> AlertRuleCommandResultV1: ...


class GetAlertRuleV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-001"
    OWNER: ClassVar[str] = "PLAN-M07"

    def __call__(self, rule_id: OpaqueIdV1) -> AlertRuleViewV1 | None: ...


class ListAlertRulesV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-001"
    OWNER: ClassVar[str] = "PLAN-M07"

    def __call__(self, query: AlertRuleListQueryV1) -> QueryPageV1[AlertRuleViewV1]: ...


class ResolveEffectiveAlertRuleV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-001"
    OWNER: ClassVar[str] = "PLAN-M07"

    def __call__(
        self,
        subject: AlertSubjectV1,
        condition_type: AlertConditionTypeV1,
        *,
        as_of: datetime,
    ) -> EffectiveAlertRuleViewV1: ...


class GetAlertV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-002"
    OWNER: ClassVar[str] = "PLAN-M07"

    def __call__(
        self, alert_id: OpaqueIdV1, *, as_of: datetime
    ) -> AlertViewV1 | None: ...


class ListAlertsV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-002"
    OWNER: ClassVar[str] = "PLAN-M07"

    def __call__(self, query: AlertListQueryV1) -> QueryPageV1[AlertViewV1]: ...


class ListAlertHistoryV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-002"
    OWNER: ClassVar[str] = "PLAN-M07"

    def __call__(
        self, query: AlertHistoryQueryV1
    ) -> QueryPageV1[AlertHistoryEntryV1]: ...


class AcknowledgeAlertV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-002"
    OWNER: ClassVar[str] = "PLAN-M07"

    def __call__(self, command: AcknowledgeAlertCommandV1) -> AlertCommandResultV1: ...


class SnoozeAlertV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-002"
    OWNER: ClassVar[str] = "PLAN-M07"

    def __call__(self, command: SnoozeAlertCommandV1) -> AlertCommandResultV1: ...


class UnsnoozeAlertV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-002"
    OWNER: ClassVar[str] = "PLAN-M07"

    def __call__(self, command: UnsnoozeAlertCommandV1) -> AlertCommandResultV1: ...


class MarkAlertReadV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-005"
    OWNER: ClassVar[str] = "PLAN-M07"

    def __call__(self, command: MarkAlertReadCommandV1) -> AlertCommandResultV1: ...


class ListDashboardNotificationsV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-005"
    OWNER: ClassVar[str] = "PLAN-M07"

    def __call__(
        self, query: AlertListQueryV1
    ) -> QueryPageV1[DashboardNotificationViewV1]: ...


class GetDashboardNotificationCountsV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-005"
    OWNER: ClassVar[str] = "PLAN-M07"

    def __call__(self, query: AlertListQueryV1) -> DashboardNotificationCountsV1: ...


class ConsumeCapacityAlertEventV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-ALERT-002"
    OWNER: ClassVar[str] = "PLAN-M07"

    def __call__(
        self,
        event: DurableEventV1[CapacityCommittedNoticeV1],
        account_id: OpaqueIdV1,
        *,
        as_of: datetime,
    ) -> AlertSignalReceiptV1: ...

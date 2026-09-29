"""Pure lifecycle reducer. Normalized signals establish no real producer truth."""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Literal, TypedDict, Unpack

from agentmonitor.contracts.alerting_v1 import (
    AcknowledgeAlertCommandV1,
    AlertDecisionSummaryV1,
    AlertLifecycleV1,
    AlertRuleViewV1,
    AlertSeverityV1,
    AlertSubjectV1,
    AlertTransitionV1,
    AlertViewV1,
    CapacityRemainingRuleConfigurationV1,
    MarkAlertReadCommandV1,
    SnoozeAlertCommandV1,
    UnsnoozeAlertCommandV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.alerting.domain.fingerprint import fingerprint_alert_condition
from agentmonitor.modules.alerting.domain.policy import capacity_remaining_severity
from agentmonitor.modules.alerting.domain.signals import (
    NormalizedAlertSignalV1 as NormalizedAlertSignalV1,
)


@dataclass(frozen=True, slots=True)
class AlertTransitionDecisionV1:
    alert: AlertViewV1 | None
    transition: AlertTransitionV1 | None
    disposition: Literal["applied", "duplicate", "stale_ignored", "not_evaluable"]


def _clock(as_of: datetime, minimum: datetime) -> None:
    if (
        not isinstance(as_of, datetime)
        or as_of.utcoffset() != timedelta(0)
        or as_of < minimum
    ):
        raise ValueError("alert_transition_time_invalid")


class _AlertChanges(TypedDict, total=False):
    subject: AlertSubjectV1
    severity: AlertSeverityV1
    lifecycle: AlertLifecycleV1
    occurrence_generation: int
    occurrence_count: int
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


def _updated(
    alert: AlertViewV1, transition: AlertTransitionV1, **changes: Unpack[_AlertChanges]
) -> AlertTransitionDecisionV1:
    # Closed replace sites own field names/values; no external payload mapping.
    result = replace(
        alert,
        record_version=alert.record_version + 1,
        aggregate_sequence=alert.aggregate_sequence + 1,
        **changes,
    )
    return AlertTransitionDecisionV1(result, transition, "applied")


def reduce_alert_signal(
    existing: AlertViewV1 | None,
    signal: NormalizedAlertSignalV1,
    rule: AlertRuleViewV1,
    alert_id: OpaqueIdV1,
    as_of: datetime,
    *,
    greatest_source_generation: int | None = None,
) -> AlertTransitionDecisionV1:
    _clock(as_of, signal.decision.source.recorded_at)
    if rule.condition_type != signal.condition_type:
        raise ValueError("alert_signal_rule_conflict")
    source = signal.decision.source
    prior_generation = greatest_source_generation or 0
    if existing is not None:
        _clock(as_of, existing.last_seen_at)
        if existing.alert_id != alert_id or fingerprint_alert_condition(
            existing.condition_type, existing.subject, 1
        ) != fingerprint_alert_condition(
            signal.condition_type, signal.subject, signal.condition_semantic_major
        ):
            raise ValueError("alert_signal_subject_conflict")
        prior = existing.decision.source
        if (prior.producer_key, prior.condition_stream_key) != (
            source.producer_key,
            source.condition_stream_key,
        ):
            raise ValueError("alert_signal_stream_conflict")
        if prior.event_id == source.event_id:
            if existing.decision != signal.decision:
                raise ValueError("alert_event_conflict")
            return AlertTransitionDecisionV1(existing, None, "duplicate")
        prior_generation = max(prior_generation, prior.source_generation)
    if source.source_generation <= prior_generation:
        return AlertTransitionDecisionV1(existing, None, "stale_ignored")
    if not rule.enabled:
        if existing is None or existing.lifecycle == "closed_by_configuration":
            return AlertTransitionDecisionV1(existing, None, "not_evaluable")
        return _updated(
            existing,
            "closed_by_configuration",
            lifecycle="closed_by_configuration",
            recovered_at=None,
            closed_at=as_of,
            snoozed_until=None,
            rule=rule,
            decision=signal.decision,
            unread=False,
            last_seen_at=as_of,
        )
    if signal.transition == "not_evaluable" or signal.decision.truth_state in (
        "unknown",
        "unsupported",
    ):
        return AlertTransitionDecisionV1(existing, None, "not_evaluable")
    if signal.condition_type == "capacity_remaining":
        if (
            signal.decision.truth_state != "current"
            or signal.decision.remaining_basis_points is None
        ):
            return AlertTransitionDecisionV1(existing, None, "not_evaluable")
        expected = capacity_remaining_severity(signal.decision, rule)
        if signal.transition == "recovered" and expected is not None:
            raise ValueError("alert_recovery_not_proven")
        if signal.transition == "active" and signal.severity != expected:
            raise ValueError("alert_active_decision_conflict")
    if signal.transition == "recovered":
        if signal.decision.truth_state != "current":
            return AlertTransitionDecisionV1(existing, None, "not_evaluable")
        if existing is None or existing.lifecycle != "open":
            return AlertTransitionDecisionV1(existing, None, "not_evaluable")
        return _updated(
            existing,
            "recovered",
            lifecycle="recovered",
            severity="information",
            recovered_at=as_of,
            closed_at=None,
            last_seen_at=as_of,
            latest_notification_at=as_of,
            notification_revision=existing.notification_revision + 1,
            unread=True,
            snoozed_until=None,
            rule=rule,
            decision=signal.decision,
        )
    if signal.decision.truth_state == "stale" and signal.condition_type != "data_stale":
        return AlertTransitionDecisionV1(existing, None, "not_evaluable")
    if signal.decision.truth_state == "unavailable" and signal.condition_type not in (
        "capacity_unavailable",
        "collector_failure",
    ):
        return AlertTransitionDecisionV1(existing, None, "not_evaluable")
    if signal.severity not in ("warning", "critical"):
        raise ValueError("alert_active_severity_required")
    decision = signal.decision
    if isinstance(rule.configuration, CapacityRemainingRuleConfigurationV1):
        decision = replace(
            decision,
            warning_remaining_basis_points=rule.configuration.warning_remaining_basis_points,
            critical_remaining_basis_points=rule.configuration.critical_remaining_basis_points,
        )
    if existing is None:
        result = AlertViewV1(
            alert_id,
            1,
            signal.condition_type,
            signal.subject,
            signal.severity,
            "open",
            1,
            1,
            1,
            as_of,
            as_of,
            None,
            None,
            as_of,
            1,
            True,
            None,
            None,
            None,
            rule,
            decision,
            1,
        )
        return AlertTransitionDecisionV1(result, "opened", "applied")
    if existing.lifecycle != "open":
        return _updated(
            existing,
            "reopened",
            lifecycle="open",
            severity=signal.severity,
            subject=signal.subject,
            occurrence_generation=existing.occurrence_generation + 1,
            occurrence_count=1,
            opened_at=as_of,
            last_seen_at=as_of,
            recovered_at=None,
            closed_at=None,
            latest_notification_at=as_of,
            notification_revision=existing.notification_revision + 1,
            unread=True,
            acknowledged_at=None,
            acknowledged_by=None,
            snoozed_until=None,
            rule=rule,
            decision=decision,
        )
    changes: _AlertChanges = {
        "subject": signal.subject,
        "last_seen_at": as_of,
        "occurrence_count": existing.occurrence_count + 1,
        "rule": rule,
        "decision": decision,
    }
    if signal.severity == existing.severity:
        return _updated(existing, "repeated", **changes)
    transition: AlertTransitionV1 = (
        "escalated" if signal.severity == "critical" else "deescalated"
    )
    changes.update(
        {
            "severity": signal.severity,
            "unread": True,
            "latest_notification_at": as_of,
            "notification_revision": existing.notification_revision + 1,
        }
    )
    if transition == "escalated":
        changes.update(
            {"acknowledged_at": None, "acknowledged_by": None, "snoozed_until": None}
        )
    return _updated(existing, transition, **changes)


def _command(alert: AlertViewV1, command: AcknowledgeAlertCommandV1) -> None:
    if alert.alert_id != command.alert_id:
        raise ValueError("alert_command_subject_conflict")
    if alert.record_version != command.expected_record_version:
        raise ValueError("alert_version_conflict")
    if alert.lifecycle != "open":
        raise ValueError("alert_not_open")
    _clock(command.as_of, alert.last_seen_at)


def acknowledge_alert(
    alert: AlertViewV1, command: AcknowledgeAlertCommandV1
) -> AlertTransitionDecisionV1:
    _command(alert, command)
    if alert.acknowledged_at is not None and not alert.unread:
        return AlertTransitionDecisionV1(alert, None, "duplicate")
    return _updated(
        alert,
        "acknowledged",
        acknowledged_at=command.as_of,
        acknowledged_by=command.actor_id,
        unread=False,
    )


def mark_alert_read(
    alert: AlertViewV1, command: MarkAlertReadCommandV1
) -> AlertTransitionDecisionV1:
    if alert.alert_id != command.alert_id:
        raise ValueError("alert_command_subject_conflict")
    if alert.notification_revision != command.expected_notification_revision:
        raise ValueError("alert_notification_conflict")
    _clock(command.as_of, alert.last_seen_at)
    if not alert.unread:
        return AlertTransitionDecisionV1(alert, None, "duplicate")
    return _updated(alert, "marked_read", unread=False)


def snooze_alert(
    alert: AlertViewV1, command: SnoozeAlertCommandV1
) -> AlertTransitionDecisionV1:
    _command(alert, command)
    return _updated(
        alert,
        "snoozed",
        snoozed_until=command.as_of + timedelta(seconds=command.duration_seconds),
        unread=False,
    )


def unsnooze_alert(
    alert: AlertViewV1, command: UnsnoozeAlertCommandV1
) -> AlertTransitionDecisionV1:
    _command(alert, command)
    if alert.snoozed_until is None:
        return AlertTransitionDecisionV1(alert, None, "duplicate")
    return _updated(
        alert,
        "unsnoozed",
        snoozed_until=None,
        unread=True,
        latest_notification_at=command.as_of,
        notification_revision=alert.notification_revision + 1,
    )


def expire_snooze(
    alert: AlertViewV1,
    expected_generation: int,
    current_generation: int,
    as_of: datetime,
) -> AlertTransitionDecisionV1:
    _clock(as_of, alert.last_seen_at)
    if (
        type(expected_generation) is not int
        or type(current_generation) is not int
        or expected_generation < 1
        or current_generation < 1
    ):
        raise ValueError("alert_deadline_generation_invalid")
    if (
        expected_generation != current_generation
        or alert.lifecycle != "open"
        or alert.snoozed_until is None
        or alert.snoozed_until > as_of
    ):
        return AlertTransitionDecisionV1(alert, None, "duplicate")
    return _updated(
        alert,
        "snooze_expired",
        snoozed_until=None,
        unread=True,
        latest_notification_at=as_of,
        notification_revision=alert.notification_revision + 1,
    )

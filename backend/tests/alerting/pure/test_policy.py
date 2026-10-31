"""A-P01..06: constructed domain values only; no I/O or provider claims."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

import pytest
from agentmonitor.contracts.alerting_v1 import (
    AcknowledgeAlertCommandV1,
    AlertDecisionSummaryV1,
    AlertRuleScopeV1,
    AlertRuleViewV1,
    AlertScopeRefV1,
    AlertSeverityV1,
    AlertSourceReferenceV1,
    AlertSubjectV1,
    AlertTruthStateV1,
    AlertViewV1,
    CapacityRemainingRuleConfigurationV1,
    MarkAlertReadCommandV1,
    SnoozeAlertCommandV1,
    UnsnoozeAlertCommandV1,
)
from agentmonitor.contracts.common_quantity_v1 import CanonicalDecimalV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.alerting.domain.fingerprint import fingerprint_alert_condition
from agentmonitor.modules.alerting.domain.lifecycle import (
    NormalizedAlertSignalV1,
    acknowledge_alert,
    expire_snooze,
    mark_alert_read,
    reduce_alert_signal,
    snooze_alert,
    unsnooze_alert,
)
from agentmonitor.modules.alerting.domain.notifications import (
    notification_counts,
    ordered_notifications,
)
from agentmonitor.modules.alerting.domain.policy import (
    builtin_rule,
    capacity_remaining_severity,
    resolve_effective_rule,
)
from agentmonitor.modules.alerting.domain.retention import (
    retention_cutoff,
    terminal_alert_is_expired,
)

NOW = datetime(2026, 9, 29, 12, tzinfo=UTC)
SUBJECT = AlertSubjectV1(
    "resource",
    OpaqueIdV1("resource"),
    "quota_window",
    "window",
    OpaqueIdV1("account"),
    "claude",
    OpaqueIdV1("organization"),
    4,
)


def rule(
    kind: AlertRuleScopeV1,
    *,
    enabled: bool = True,
    warning: int = 3000,
    critical: int = 1500,
) -> AlertRuleViewV1:
    value = {
        "account": "account",
        "provider": "claude",
        "organization": "organization",
        "global": None,
    }[kind]
    return AlertRuleViewV1(
        OpaqueIdV1(f"rule-{kind}"),
        "capacity_remaining",
        AlertScopeRefV1(kind, value),
        enabled,
        CapacityRemainingRuleConfigurationV1(1, warning, critical),
        1,
        NOW,
        NOW,
        None,
        OpaqueIdV1("owner"),
        False,
        None,
    )


def decision(
    value: str | None = "1000",
    *,
    generation: int = 1,
    truth: AlertTruthStateV1 = "current",
) -> AlertDecisionSummaryV1:
    source = AlertSourceReferenceV1(
        "capacity",
        "capacity-window",
        generation,
        OpaqueIdV1(f"event-{generation}"),
        (OpaqueIdV1(f"observation-{generation}"),),
        (),
        NOW,
        NOW,
        NOW + timedelta(minutes=10),
        "rounded",
        "high",
        "quota_remaining",
    )
    return AlertDecisionSummaryV1(
        "quota_remaining",
        truth,
        CanonicalDecimalV1.from_decimal(Decimal(value)) if value is not None else None,
        3000,
        1500,
        NOW + timedelta(hours=1),
        None,
        source,
    )


def signal(
    *,
    generation: int = 1,
    value: str | None = "1000",
    transition: Literal["active", "recovered", "not_evaluable"] = "active",
    severity: AlertSeverityV1 | None = "critical",
    truth: AlertTruthStateV1 = "current",
) -> NormalizedAlertSignalV1:
    return NormalizedAlertSignalV1(
        "capacity_remaining",
        SUBJECT,
        transition,
        severity,
        decision(value, generation=generation, truth=truth),
        1,
    )


def opened() -> AlertViewV1:
    result = reduce_alert_signal(
        None, signal(), builtin_rule("capacity_remaining"), OpaqueIdV1("alert"), NOW
    )
    assert result.alert is not None
    return result.alert


@pytest.mark.parametrize("kind", ["account", "provider", "organization", "global"])
def test_whole_rule_specificity_and_disabled_override(kind: AlertRuleScopeV1) -> None:
    ranks: list[AlertRuleScopeV1] = ["account", "provider", "organization", "global"]
    rules = tuple(rule(item) for item in ranks[ranks.index(kind) :])
    actual = resolve_effective_rule(SUBJECT, "capacity_remaining", rules)
    assert actual.selected.scope.scope_kind == kind
    disabled = replace(rules[0], enabled=False)
    assert (
        resolve_effective_rule(
            SUBJECT, "capacity_remaining", (disabled,) + rules[1:]
        ).selected
        == disabled
    )


def test_provider_beats_organization_and_no_guess_for_unresolved_account() -> None:
    assert (
        resolve_effective_rule(
            SUBJECT, "capacity_remaining", (rule("organization"), rule("provider"))
        ).selected.scope.scope_kind
        == "provider"
    )
    unresolved = replace(SUBJECT, account_id=None, organization_id=None)
    assert resolve_effective_rule(
        unresolved, "capacity_remaining", (rule("account"), rule("organization"))
    ).selected.is_builtin
    assert resolve_effective_rule(
        SUBJECT,
        "capacity_remaining",
        (
            rule("account", warning=4000, critical=100),
            rule("global", warning=9000, critical=8000),
        ),
    ).selected.configuration == CapacityRemainingRuleConfigurationV1(1, 4000, 100)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("3001", None),
        ("3000", "warning"),
        ("1500", "critical"),
        ("1500.0001", "warning"),
        ("3000.0001", None),
        ("0", "critical"),
    ],
)
def test_inclusive_exact_remaining_thresholds(value: str, expected: str | None) -> None:
    assert (
        capacity_remaining_severity(decision(value), builtin_rule("capacity_remaining"))
        == expected
    )


@pytest.mark.parametrize(
    "truth,value",
    [("stale", "0"), ("unknown", None), ("unsupported", None), ("unavailable", None)],
)
def test_missing_or_stale_is_not_exhausted(
    truth: AlertTruthStateV1, value: str | None
) -> None:
    assert (
        capacity_remaining_severity(
            decision(value, truth=truth), builtin_rule("capacity_remaining")
        )
        is None
    )


def test_fingerprint_stable_across_mutable_scope_and_distinct_per_window() -> None:
    first = fingerprint_alert_condition("capacity_remaining", SUBJECT, 1)
    moved = replace(
        SUBJECT, organization_id=OpaqueIdV1("other-org"), registry_revision=8
    )
    assert fingerprint_alert_condition("capacity_remaining", moved, 1) == first
    assert (
        fingerprint_alert_condition(
            "capacity_remaining", replace(SUBJECT, dimension_id="other-window"), 1
        )
        != first
    )
    assert fingerprint_alert_condition("capacity_exhausted", SUBJECT, 1) != first


def test_duplicate_old_and_unknown_generations_never_recover() -> None:
    alert = opened()
    assert (
        reduce_alert_signal(
            alert, signal(), alert.rule, alert.alert_id, NOW
        ).disposition
        == "duplicate"
    )
    repeated = reduce_alert_signal(
        alert,
        signal(generation=3),
        alert.rule,
        alert.alert_id,
        NOW + timedelta(seconds=1),
    ).alert
    assert repeated is not None
    assert repeated.occurrence_count == 2
    assert repeated.notification_revision == 1
    old = signal(generation=2, value="8000", transition="recovered", severity=None)
    assert (
        reduce_alert_signal(
            repeated, old, alert.rule, alert.alert_id, NOW + timedelta(seconds=2)
        ).disposition
        == "stale_ignored"
    )
    unknown = signal(
        generation=4,
        value=None,
        transition="not_evaluable",
        severity=None,
        truth="unknown",
    )
    result = reduce_alert_signal(
        repeated, unknown, alert.rule, alert.alert_id, NOW + timedelta(seconds=3)
    )
    assert result.alert == repeated
    assert result.disposition == "not_evaluable"
    assert (
        reduce_alert_signal(
            None, old, alert.rule, alert.alert_id, NOW, greatest_source_generation=4
        ).disposition
        == "stale_ignored"
    )


def test_same_event_id_with_changed_decision_conflicts() -> None:
    with pytest.raises(ValueError, match="alert_event_conflict"):
        reduce_alert_signal(
            opened(),
            signal(value="900"),
            builtin_rule("capacity_remaining"),
            OpaqueIdV1("alert"),
            NOW,
        )


def test_older_or_unavailable_inverse_never_closes_condition() -> None:
    alert = opened()
    with pytest.raises(ValueError, match="alert_recovery_not_proven"):
        reduce_alert_signal(
            alert,
            signal(generation=2, value="1000", transition="recovered", severity=None),
            alert.rule,
            alert.alert_id,
            NOW,
        )
    unproved = signal(
        generation=2, value=None, truth="unknown", transition="recovered", severity=None
    )
    assert (
        reduce_alert_signal(alert, unproved, alert.rule, alert.alert_id, NOW).alert
        == alert
    )


def test_ack_snooze_repeat_escalation_recovery_and_reopen() -> None:
    warning = reduce_alert_signal(
        None,
        signal(value="2500", severity="warning"),
        builtin_rule("capacity_remaining"),
        OpaqueIdV1("alert"),
        NOW,
    ).alert
    assert warning is not None
    ack = acknowledge_alert(
        warning,
        AcknowledgeAlertCommandV1(
            OpaqueIdV1("ack"), OpaqueIdV1("owner"), warning.alert_id, 1, NOW
        ),
    ).alert
    assert ack is not None and not ack.unread
    snoozed = snooze_alert(
        ack,
        SnoozeAlertCommandV1(
            OpaqueIdV1("snooze"),
            OpaqueIdV1("owner"),
            ack.alert_id,
            ack.record_version,
            NOW,
            60,
        ),
    ).alert
    assert snoozed is not None and snoozed.acknowledged_at == NOW
    repeated = reduce_alert_signal(
        snoozed,
        signal(generation=2, value="2500", severity="warning"),
        snoozed.rule,
        snoozed.alert_id,
        NOW + timedelta(seconds=1),
    ).alert
    assert (
        repeated is not None
        and repeated.snoozed_until == snoozed.snoozed_until
        and not repeated.unread
    )
    critical = reduce_alert_signal(
        repeated,
        signal(generation=3),
        repeated.rule,
        repeated.alert_id,
        NOW + timedelta(seconds=2),
    ).alert
    assert (
        critical is not None
        and critical.unread
        and critical.acknowledged_at is None
        and critical.snoozed_until is None
    )
    recovered = reduce_alert_signal(
        critical,
        signal(generation=4, value="8000", transition="recovered", severity=None),
        critical.rule,
        critical.alert_id,
        NOW + timedelta(seconds=3),
    ).alert
    assert (
        recovered is not None
        and recovered.lifecycle == "recovered"
        and recovered.severity == "information"
    )
    reopened = reduce_alert_signal(
        recovered,
        signal(generation=5),
        recovered.rule,
        recovered.alert_id,
        NOW + timedelta(seconds=4),
    ).alert
    assert (
        reopened is not None
        and reopened.occurrence_generation == 2
        and reopened.occurrence_count == 1
        and reopened.alert_id == critical.alert_id
    )


def test_read_requires_notification_revision_and_command_requires_record_version() -> (
    None
):
    alert = opened()
    read = mark_alert_read(
        alert,
        MarkAlertReadCommandV1(
            OpaqueIdV1("read"), OpaqueIdV1("owner"), alert.alert_id, 1, NOW
        ),
    ).alert
    assert read is not None and not read.unread and read.notification_revision == 1
    with pytest.raises(ValueError, match="alert_version_conflict"):
        acknowledge_alert(
            read,
            AcknowledgeAlertCommandV1(
                OpaqueIdV1("ack"), OpaqueIdV1("owner"), read.alert_id, 1, NOW
            ),
        )
    with pytest.raises(ValueError, match="alert_notification_conflict"):
        mark_alert_read(
            alert,
            MarkAlertReadCommandV1(
                OpaqueIdV1("read"), OpaqueIdV1("owner"), alert.alert_id, 2, NOW
            ),
        )


def test_snooze_expiry_is_due_fenced_and_idempotent() -> None:
    alert = opened()
    snoozed = snooze_alert(
        alert,
        SnoozeAlertCommandV1(
            OpaqueIdV1("snooze"), OpaqueIdV1("owner"), alert.alert_id, 1, NOW, 60
        ),
    ).alert
    assert snoozed is not None
    assert expire_snooze(snoozed, 1, 2, NOW + timedelta(seconds=60)).alert == snoozed
    assert expire_snooze(snoozed, 1, 1, NOW + timedelta(seconds=59)).alert == snoozed
    expired = expire_snooze(snoozed, 1, 1, NOW + timedelta(seconds=60)).alert
    assert expired is not None and expired.snoozed_until is None and expired.unread
    assert expire_snooze(expired, 1, 1, NOW + timedelta(seconds=61)).transition is None


@pytest.mark.parametrize("seconds", [59, 2592001])
def test_snooze_bounds(seconds: int) -> None:
    with pytest.raises(ValueError):
        SnoozeAlertCommandV1(
            OpaqueIdV1("snooze"),
            OpaqueIdV1("owner"),
            OpaqueIdV1("alert"),
            1,
            NOW,
            seconds,
        )


def test_unsnooze_requires_active_version_and_config_close_is_distinct() -> None:
    alert = opened()
    snoozed = snooze_alert(
        alert,
        SnoozeAlertCommandV1(
            OpaqueIdV1("snooze"), OpaqueIdV1("owner"), alert.alert_id, 1, NOW, 60
        ),
    ).alert
    assert snoozed is not None
    undone = unsnooze_alert(
        snoozed,
        UnsnoozeAlertCommandV1(
            OpaqueIdV1("undo"),
            OpaqueIdV1("owner"),
            alert.alert_id,
            snoozed.record_version,
            NOW,
        ),
    ).alert
    assert undone is not None and undone.snoozed_until is None
    disabled = replace(alert.rule, enabled=False)
    closed = reduce_alert_signal(
        alert, signal(generation=2), disabled, alert.alert_id, NOW
    ).alert
    assert (
        closed is not None
        and closed.lifecycle == "closed_by_configuration"
        and closed.recovered_at is None
    )


def test_notification_order_and_visible_unread_counts() -> None:
    critical = opened()
    warning = reduce_alert_signal(
        None,
        signal(value="2500", severity="warning"),
        critical.rule,
        OpaqueIdV1("warning-alert"),
        NOW,
    ).alert
    assert warning is not None
    snoozed = replace(
        critical,
        alert_id=OpaqueIdV1("snoozed-alert"),
        snoozed_until=NOW + timedelta(seconds=60),
    )
    ordered = ordered_notifications((warning, snoozed, critical), NOW)
    assert [item.alert.alert_id for item in ordered] == [
        critical.alert_id,
        warning.alert_id,
        snoozed.alert_id,
    ]
    counts = notification_counts((warning, snoozed, critical), NOW)
    assert (
        counts.active_critical == 1
        and counts.active_warning == 1
        and counts.visible_unread == 2
        and counts.total_unread == 3
        and counts.snoozed == 1
    )


def test_retention_cutoff_and_active_pending_boundary_guards() -> None:
    alert = opened()
    terminal = reduce_alert_signal(
        alert,
        signal(generation=2, value="8000", transition="recovered", severity=None),
        alert.rule,
        alert.alert_id,
        NOW,
    ).alert
    assert terminal is not None
    assert retention_cutoff(NOW + timedelta(days=365)) == NOW
    assert not terminal_alert_is_expired(
        terminal,
        NOW + timedelta(days=365),
        has_pending_work=False,
        has_retained_dependencies=False,
        replay_safe=True,
    )
    later = NOW + timedelta(days=365, seconds=1)
    assert terminal_alert_is_expired(
        terminal,
        later,
        has_pending_work=False,
        has_retained_dependencies=False,
        replay_safe=True,
    )
    assert not terminal_alert_is_expired(
        alert,
        later,
        has_pending_work=False,
        has_retained_dependencies=False,
        replay_safe=True,
    )
    assert not terminal_alert_is_expired(
        terminal,
        later,
        has_pending_work=True,
        has_retained_dependencies=False,
        replay_safe=True,
    )
    assert not terminal_alert_is_expired(
        terminal,
        later,
        has_pending_work=False,
        has_retained_dependencies=True,
        replay_safe=True,
    )
    assert not terminal_alert_is_expired(
        terminal,
        later,
        has_pending_work=False,
        has_retained_dependencies=False,
        replay_safe=False,
    )

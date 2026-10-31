"""Pure M07 rule specificity and exact remaining-capacity decisions."""

import hashlib
import json
from datetime import datetime, timedelta

from agentmonitor.contracts.alerting_v1 import (
    AlertConditionTypeV1,
    AlertDecisionSummaryV1,
    AlertRuleViewV1,
    AlertScopeRefV1,
    AlertSeverityV1,
    AlertSourceReferenceV1,
    AlertSubjectV1,
    CapacityRemainingRuleConfigurationV1,
    ConditionRuleConfigurationV1,
    EffectiveAlertRuleViewV1,
)
from agentmonitor.contracts.capacity_v1 import CapacityAlertConditionV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import AlertSubjectScopeV1
from agentmonitor.modules.alerting.domain.signals import NormalizedAlertSignalV1

BUILTIN_POLICY_VERSION = "m07-builtin-1"


def builtin_rule(condition_type: AlertConditionTypeV1) -> AlertRuleViewV1:
    configuration = (
        CapacityRemainingRuleConfigurationV1(1, 3000, 1500)
        if condition_type == "capacity_remaining"
        else ConditionRuleConfigurationV1(1)
    )
    return AlertRuleViewV1(
        None,
        condition_type,
        AlertScopeRefV1("global", None),
        True,
        configuration,
        0,
        None,
        None,
        None,
        None,
        True,
        BUILTIN_POLICY_VERSION,
    )


def resolve_effective_rule(
    subject: AlertSubjectV1,
    condition_type: AlertConditionTypeV1,
    rules: tuple[AlertRuleViewV1, ...],
) -> EffectiveAlertRuleViewV1:
    scopes: tuple[AlertScopeRefV1, ...] = ()
    if subject.account_id is not None:
        scopes += (AlertScopeRefV1("account", subject.account_id.value),)
    if subject.provider_key is not None:
        scopes += (AlertScopeRefV1("provider", subject.provider_key),)
    if subject.account_id is not None and subject.organization_id is not None:
        scopes += (AlertScopeRefV1("organization", subject.organization_id.value),)
    scopes += (AlertScopeRefV1("global", None),)
    candidates: tuple[AlertRuleViewV1, ...] = ()
    for scope in scopes:
        matches = tuple(
            item
            for item in rules
            if item.condition_type == condition_type
            and item.scope == scope
            and item.archived_at is None
            and not item.is_builtin
        )
        if len(matches) > 1:
            raise ValueError("alert_rule_scope_conflict")
        candidates += matches
    candidates += (builtin_rule(condition_type),)
    selected = candidates[0]
    explanations = {
        "account": "account_override",
        "provider": "provider_override",
        "organization": "organization_override",
        "global": "global_override",
    }
    from typing import Literal, cast

    code = (
        "builtin_default"
        if selected.is_builtin
        else explanations[selected.scope.scope_kind]
    )
    return EffectiveAlertRuleViewV1(
        selected,
        candidates,
        subject.registry_revision,
        cast(
            Literal[
                "account_override",
                "provider_override",
                "organization_override",
                "global_override",
                "builtin_default",
            ],
            code,
        ),
    )


def capacity_remaining_severity(
    decision: AlertDecisionSummaryV1,
    rule: AlertRuleViewV1,
) -> AlertSeverityV1 | None:
    if rule.condition_type != "capacity_remaining" or not isinstance(
        rule.configuration, CapacityRemainingRuleConfigurationV1
    ):
        raise ValueError("alert_capacity_rule_required")
    if (
        not rule.enabled
        or decision.truth_state != "current"
        or decision.remaining_basis_points is None
    ):
        return None
    value = decision.remaining_basis_points.as_decimal()
    if value <= rule.configuration.critical_remaining_basis_points:
        return "critical"
    if value <= rule.configuration.warning_remaining_basis_points:
        return "warning"
    return None


def map_capacity_alert_condition(
    fact: CapacityAlertConditionV1,
    scope: AlertSubjectScopeV1,
    event_id: OpaqueIdV1,
    rule: AlertRuleViewV1,
    *,
    as_of: datetime,
) -> NormalizedAlertSignalV1:
    """Interpret an admitted current fact; no producer query or value derivation."""
    if (
        not scope.eligible
        or fact.account_id != scope.account_id
        or fact.provider_key != scope.provider_key
    ):
        raise ValueError("alert_capacity_scope_conflict")
    if as_of.utcoffset() != timedelta(0) or as_of < fact.recorded_at:
        raise ValueError("alert_capacity_time_invalid")
    if fact.availability == "current" and (
        fact.freshness_deadline is None or as_of >= fact.freshness_deadline
    ):
        raise ValueError("alert_capacity_current_expired")
    if rule.condition_type not in ("capacity_remaining", "capacity_exhausted"):
        raise ValueError("alert_capacity_condition_unsupported")
    material = json.dumps(
        [fact.account_id.value, fact.resource_id.value, fact.window_id.value],
        ensure_ascii=True,
        separators=(",", ":"),
    )
    source = AlertSourceReferenceV1(
        "capacity",
        "capacity:" + hashlib.sha256(material.encode("ascii")).hexdigest(),
        fact.generation,
        event_id,
        fact.observation_ids,
        (),
        fact.observed_at,
        fact.recorded_at,
        fact.freshness_deadline,
        fact.precision,
        fact.confidence,
        fact.reason_code,
    )
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
    configuration = rule.configuration
    thresholds = (
        (
            configuration.warning_remaining_basis_points,
            configuration.critical_remaining_basis_points,
        )
        if isinstance(configuration, CapacityRemainingRuleConfigurationV1)
        else (None, None)
    )
    decision = AlertDecisionSummaryV1(
        "source_not_evaluable"
        if fact.availability != "current"
        else "quota_remaining"
        if rule.condition_type == "capacity_remaining"
        else "capacity_exhausted"
        if fact.exhausted
        else "capacity_current",
        fact.availability,
        fact.remaining_basis_points,
        thresholds[0],
        thresholds[1],
        fact.reset_at,
        None,
        source,
    )
    severity: AlertSeverityV1 | None = None
    if fact.availability == "current" and rule.enabled:
        severity = (
            capacity_remaining_severity(decision, rule)
            if rule.condition_type == "capacity_remaining"
            else "critical"
            if fact.exhausted
            else None
        )
    return NormalizedAlertSignalV1(
        rule.condition_type,
        subject,
        "not_evaluable"
        if fact.availability != "current" or not rule.enabled
        else "active"
        if severity is not None
        else "recovered",
        severity,
        decision,
        1,
    )

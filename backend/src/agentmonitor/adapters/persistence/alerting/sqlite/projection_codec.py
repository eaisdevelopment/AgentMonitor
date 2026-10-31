"""Closed M07 alert snapshots; no provider payload or free-form text."""

import json
from dataclasses import asdict
from datetime import datetime
from typing import Literal, cast

from agentmonitor.adapters.persistence.alerting.sqlite.codec import (
    canonical_json,
    integer,
    text,
    utc_text,
    utc_value,
)
from agentmonitor.contracts.alerting_v1 import (
    AlertConditionTypeV1,
    AlertDecisionSummaryV1,
    AlertDimensionKindV1,
    AlertLifecycleV1,
    AlertOpenedV1,
    AlertReasonCodeV1,
    AlertRuleConfigurationV1,
    AlertRuleViewV1,
    AlertScopeRefV1,
    AlertSeverityV1,
    AlertSourceReferenceV1,
    AlertStateChangedV1,
    AlertSubjectV1,
    AlertTruthStateV1,
    AlertViewV1,
    CapacityRemainingRuleConfigurationV1,
    ConditionRuleConfigurationV1,
)
from agentmonitor.contracts.common_provenance_v1 import ConfidenceV1, PrecisionV1
from agentmonitor.contracts.common_quantity_v1 import CanonicalDecimalV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from sqlalchemy.engine import RowMapping


def _pack(value: object) -> object:
    if isinstance(value, datetime):
        return utc_text(value)
    if isinstance(value, dict):
        return {text(key): _pack(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_pack(item) for item in value]
    if value is None or type(value) in (str, int, bool):
        return value
    raise ValueError("alert_snapshot_value_invalid")


def _dump(value: object) -> str:
    if not isinstance(value, (AlertRuleViewV1, AlertDecisionSummaryV1, AlertViewV1)):
        raise ValueError("alert_snapshot_type_invalid")
    result = canonical_json(_pack(asdict(value)))
    if len(result) > 16384:
        raise ValueError("alert_snapshot_too_large")
    return result


def rule_snapshot(rule: AlertRuleViewV1) -> str:
    return _dump(rule)


def decision_snapshot(decision: AlertDecisionSummaryV1) -> str:
    return _dump(decision)


def alert_snapshot(alert: AlertViewV1) -> str:
    return _dump(alert)


def event_payload_snapshot(event: AlertOpenedV1 | AlertStateChangedV1) -> str:
    """Store the actual published immutable event payload, not a hint dictionary."""
    if not isinstance(event, (AlertOpenedV1, AlertStateChangedV1)):
        raise ValueError("alert_event_payload_invalid")
    result = canonical_json(_pack(asdict(event)))
    if len(result) > 32768:
        raise ValueError("alert_event_payload_too_large")
    return result


def _document(raw: object, keys: frozenset[str]) -> dict[str, object]:
    if type(raw) is not str or len(raw) > 16384:
        raise ValueError("alert_snapshot_invalid")
    try:
        parsed: object = json.loads(raw)
    except (ValueError, TypeError):
        raise ValueError("alert_snapshot_invalid") from None
    if not isinstance(parsed, dict) or parsed.keys() != keys:
        raise ValueError("alert_snapshot_invalid")
    return cast(dict[str, object], parsed)


def _mapping(value: object, keys: frozenset[str]) -> dict[str, object]:
    if not isinstance(value, dict) or value.keys() != keys:
        raise ValueError("alert_snapshot_invalid")
    return cast(dict[str, object], value)


def _optional_id(value: object) -> OpaqueIdV1 | None:
    if value is None:
        return None
    return OpaqueIdV1(text(_mapping(value, frozenset({"value"}))["value"]))


def _required_id(value: object) -> OpaqueIdV1:
    result = _optional_id(value)
    if result is None:
        raise ValueError("alert_snapshot_invalid")
    return result


def _optional_time(value: object) -> datetime | None:
    return None if value is None else utc_value(value)


def _id_list(value: object) -> tuple[OpaqueIdV1, ...]:
    if not isinstance(value, list) or len(value) > 64:
        raise ValueError("alert_snapshot_invalid")
    return tuple(
        OpaqueIdV1(text(_mapping(item, frozenset({"value"}))["value"]))
        for item in value
    )


_RULE_KEYS = frozenset(
    {
        "rule_id",
        "condition_type",
        "scope",
        "enabled",
        "configuration",
        "record_version",
        "created_at",
        "updated_at",
        "archived_at",
        "actor_id",
        "is_builtin",
        "builtin_policy_version",
    }
)
_DECISION_KEYS = frozenset(
    {
        "reason_code",
        "truth_state",
        "remaining_basis_points",
        "warning_remaining_basis_points",
        "critical_remaining_basis_points",
        "reset_at",
        "forecast_exhaustion_at",
        "source",
    }
)
_SOURCE_KEYS = frozenset(
    {
        "producer_key",
        "condition_stream_key",
        "source_generation",
        "event_id",
        "observation_ids",
        "evidence_ids",
        "observed_at",
        "recorded_at",
        "freshness_deadline",
        "precision",
        "confidence",
        "reason_code",
    }
)


def _rule(raw: object) -> AlertRuleViewV1:
    value = _document(raw, _RULE_KEYS)
    scope = _mapping(value["scope"], frozenset({"scope_kind", "scope_id"}))
    config = value["configuration"]
    if not isinstance(config, dict):
        raise ValueError("alert_snapshot_invalid")
    configuration: AlertRuleConfigurationV1
    if config.keys() == {"schema_major"}:
        configuration = ConditionRuleConfigurationV1(
            cast("Literal[1]", integer(config["schema_major"]))
        )
    elif config.keys() == {
        "schema_major",
        "warning_remaining_basis_points",
        "critical_remaining_basis_points",
    }:
        configuration = CapacityRemainingRuleConfigurationV1(
            cast("Literal[1]", integer(config["schema_major"])),
            integer(config["warning_remaining_basis_points"]),
            integer(config["critical_remaining_basis_points"]),
        )
    else:
        raise ValueError("alert_snapshot_invalid")
    if type(value["enabled"]) is not bool or type(value["is_builtin"]) is not bool:
        raise ValueError("alert_snapshot_invalid")
    return AlertRuleViewV1(
        _optional_id(value["rule_id"]),
        cast(AlertConditionTypeV1, text(value["condition_type"])),
        AlertScopeRefV1(
            cast(
                Literal["global", "organization", "provider", "account"],
                text(scope["scope_kind"]),
            ),
            None if scope["scope_id"] is None else text(scope["scope_id"]),
        ),
        value["enabled"],
        configuration,
        integer(value["record_version"]),
        _optional_time(value["created_at"]),
        _optional_time(value["updated_at"]),
        _optional_time(value["archived_at"]),
        _optional_id(value["actor_id"]),
        value["is_builtin"],
        None
        if value["builtin_policy_version"] is None
        else text(value["builtin_policy_version"]),
    )


def _decision(raw: object) -> AlertDecisionSummaryV1:
    value = _document(raw, _DECISION_KEYS)
    source = _mapping(value["source"], _SOURCE_KEYS)
    remaining = value["remaining_basis_points"]
    if remaining is None:
        basis_points = None
    else:
        decimal = _mapping(remaining, frozenset({"coefficient", "scale"}))
        basis_points = CanonicalDecimalV1(
            text(decimal["coefficient"]), integer(decimal["scale"])
        )
    return AlertDecisionSummaryV1(
        cast(AlertReasonCodeV1, text(value["reason_code"])),
        cast(AlertTruthStateV1, text(value["truth_state"])),
        basis_points,
        None
        if value["warning_remaining_basis_points"] is None
        else integer(value["warning_remaining_basis_points"]),
        None
        if value["critical_remaining_basis_points"] is None
        else integer(value["critical_remaining_basis_points"]),
        _optional_time(value["reset_at"]),
        _optional_time(value["forecast_exhaustion_at"]),
        AlertSourceReferenceV1(
            cast(
                Literal[
                    "registry", "collection_control", "capacity", "runtime_observation"
                ],
                text(source["producer_key"]),
            ),
            text(source["condition_stream_key"]),
            integer(source["source_generation"]),
            _required_id(source["event_id"]),
            _id_list(source["observation_ids"]),
            _id_list(source["evidence_ids"]),
            _optional_time(source["observed_at"]),
            utc_value(source["recorded_at"]),
            _optional_time(source["freshness_deadline"]),
            cast(PrecisionV1, text(source["precision"])),
            cast(ConfidenceV1, text(source["confidence"])),
            cast(AlertReasonCodeV1, text(source["reason_code"])),
        ),
    )


def alert_from_row(row: RowMapping) -> AlertViewV1:
    subject = AlertSubjectV1(
        cast(
            Literal["account", "resource", "profile", "collector", "session"],
            text(row["subject_kind"]),
        ),
        OpaqueIdV1(text(row["subject_id"])),
        cast(AlertDimensionKindV1, text(row["dimension_kind"])),
        text(row["dimension_id"]),
        OpaqueIdV1(text(row["account_id"])) if row["account_id"] else None,
        text(row["provider_key"]) if row["provider_key"] else None,
        OpaqueIdV1(text(row["organization_id"])) if row["organization_id"] else None,
        integer(row["registry_revision"]),
    )
    return AlertViewV1(
        OpaqueIdV1(text(row["alert_id"])),
        cast("Literal[1]", integer(row["fingerprint_version"])),
        cast(AlertConditionTypeV1, text(row["condition_type"])),
        subject,
        cast(AlertSeverityV1, text(row["severity"])),
        cast(AlertLifecycleV1, text(row["lifecycle"])),
        integer(row["occurrence_generation"]),
        integer(row["occurrence_count"]),
        integer(row["record_version"]),
        utc_value(row["opened_at"]),
        utc_value(row["last_seen_at"]),
        _optional_time(row["recovered_at"]),
        _optional_time(row["closed_at"]),
        utc_value(row["latest_notification_at"]),
        integer(row["notification_revision"]),
        integer(row["unread"]) == 1,
        _optional_time(row["acknowledged_at"]),
        OpaqueIdV1(text(row["acknowledged_by"])) if row["acknowledged_by"] else None,
        _optional_time(row["snoozed_until"]),
        _rule(row["rule_snapshot_json"]),
        _decision(row["decision_json"]),
        integer(row["aggregate_sequence"]),
    )


_ALERT_KEYS = frozenset(
    {
        "alert_id",
        "fingerprint_version",
        "condition_type",
        "subject",
        "severity",
        "lifecycle",
        "occurrence_generation",
        "occurrence_count",
        "record_version",
        "opened_at",
        "last_seen_at",
        "recovered_at",
        "closed_at",
        "latest_notification_at",
        "notification_revision",
        "unread",
        "acknowledged_at",
        "acknowledged_by",
        "snoozed_until",
        "rule",
        "decision",
        "aggregate_sequence",
    }
)


def alert_from_snapshot(raw: object) -> AlertViewV1:
    """Restore the exact command result even if later actions changed projection."""
    value = _document(raw, _ALERT_KEYS)
    subject = _mapping(
        value["subject"],
        frozenset(
            {
                "subject_kind",
                "subject_id",
                "dimension_kind",
                "dimension_id",
                "account_id",
                "provider_key",
                "organization_id",
                "registry_revision",
            }
        ),
    )
    if type(value["unread"]) is not bool:
        raise ValueError("alert_snapshot_invalid")
    scope = AlertSubjectV1(
        cast(
            Literal["account", "resource", "profile", "collector", "session"],
            text(subject["subject_kind"]),
        ),
        _required_id(subject["subject_id"]),
        cast(AlertDimensionKindV1, text(subject["dimension_kind"])),
        text(subject["dimension_id"]),
        _optional_id(subject["account_id"]),
        None if subject["provider_key"] is None else text(subject["provider_key"]),
        _optional_id(subject["organization_id"]),
        integer(subject["registry_revision"]),
    )
    return AlertViewV1(
        _required_id(value["alert_id"]),
        cast(Literal[1], integer(value["fingerprint_version"])),
        cast(AlertConditionTypeV1, text(value["condition_type"])),
        scope,
        cast(AlertSeverityV1, text(value["severity"])),
        cast(AlertLifecycleV1, text(value["lifecycle"])),
        integer(value["occurrence_generation"]),
        integer(value["occurrence_count"]),
        integer(value["record_version"]),
        utc_value(value["opened_at"]),
        utc_value(value["last_seen_at"]),
        _optional_time(value["recovered_at"]),
        _optional_time(value["closed_at"]),
        utc_value(value["latest_notification_at"]),
        integer(value["notification_revision"]),
        value["unread"],
        _optional_time(value["acknowledged_at"]),
        _optional_id(value["acknowledged_by"]),
        _optional_time(value["snoozed_until"]),
        _rule(canonical_json(value["rule"])),
        _decision(canonical_json(value["decision"])),
        integer(value["aggregate_sequence"]),
    )

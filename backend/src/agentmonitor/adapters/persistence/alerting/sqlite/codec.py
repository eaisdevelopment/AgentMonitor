"""Closed M07-owned configuration codec; no provider or arbitrary payload parser."""

import json
from datetime import UTC, datetime, timedelta
from typing import cast

from agentmonitor.contracts.alerting_v1 import (
    AlertConditionTypeV1,
    AlertRuleConfigurationV1,
    AlertRuleScopeV1,
    AlertRuleViewV1,
    AlertScopeRefV1,
    CapacityRemainingRuleConfigurationV1,
    ConditionRuleConfigurationV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from sqlalchemy.engine import RowMapping


def text(value: object) -> str:
    if type(value) is not str:
        raise ValueError("alert_stored_value_invalid")
    return value


def integer(value: object) -> int:
    if type(value) is not int:
        raise ValueError("alert_stored_value_invalid")
    return value


def utc_text(value: datetime) -> str:
    if value.utcoffset() != timedelta(0):
        raise ValueError("alert_utc_required")
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def utc_value(value: object) -> datetime:
    return datetime.fromisoformat(text(value).replace("Z", "+00:00")).astimezone(UTC)


def canonical_json(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    )


def config_document(configuration: AlertRuleConfigurationV1) -> dict[str, int]:
    result = {"schema_major": 1}
    if isinstance(configuration, CapacityRemainingRuleConfigurationV1):
        result.update(
            warning_remaining_basis_points=configuration.warning_remaining_basis_points,
            critical_remaining_basis_points=configuration.critical_remaining_basis_points,
        )
    return result


def configuration(raw: str) -> AlertRuleConfigurationV1:
    parsed: object = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("alert_stored_configuration_invalid")
    data = cast(dict[str, object], parsed)
    if data.keys() == {"schema_major"} and integer(data["schema_major"]) == 1:
        return ConditionRuleConfigurationV1(1)
    if (
        data.keys()
        == {
            "schema_major",
            "warning_remaining_basis_points",
            "critical_remaining_basis_points",
        }
        and integer(data["schema_major"]) == 1
    ):
        return CapacityRemainingRuleConfigurationV1(
            1,
            integer(data["warning_remaining_basis_points"]),
            integer(data["critical_remaining_basis_points"]),
        )
    raise ValueError("alert_stored_configuration_invalid")


def rule_from_row(row: RowMapping) -> AlertRuleViewV1:
    kind = cast(AlertRuleScopeV1, text(row["scope_kind"]))
    return AlertRuleViewV1(
        OpaqueIdV1(text(row["rule_id"])),
        cast(AlertConditionTypeV1, text(row["condition_type"])),
        AlertScopeRefV1(kind, None if kind == "global" else text(row["scope_key"])),
        bool(integer(row["enabled"])),
        configuration(text(row["config_json"])),
        integer(row["record_version"]),
        utc_value(row["created_at"]),
        utc_value(row["updated_at"]),
        utc_value(row["archived_at"]) if row["archived_at"] is not None else None,
        OpaqueIdV1(text(row["actor_id"])),
        False,
        None,
    )

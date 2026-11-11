"""Canonical, bounded encoding of the closed M05 normalized report contract."""

import hashlib
import json
from dataclasses import fields
from datetime import UTC, datetime
from typing import Any, cast

from agentmonitor.contracts.capacity_v1 import (
    BudgetCostBucketV1,
    BudgetDimensionV1,
    BudgetPeriodV1,
    BudgetReportInputV1,
    BudgetUsageBucketV1,
    CapacitySubjectV2,
)
from agentmonitor.contracts.common_provenance_v1 import (
    FallbackAttemptV1,
    ObservationProvenanceV1,
)
from agentmonitor.contracts.common_quantity_v1 import (
    CanonicalDecimalV1,
    ExactMoneyV1,
    ExactQuantityV1,
)
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.contracts.registry_v1 import ProviderTargetRefV1

MAX_REPORT_BYTES = 16 * 1024 * 1024
_TYPES = (
    BudgetReportInputV1,
    CapacitySubjectV2,
    ProviderTargetRefV1,
    BudgetPeriodV1,
    BudgetCostBucketV1,
    BudgetUsageBucketV1,
    BudgetDimensionV1,
    ExactMoneyV1,
    ExactQuantityV1,
    CanonicalDecimalV1,
    ObservationProvenanceV1,
    FallbackAttemptV1,
    FieldAvailabilityV1,
)


class BudgetCodecError(ValueError):
    """A safe error without provider values or serialized input."""

    def __init__(self) -> None:
        super().__init__("budget_report_encoding_invalid")


def utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise BudgetCodecError()
    return (
        value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )


def _encode(value: object) -> object:
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is datetime:
        return utc_text(value)
    if type(value) is OpaqueIdV1:
        return value.value
    if type(value) is tuple:
        return [_encode(item) for item in value]
    if type(value) in _TYPES:
        return {
            field.name: _encode(getattr(value, field.name))
            for field in fields(cast(Any, value))
        }
    raise BudgetCodecError()


def _object(data: Any, cls: type[Any]) -> dict[str, Any]:
    if type(data) is not dict or set(data) != {field.name for field in fields(cls)}:
        raise BudgetCodecError()
    return cast(dict[str, Any], data)


def _time(value: Any) -> datetime:
    if type(value) is not str or len(value) != 27 or not value.endswith("Z"):
        raise BudgetCodecError()
    parsed = datetime.fromisoformat(value)
    if utc_text(parsed) != value:
        raise BudgetCodecError()
    return parsed


def _period(value: Any) -> BudgetPeriodV1:
    data = _object(value, BudgetPeriodV1)
    return BudgetPeriodV1(_time(data["start"]), _time(data["end"]))


def _decimal(value: Any) -> CanonicalDecimalV1:
    return CanonicalDecimalV1(**_object(value, CanonicalDecimalV1))


def _dimensions(value: Any) -> tuple[BudgetDimensionV1, ...]:
    if type(value) is not list:
        raise BudgetCodecError()
    return tuple(
        BudgetDimensionV1(**_object(item, BudgetDimensionV1)) for item in value
    )


def _report(data: Any) -> BudgetReportInputV1:
    values = dict(_object(data, BudgetReportInputV1))
    subject = dict(_object(values["subject"], CapacitySubjectV2))
    target = dict(_object(subject["provider_target"], ProviderTargetRefV1))
    target["target_id"] = OpaqueIdV1(target["target_id"])
    subject["provider_target"] = ProviderTargetRefV1(**target)
    for name in ("account_id", "resource_id"):
        subject[name] = OpaqueIdV1(subject[name])
    values["subject"] = CapacitySubjectV2(**subject)
    values["binding_id"] = OpaqueIdV1(values["binding_id"])
    if values["scope_id"] is not None:
        values["scope_id"] = OpaqueIdV1(values["scope_id"])
    if values["scope_evidence"] not in (
        "unresolved",
        "owner_asserted",
        "provider_verified",
    ):
        raise BudgetCodecError()
    if values["completeness"] not in ("complete", "partial", "unknown"):
        raise BudgetCodecError()
    values["requested_period"] = _period(values["requested_period"])
    if values["covered_period"] is not None:
        values["covered_period"] = _period(values["covered_period"])
    for name in ("collected_at", "source_data_through"):
        if values[name] is not None:
            values[name] = _time(values[name])
    for name in ("grouping", "omission_codes", "cost_buckets", "usage_buckets"):
        if type(values[name]) is not list:
            raise BudgetCodecError()
    costs = []
    for raw in values["cost_buckets"]:
        row = dict(_object(raw, BudgetCostBucketV1))
        money = _object(row["amount"], ExactMoneyV1)
        row["amount"] = ExactMoneyV1(_decimal(money["amount"]), money["currency"])
        row["period"] = _period(row["period"])
        row["dimensions"] = _dimensions(row["dimensions"])
        if row["kind"] not in ("charge", "adjustment"):
            raise BudgetCodecError()
        costs.append(BudgetCostBucketV1(**row))
    usage = []
    for raw in values["usage_buckets"]:
        row = dict(_object(raw, BudgetUsageBucketV1))
        quantity = _object(row["quantity"], ExactQuantityV1)
        row["quantity"] = ExactQuantityV1(
            _decimal(quantity["amount"]), quantity["unit"]
        )
        row["period"] = _period(row["period"])
        row["dimensions"] = _dimensions(row["dimensions"])
        usage.append(BudgetUsageBucketV1(**row))
    values["cost_buckets"] = tuple(costs)
    values["usage_buckets"] = tuple(usage)
    values["grouping"] = tuple(values["grouping"])
    values["omission_codes"] = tuple(values["omission_codes"])
    return BudgetReportInputV1(**values)


def _dump(report: BudgetReportInputV1) -> str:
    text = json.dumps(
        _encode(report), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    if len(text) > MAX_REPORT_BYTES:
        raise BudgetCodecError()
    return text


def encode_budget_report(report: BudgetReportInputV1) -> str:
    try:
        if type(report) is not BudgetReportInputV1:
            raise BudgetCodecError()
        # Reconstruct to enforce runtime closed enums even for a caller that
        # bypassed a Literal annotation; no new serialization surface is open.
        return _dump(_report(_encode(report)))
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise BudgetCodecError() from None


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BudgetCodecError()
        result[key] = value
    return result


def _reject_number(value: str) -> None:
    raise BudgetCodecError()


def decode_budget_report(text: str) -> BudgetReportInputV1:
    try:
        if type(text) is not str or len(text) > MAX_REPORT_BYTES or not text.isascii():
            raise BudgetCodecError()
        data = json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
        report = _report(data)
        if _dump(report) != text:
            raise BudgetCodecError()
        return report
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise BudgetCodecError() from None


def budget_report_digest(report: BudgetReportInputV1) -> str:
    return hashlib.sha256(encode_budget_report(report).encode("ascii")).hexdigest()


def _provenance(data: Any) -> ObservationProvenanceV1:
    values = dict(_object(data, ObservationProvenanceV1))
    variants = {
        "source_class": (
            "documented_api",
            "supported_cli",
            "approved_local_metadata",
            "experimental_private_or_browser",
        ),
        "precision": ("exact", "rounded", "range", "estimated", "unknown"),
        "confidence": ("confirmed", "high", "medium", "low", "unknown"),
        "value_kind": (
            "authoritative",
            "provider_reported",
            "derived",
            "heuristic",
            "unknown",
        ),
    }
    for name, choices in variants.items():
        if values[name] not in choices:
            raise BudgetCodecError()
    for name in (
        "provider_version_availability",
        "observed_at_availability",
        "freshness_availability",
    ):
        values[name] = FieldAvailabilityV1(**_object(values[name], FieldAvailabilityV1))
    for name in ("observed_at", "collected_at", "freshness_deadline"):
        if values[name] is not None:
            values[name] = _time(values[name])
    for name in ("operation_id", "correlation_id"):
        values[name] = OpaqueIdV1(values[name])
    for name in ("fallback_lineage", "warnings", "input_observation_ids"):
        if type(values[name]) is not list:
            raise BudgetCodecError()
    values["fallback_lineage"] = tuple(
        FallbackAttemptV1(**_object(item, FallbackAttemptV1))
        for item in values["fallback_lineage"]
    )
    values["warnings"] = tuple(values["warnings"])
    values["input_observation_ids"] = tuple(
        OpaqueIdV1(item) for item in values["input_observation_ids"]
    )
    return ObservationProvenanceV1(**values)


def encode_budget_provenance(provenance: ObservationProvenanceV1) -> str:
    try:
        if type(provenance) is not ObservationProvenanceV1:
            raise BudgetCodecError()
        value = _provenance(_encode(provenance))
        text = json.dumps(
            _encode(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        if len(text) > 65536:
            raise BudgetCodecError()
        return text
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise BudgetCodecError() from None


def decode_budget_provenance(text: str) -> ObservationProvenanceV1:
    try:
        if type(text) is not str or len(text) > 65536 or not text.isascii():
            raise BudgetCodecError()
        value = _provenance(
            json.loads(
                text,
                object_pairs_hook=_pairs,
                parse_float=_reject_number,
                parse_constant=_reject_number,
            )
        )
        if encode_budget_provenance(value) != text:
            raise BudgetCodecError()
        return value
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise BudgetCodecError() from None

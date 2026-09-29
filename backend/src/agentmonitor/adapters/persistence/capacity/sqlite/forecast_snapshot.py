"""Closed, bounded M05 current forecast snapshot wire stored in owned SQLite."""

import json
from datetime import datetime

from agentmonitor.contracts.capacity_v1 import (
    CapacityBurnRateV1,
    CapacityForecastV1,
    CapacitySubjectV1,
)
from agentmonitor.contracts.common_quantity_v1 import (
    CanonicalDecimalV1,
    ExactQuantityV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


class ForecastSnapshotInvalidV1(ValueError):
    pass


def _quantity(value: ExactQuantityV1) -> list[object]:
    return [value.amount.coefficient, value.amount.scale, value.unit]


def _read_quantity(value: object) -> ExactQuantityV1:
    if not isinstance(value, list) or len(value) != 3:
        raise ForecastSnapshotInvalidV1("capacity_forecast_snapshot_invalid")
    coefficient, scale, unit = value
    if (
        not isinstance(coefficient, str)
        or type(scale) is not int
        or not isinstance(unit, str)
    ):
        raise ForecastSnapshotInvalidV1("capacity_forecast_snapshot_invalid")
    return ExactQuantityV1(CanonicalDecimalV1(coefficient, scale), unit)


def _timestamp(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 40:
        raise ForecastSnapshotInvalidV1("capacity_forecast_snapshot_invalid")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    offset = result.utcoffset()
    if offset is None or offset.total_seconds() != 0:
        raise ForecastSnapshotInvalidV1("capacity_forecast_snapshot_invalid")
    return result


def encode_forecast_snapshot_v1(forecast: CapacityForecastV1) -> str:
    burn = forecast.burn_rate
    data = {
        "schema": "capacity.current.forecast.v1",
        "forecast_id": forecast.forecast_id.value,
        "generation": forecast.generation,
        "subject": [
            forecast.subject.provider_key,
            forecast.subject.installation_id.value,
            forecast.subject.account_id.value,
            forecast.subject.resource_id.value,
        ],
        "window_id": forecast.window_id.value,
        "window_definition_id": forecast.window_definition_id.value,
        "metric": forecast.metric,
        "state": forecast.state,
        "burn_rate": None
        if burn is None
        else {
            "estimate": _quantity(burn.estimate),
            "lower_bound": _quantity(burn.lower_bound),
            "upper_bound": _quantity(burn.upper_bound),
            "sample_count": burn.sample_count,
            "observed_span_seconds": [
                burn.observed_span_seconds.coefficient,
                burn.observed_span_seconds.scale,
            ],
            "input_observation_ids": [
                item.value for item in burn.input_observation_ids
            ],
            "time_basis": burn.time_basis,
        },
        "earliest_exhaustion_at": forecast.earliest_exhaustion_at.isoformat()
        if forecast.earliest_exhaustion_at
        else None,
        "latest_exhaustion_at": forecast.latest_exhaustion_at.isoformat()
        if forecast.latest_exhaustion_at
        else None,
        "reset_relation": forecast.reset_relation,
        "confidence": forecast.confidence,
        "precision": forecast.precision,
        "uncertainty_codes": list(forecast.uncertainty_codes),
        "reason_codes": list(forecast.reason_codes),
        "input_observation_ids": [
            item.value for item in forecast.input_observation_ids
        ],
        "input_set_digest": forecast.input_set_digest,
        "method_id": forecast.method_id,
        "method_version": forecast.method_version,
        "generated_at": forecast.generated_at.isoformat(),
        "valid_until": forecast.valid_until.isoformat()
        if forecast.valid_until
        else None,
    }
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(encoded) > 65536:
        raise ForecastSnapshotInvalidV1("capacity_forecast_snapshot_too_large")
    return encoded


def decode_forecast_snapshot_v1(encoded: str) -> CapacityForecastV1:
    if len(encoded) > 65536:
        raise ForecastSnapshotInvalidV1("capacity_forecast_snapshot_too_large")
    try:
        data = json.loads(encoded)
        if (
            not isinstance(data, dict)
            or set(data)
            != {
                "schema",
                "forecast_id",
                "generation",
                "subject",
                "window_id",
                "window_definition_id",
                "metric",
                "state",
                "burn_rate",
                "earliest_exhaustion_at",
                "latest_exhaustion_at",
                "reset_relation",
                "confidence",
                "precision",
                "uncertainty_codes",
                "reason_codes",
                "input_observation_ids",
                "input_set_digest",
                "method_id",
                "method_version",
                "generated_at",
                "valid_until",
            }
            or data["schema"] != "capacity.current.forecast.v1"
        ):
            raise ForecastSnapshotInvalidV1("capacity_forecast_snapshot_invalid")
        subject = data["subject"]
        if not isinstance(subject, list) or len(subject) != 4:
            raise ForecastSnapshotInvalidV1("capacity_forecast_snapshot_invalid")
        burn_raw = data["burn_rate"]
        burn = None
        if burn_raw is not None:
            if not isinstance(burn_raw, dict) or set(burn_raw) != {
                "estimate",
                "lower_bound",
                "upper_bound",
                "sample_count",
                "observed_span_seconds",
                "input_observation_ids",
                "time_basis",
            }:
                raise ForecastSnapshotInvalidV1("capacity_forecast_snapshot_invalid")
            span = burn_raw["observed_span_seconds"]
            if not isinstance(span, list) or len(span) != 2:
                raise ForecastSnapshotInvalidV1("capacity_forecast_snapshot_invalid")
            burn = CapacityBurnRateV1(
                _read_quantity(burn_raw["estimate"]),
                _read_quantity(burn_raw["lower_bound"]),
                _read_quantity(burn_raw["upper_bound"]),
                burn_raw["sample_count"],
                CanonicalDecimalV1(span[0], span[1]),
                tuple(OpaqueIdV1(item) for item in burn_raw["input_observation_ids"]),
                burn_raw["time_basis"],
            )
        generated_at = _timestamp(data["generated_at"])
        if generated_at is None:
            raise ForecastSnapshotInvalidV1("capacity_forecast_snapshot_invalid")
        return CapacityForecastV1(
            OpaqueIdV1(data["forecast_id"]),
            data["generation"],
            CapacitySubjectV1(
                subject[0],
                OpaqueIdV1(subject[1]),
                OpaqueIdV1(subject[2]),
                OpaqueIdV1(subject[3]),
            ),
            OpaqueIdV1(data["window_id"]),
            OpaqueIdV1(data["window_definition_id"]),
            data["metric"],
            data["state"],
            burn,
            _timestamp(data["earliest_exhaustion_at"]),
            _timestamp(data["latest_exhaustion_at"]),
            data["reset_relation"],
            data["confidence"],
            data["precision"],
            tuple(data["uncertainty_codes"]),
            tuple(data["reason_codes"]),
            tuple(OpaqueIdV1(item) for item in data["input_observation_ids"]),
            data["input_set_digest"],
            data["method_id"],
            data["method_version"],
            generated_at,
            _timestamp(data["valid_until"]),
        )
    except (TypeError, ValueError, KeyError, IndexError) as error:
        raise ForecastSnapshotInvalidV1("capacity_forecast_snapshot_invalid") from error

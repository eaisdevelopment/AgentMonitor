"""Pure operations classification over explicit immutable samples and UTC time."""

from dataclasses import replace
from datetime import datetime
from typing import Literal

from agentmonitor.contracts.common_v1 import OpaqueIdV1, QueryAvailabilityV1
from agentmonitor.contracts.operations_v1 import (
    MAX_COMPONENTS_V1,
    MAX_REASONS_V1,
    ComponentHealthResultV1,
    ComponentRegistrationV1,
    HealthStateV1,
    HealthViewV1,
    InvalidOperationsContractV1,
    LivenessViewV1,
    ReadinessStateV1,
    ReadinessViewV1,
)


def validate_manifest_v1(manifest: tuple[ComponentRegistrationV1, ...]) -> None:
    if (
        type(manifest) is not tuple
        or not 1 <= len(manifest) <= MAX_COMPONENTS_V1
        or len({item.component_key for item in manifest}) != len(manifest)
    ):
        raise InvalidOperationsContractV1("operations_manifest_invalid")


def _codes(values: set[str]) -> tuple[str, ...]:
    return tuple(sorted(values))[:MAX_REASONS_V1]


def classify_operations_health_v1(
    manifest: tuple[ComponentRegistrationV1, ...],
    results: tuple[ComponentHealthResultV1, ...],
    *,
    as_of: datetime,
    correlation_id: OpaqueIdV1,
) -> tuple[HealthViewV1, ReadinessViewV1]:
    """Preserve every manifest slot; optional failure never blocks normal readiness."""
    validate_manifest_v1(manifest)
    registered = {item.component_key: item for item in manifest}
    supplied = {item.component_key: item for item in results}
    if len(supplied) != len(results) or not supplied.keys() <= registered.keys():
        raise InvalidOperationsContractV1("operations_result_invalid")
    normalized: list[ComponentHealthResultV1] = []
    blockers: list[str] = []
    states: list[HealthStateV1] = []
    required_states: list[HealthStateV1] = []
    reason_codes: set[str] = set()
    validity: list[datetime] = []
    incomplete = False
    setup_blockers: set[str] = set()
    for key, registration in sorted(registered.items()):
        result = supplied.get(key)
        if result is None:
            result = ComponentHealthResultV1(
                key,
                "unavailable",
                None,
                as_of,
                "operations_required_component_missing"
                if registration.criticality == "required_for_normal_readiness"
                else "operations_component_unavailable",
            )
        sample = result.sample
        state: HealthStateV1 = (
            "incompatible" if result.outcome == "incompatible" else "unavailable"
        )
        if sample is not None:
            if not {item.key for item in sample.indicators} <= set(
                registration.indicator_keys
            ):
                raise InvalidOperationsContractV1("operations_indicator_invalid")
            state = sample.state
            freshness_reason: str | None = None
            if sample.checked_at > as_of or result.checked_at > as_of:
                state = "unknown"
                freshness_reason = "operations_component_future"
            elif sample.valid_until <= as_of:
                state = "unknown"
                freshness_reason = "operations_component_stale"
            if freshness_reason is not None:
                codes = tuple(dict.fromkeys((freshness_reason, *sample.reason_codes)))
                sample = replace(
                    sample, state=state, reason_codes=codes[:MAX_REASONS_V1]
                )
                result = replace(result, sample=sample, reason_code=freshness_reason)
            validity.append(sample.valid_until)
            reason_codes.update(sample.reason_codes)
            if (
                "operations_setup_required" in sample.reason_codes
                and key == "identity_access"
            ):
                setup_blockers.add(key)
        else:
            validity.append(as_of)
            incomplete = True
        reason_codes.add(result.reason_code)
        normalized.append(result)
        states.append(state)
        if state == "unknown":
            incomplete = True
        if registration.criticality == "required_for_normal_readiness":
            required_states.append(state)
            if state != "healthy":
                blockers.append(key)
    overall: HealthStateV1 = "healthy"
    for state in ("incompatible", "maintenance", "unavailable", "unknown", "degraded"):
        if state in required_states:
            overall = state
            break
    if overall == "healthy" and any(state != "healthy" for state in states):
        overall = "degraded"
    readiness: ReadinessStateV1 = "ready"
    if blockers:
        readiness = "not_ready"
        if "maintenance" in required_states:
            readiness = "maintenance"
        elif set(blockers) <= setup_blockers:
            readiness = "setup_required"
    validity_at = min(validity)
    availability_state: Literal["available", "partial", "unavailable"] = (
        "unavailable"
        if all(item.sample is None for item in normalized)
        else "partial"
        if incomplete
        else "available"
    )
    availability_code = (
        "operations_health_unavailable"
        if availability_state == "unavailable"
        else "operations_health_partial"
        if incomplete
        else "operations_health_complete"
    )
    return (
        HealthViewV1(
            overall,
            as_of,
            validity_at,
            tuple(normalized),
            QueryAvailabilityV1(availability_state, availability_code, as_of),
            _codes(reason_codes),
            correlation_id,
        ),
        ReadinessViewV1(
            readiness,
            as_of,
            validity_at,
            tuple(blockers),
            _codes(
                reason_codes
                | {
                    "operations_ready"
                    if readiness == "ready"
                    else "operations_not_ready"
                }
            ),
            correlation_id,
        ),
    )


def classify_liveness_v1(
    phase: str, as_of: datetime, correlation_id: OpaqueIdV1
) -> LivenessViewV1:
    """No clock, health leaf, authentication, file or DB access."""
    return LivenessViewV1(
        "healthy" if phase == "running" else "unavailable", as_of, correlation_id
    )

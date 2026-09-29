"""A-P02/03: pure constructed producer facts; no external-source claim."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from agentmonitor.contracts.capacity_v1 import (
    CapacityAlertAvailabilityV1,
    CapacityAlertConditionV1,
)
from agentmonitor.contracts.common_quantity_v1 import CanonicalDecimalV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import AlertSubjectScopeV1
from agentmonitor.modules.alerting.domain import policy

NOW = datetime(2026, 9, 29, 12, tzinfo=UTC)
SCOPE = AlertSubjectScopeV1(
    OpaqueIdV1("account"), "claude", OpaqueIdV1("organization"), True, 8
)


def fact(value: str = "1500") -> CapacityAlertConditionV1:
    return CapacityAlertConditionV1(
        OpaqueIdV1("resource"),
        SCOPE.account_id,
        SCOPE.provider_key,
        OpaqueIdV1("window"),
        87,
        CanonicalDecimalV1.from_decimal(Decimal(value)),
        "used_percent_complement",
        "current",
        Decimal(value) == 0,
        None,
        NOW + timedelta(minutes=10),
        (OpaqueIdV1("observation"),),
        "rounded",
        "high",
        "capacity_used_percent_current",
        NOW,
        NOW,
    )


@pytest.mark.parametrize(
    ("value", "transition", "severity"),
    [
        ("0", "active", "critical"),
        ("1500", "active", "critical"),
        ("1500.01", "active", "warning"),
        ("3000", "active", "warning"),
        ("3000.01", "recovered", None),
    ],
)
def test_exact_current_fact_uses_inclusive_threshold_and_preserves_lineage(
    value: str, transition: str, severity: str | None
) -> None:
    source = fact(value)
    actual = policy.map_capacity_alert_condition(
        source,
        SCOPE,
        OpaqueIdV1("trigger-event"),
        policy.builtin_rule("capacity_remaining"),
        as_of=NOW,
    )
    assert actual.transition == transition and actual.severity == severity
    assert actual.decision.remaining_basis_points == source.remaining_basis_points
    assert actual.decision.source.source_generation == 87
    assert actual.decision.source.event_id == OpaqueIdV1("trigger-event")
    assert actual.decision.source.observation_ids == source.observation_ids
    assert actual.decision.source.precision == source.precision
    assert actual.decision.source.reason_code == source.reason_code
    assert actual.subject.dimension_id == source.window_id.value
    assert actual.subject.organization_id == SCOPE.organization_id
    assert actual.decision.reset_at is None
    assert actual.decision.source.condition_stream_key.startswith("capacity:")
    assert len(actual.decision.source.condition_stream_key) == 73


@pytest.mark.parametrize("value", ["0", "0.01"])
def test_exhausted_condition_requires_explicit_current_boolean(value: str) -> None:
    source = fact(value)
    actual = policy.map_capacity_alert_condition(
        source,
        SCOPE,
        OpaqueIdV1("trigger-event"),
        policy.builtin_rule("capacity_exhausted"),
        as_of=NOW,
    )
    assert actual.transition == ("active" if source.exhausted else "recovered")
    assert actual.severity == ("critical" if source.exhausted else None)


@pytest.mark.parametrize("state", ["stale", "unknown", "unsupported", "unavailable"])
def test_no_value_fact_cannot_open_or_recover(
    state: CapacityAlertAvailabilityV1,
) -> None:
    source = replace(
        fact(),
        availability=state,
        remaining_basis_points=None,
        exhausted=None,
        denominator_kind="unknown",
        reason_code="capacity_reading_stale",
    )
    for condition in ("capacity_remaining", "capacity_exhausted"):
        actual = policy.map_capacity_alert_condition(
            source,
            SCOPE,
            OpaqueIdV1("trigger-event"),
            policy.builtin_rule(condition),
            as_of=NOW,
        )
        assert actual.transition == "not_evaluable"
        assert actual.severity is None
        assert actual.decision.remaining_basis_points is None
        assert actual.decision.truth_state == state


@pytest.mark.parametrize(
    "changed_scope",
    [
        replace(SCOPE, account_id=OpaqueIdV1("other")),
        replace(SCOPE, provider_key="other"),
        replace(SCOPE, eligible=False),
    ],
)
def test_wrong_or_ineligible_account_scope_is_rejected(
    changed_scope: AlertSubjectScopeV1,
) -> None:
    with pytest.raises(ValueError, match="alert_capacity_scope_conflict"):
        policy.map_capacity_alert_condition(
            fact(),
            changed_scope,
            OpaqueIdV1("trigger-event"),
            policy.builtin_rule("capacity_remaining"),
            as_of=NOW,
        )


def test_current_expired_fact_is_rejected_without_inventing_stale_generation() -> None:
    with pytest.raises(ValueError, match="alert_capacity_current_expired"):
        policy.map_capacity_alert_condition(
            fact(),
            SCOPE,
            OpaqueIdV1("trigger-event"),
            policy.builtin_rule("capacity_remaining"),
            as_of=NOW + timedelta(minutes=10),
        )

"""M4-CAP-A01: only constructed zero-I/O quota domain facts."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal

import pytest
from agentmonitor.contracts import capacity_v1 as contracts
from agentmonitor.contracts.common_quantity_v1 import ExactQuantityV1
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.modules.capacity.application import queries

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _field(
    value: str | int,
    unit: str = "ratio",
    precision: Literal["exact", "rounded"] = "rounded",
) -> Any:
    return contracts.ExactMetricFieldV1(
        FieldAvailabilityV1("available"),
        ExactQuantityV1.from_decimal(Decimal(value), unit=unit),
        precision,
        "high",
        "provider_reported",
        None,
    )


def _unknown(state: Literal["unknown", "unsupported"] = "unknown") -> Any:
    return contracts.ExactMetricFieldV1(
        FieldAvailabilityV1(state),
        None,
        "unknown",
        "unknown",
        "unknown",
        "domain_measure_absent",
    )


def _window() -> Any:
    provenance = contracts.CapacityObservationProvenanceViewV1(
        "quota",
        "1.0.0",
        "domain-adapter",
        "1.0.0",
        "1.0.0",
        "domain-source",
        "supported_cli",
        "1.0.0",
        None,
        None,
        NOW + timedelta(seconds=300),
        "domain-freshness",
        "rounded",
        "high",
        "domain-reported",
        False,
        "domain-decision",
    )
    return contracts.QuotaWindowViewV1(
        OpaqueIdV1("window"),
        contracts.CapacitySubjectV1(
            "domain-provider",
            OpaqueIdV1("installation"),
            OpaqueIdV1("account"),
            OpaqueIdV1("resource"),
        ),
        "native-window",
        None,
        _field("97", "percent"),
        _unknown(),
        _unknown(),
        _field("0.03"),
        provenance,
        "fresh",
        OpaqueIdV1("observation"),
        OpaqueIdV1("collection-run"),
        NOW,
        NOW,
        NOW,
        "session",
        True,
        1,
        None,
        "unknown",
        4,
        7,
        "complete",
    )


def _derive(window: Any = None, as_of: datetime = NOW) -> Any:
    derive = getattr(queries, "derive_capacity_alert_condition_v1", None)
    assert callable(derive), "M05 current alert fact derivation is absent"
    return derive(_window() if window is None else window, as_of=as_of)


def test_fresh_ratio_has_exact_basis_points_and_durable_generation() -> None:
    window = _window()
    fact = _derive(window)
    assert fact.generation == 7
    assert fact.remaining_basis_points.as_decimal() == Decimal("300")
    assert fact.availability == "current"
    assert fact.denominator_kind == "remaining_ratio"
    assert fact.exhausted is False
    assert fact.precision == "rounded"
    assert fact.confidence == "high"
    assert fact.observation_ids == (window.current_observation_id,)
    assert fact.recorded_at == window.stored_at


def test_exact_zero_is_available_and_exhausted() -> None:
    fact = _derive(replace(_window(), remaining_ratio=_field("0", precision="exact")))
    assert fact.remaining_basis_points.as_decimal() == 0
    assert fact.exhausted is True


@pytest.mark.parametrize(
    "changes,availability,reason",
    [
        ({"freshness": "stale"}, "stale", "capacity_reading_stale"),
        ({"freshness": "conflicted"}, "unknown", "capacity_reading_conflicted"),
        ({"freshness": "freshness_unknown"}, "unknown", "capacity_freshness_unknown"),
        ({"completeness": "partial"}, "unknown", "capacity_reading_partial"),
        (
            {"remaining_ratio": _unknown("unsupported"), "used": _unknown()},
            "unsupported",
            "capacity_ratio_unsupported",
        ),
        (
            {"remaining_ratio": _unknown(), "used": _unknown()},
            "unknown",
            "capacity_ratio_unknown",
        ),
    ],
)
def test_untrusted_condition_never_becomes_a_numeric_recovery(
    changes: dict[str, Any], availability: str, reason: str
) -> None:
    fact = _derive(replace(_window(), **changes))
    assert fact.availability == availability
    assert fact.reason_code == reason
    assert fact.remaining_basis_points is None
    assert fact.exhausted is None


def test_freshness_deadline_equality_is_stale() -> None:
    fact = _derive(as_of=NOW + timedelta(seconds=300))
    assert fact.availability == "stale"
    assert fact.remaining_basis_points is None


def test_missing_projection_version_cannot_be_replaced_by_run_generation() -> None:
    with pytest.raises(ValueError, match="capacity_projection_generation_unknown"):
        _derive(replace(_window(), projection_version=None))


def test_native_percent_complement_is_explicitly_derived() -> None:
    fact = _derive(replace(_window(), remaining_ratio=_unknown()))
    assert fact.remaining_basis_points.as_decimal() == 300
    assert fact.denominator_kind == "used_percent_complement"
    assert fact.precision == "rounded"
    assert fact.reason_code == "capacity_used_percent_current"


def test_other_native_unit_cannot_be_used_as_a_percentage_denominator() -> None:
    fact = _derive(
        replace(_window(), remaining_ratio=_unknown(), used=_field("97", "requests"))
    )
    assert fact.remaining_basis_points is None
    assert fact.denominator_kind == "unknown"


def test_nonconstraining_zero_ratio_cannot_trigger_exhaustion() -> None:
    fact = _derive(
        replace(_window(), is_constraining=False, remaining_ratio=_field("0"))
    )
    assert fact.availability != "current"
    assert fact.remaining_basis_points is None
    assert fact.exhausted is None


def test_current_nonconstraining_window_reports_not_applicable() -> None:
    fact = _derive(replace(_window(), is_constraining=False))
    assert fact.availability == "unavailable"
    assert fact.reason_code == "capacity_nonconstraining"
    assert fact.remaining_basis_points is None
    assert fact.exhausted is None


def test_stale_nonconstraining_window_cannot_prove_resolution() -> None:
    fact = _derive(replace(_window(), is_constraining=False, freshness="stale"))
    assert fact.reason_code == "capacity_reading_stale"


def test_current_nonconstraining_window_can_resolve_with_partial_scope() -> None:
    fact = _derive(replace(_window(), is_constraining=False, completeness="partial"))
    assert fact.availability == "unavailable"
    assert fact.reason_code == "capacity_nonconstraining"
    assert fact.remaining_basis_points is None
    assert fact.exhausted is None

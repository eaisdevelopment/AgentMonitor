"""M4-OPS-PURE-001..007: constructed domain inputs only, with no I/O."""

from dataclasses import fields
from datetime import UTC, datetime, timedelta
from importlib import import_module
from types import ModuleType
from typing import Any, cast

import pytest
from agentmonitor.contracts.common_v1 import (
    FieldAvailabilityV1,
    OpaqueIdV1,
    QueryAvailabilityV1,
)

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
CORRELATION = OpaqueIdV1("domain-correlation")


def contract() -> ModuleType:
    return import_module("agentmonitor.contracts.operations_v1")


def policy() -> ModuleType:
    return import_module("agentmonitor.modules.operations.domain.health")


def registration(key: str = "database", required: bool = True) -> Any:
    return contract().ComponentRegistrationV1(
        key,
        "required_for_normal_readiness" if required else "optional_degraded",
        (),
    )


def result(
    key: str = "database",
    state: str = "healthy",
    expiry: datetime | None = None,
    codes: tuple[str, ...] = (),
) -> Any:
    sample = contract().ComponentHealthSampleV1(
        key,
        "1.0.0",
        state,
        NOW - timedelta(seconds=1),
        expiry or NOW + timedelta(seconds=30),
        NOW - timedelta(seconds=2),
        codes,
        (),
    )
    return contract().ComponentHealthResultV1(
        key, "available", sample, NOW, "operations_component_healthy"
    )


def classify(manifest: tuple[Any, ...], results: tuple[Any, ...]) -> tuple[Any, Any]:
    return cast(
        tuple[Any, Any],
        policy().classify_operations_health_v1(
            manifest, results, as_of=NOW, correlation_id=CORRELATION
        ),
    )


def test_required_missing_leaf_is_preserved_and_blocks_readiness() -> None:
    health, readiness = classify((registration(),), ())
    assert readiness.state == "not_ready"
    assert readiness.blocker_component_keys == ("database",)
    assert health.components[0].component_key == "database"
    assert health.components[0].outcome == "unavailable"
    assert health.state == "unavailable"


def test_optional_failure_degrades_health_without_blocking_required_work() -> None:
    health, readiness = classify(
        (registration(), registration("provider.claude", False)),
        (result(), result("provider.claude", "degraded")),
    )
    assert health.state == "degraded"
    assert readiness.state == "ready"
    assert readiness.blocker_component_keys == ()
    assert len(health.components) == 2


@pytest.mark.parametrize(
    "state", ["degraded", "unavailable", "incompatible", "unknown"]
)
def test_nonhealthy_required_leaf_never_becomes_ready(state: str) -> None:
    _, readiness = classify((registration(),), (result(state=state),))
    assert readiness.state == "not_ready"


def test_expiry_at_as_of_is_unknown_without_extending_validity() -> None:
    health, readiness = classify((registration(),), (result(expiry=NOW),))
    assert readiness.state == "not_ready"
    assert health.components[0].sample.state == "unknown"
    assert health.components[0].reason_code == "operations_component_stale"
    assert health.valid_until == NOW
    assert "operations_component_stale" in health.reason_codes


def test_uninitialized_iam_is_setup_required_only_without_other_blockers() -> None:
    health, readiness = classify(
        (registration("identity_access"),),
        (result("identity_access", "degraded", codes=("operations_setup_required",)),),
    )
    assert readiness.state == "setup_required"
    assert health.state == "degraded"
    _, readiness = classify(
        (registration("identity_access"), registration()),
        (result("identity_access", "degraded", codes=("operations_setup_required",)),),
    )
    assert readiness.state == "not_ready"


def test_duplicate_and_unexpected_component_inputs_are_rejected() -> None:
    with pytest.raises(ValueError, match="operations_manifest_invalid"):
        classify((registration(), registration()), ())
    with pytest.raises(ValueError, match="operations_result_invalid"):
        classify((registration(),), (result("registry"),))
    with pytest.raises(ValueError, match="operations_result_invalid"):
        classify((registration(),), (result(), result()))


def test_partial_results_preserve_siblings_and_earliest_expiry() -> None:
    health, readiness = classify(
        (registration("registry"), registration(), registration("capacity", False)),
        (result("registry", expiry=NOW + timedelta(seconds=5)), result()),
    )
    assert tuple(item.component_key for item in health.components) == (
        "capacity",
        "database",
        "registry",
    )
    assert health.availability.state == "partial"
    assert readiness.state == "ready"
    # Missing evidence is immediately invalid, never a new freshness lease.
    assert health.valid_until == NOW


def test_future_sample_is_unknown_not_current() -> None:
    c = contract()
    sample = c.ComponentHealthSampleV1(
        "database",
        "1.0.0",
        "healthy",
        NOW + timedelta(seconds=1),
        NOW + timedelta(seconds=30),
        None,
        (),
        (),
    )
    health, readiness = classify(
        (registration(),),
        (
            c.ComponentHealthResultV1(
                "database", "available", sample, NOW, "operations_component_healthy"
            ),
        ),
    )
    assert health.components[0].sample.state == "unknown"
    assert health.components[0].reason_code == "operations_component_future"
    assert readiness.state == "not_ready"


def test_unknown_reason_indicator_and_invalid_tag_are_rejected() -> None:
    c = contract()
    with pytest.raises(ValueError, match="operations_reason_invalid"):
        result(codes=("an_account_email_or_path",))
    with pytest.raises(ValueError, match="operations_indicator_invalid"):
        c.ComponentIndicatorV1(
            "account_id", 1, "count", FieldAvailabilityV1("available")
        )
    with pytest.raises(ValueError, match="operations_result_invalid"):
        c.ComponentHealthResultV1(
            "database", "available", None, NOW, "operations_component_unavailable"
        )
    with pytest.raises(ValueError, match="operations_indicator_invalid"):
        c.ComponentIndicatorV1(
            "running_count", True, "count", FieldAvailabilityV1("available")
        )


def test_configuration_presence_excludes_values_and_unregistered_names() -> None:
    c = contract()
    assert {field.name for field in fields(c.ConfigurationPresenceV1)} == {
        "key",
        "owner",
        "presence",
    }
    with pytest.raises(ValueError, match="operations_configuration_invalid"):
        c.ConfigurationPresenceV1("TOKEN_WITH_SENSITIVE_VALUE", "M01", "configured")
    with pytest.raises(ValueError, match="operations_version_invalid"):
        c.VersionValueV1(
            "/home/owner/private", FieldAvailabilityV1("available"), "build_manifest"
        )


def test_missing_versions_remain_unknown_and_available_requires_a_value() -> None:
    c = contract()
    value = c.VersionValueV1(None, FieldAvailabilityV1("unknown"), "schema_port")
    assert value.value is None
    assert value.availability.state == "unknown"
    with pytest.raises(ValueError, match="operations_version_invalid"):
        c.VersionValueV1(None, FieldAvailabilityV1("available"), "schema_port")
    with pytest.raises(ValueError, match="operations_version_invalid"):
        c.VersionValueV1("1.0.0", FieldAvailabilityV1("unknown"), "build_manifest")


def test_query_budget_and_component_result_bounds_are_enforced() -> None:
    c = contract()
    with pytest.raises(ValueError, match="operations_deadline_invalid"):
        c.OperationsQueryRequestV1(
            NOW, NOW + timedelta(milliseconds=2001), CORRELATION, "administrator"
        )
    with pytest.raises(ValueError, match="operations_deadline_invalid"):
        c.OperationsQueryRequestV1(NOW, NOW, CORRELATION, "administrator")
    with pytest.raises(ValueError, match="operations_reason_invalid"):
        result(codes=("operations_component_healthy",) * 9)


def test_liveness_is_pure_and_does_not_imply_readiness() -> None:
    assert policy().classify_liveness_v1("running", NOW, CORRELATION).state == "healthy"
    assert (
        policy().classify_liveness_v1("stopped", NOW, CORRELATION).state
        == "unavailable"
    )


def test_available_export_declaration_requires_real_safety_receipts() -> None:
    c = contract()
    with pytest.raises(ValueError, match="operations_artifact_invalid"):
        c.ExportJobViewV1(
            OpaqueIdV1("domain-job"),
            None,
            "owner_requested",
            "agentmonitor-ndjson-v1",
            1,
            "available",
            NOW,
            NOW,
            NOW + timedelta(days=1),
            None,
            None,
            None,
            "not_scanned",
            True,
            "operations_ready",
        )


def test_diagnostic_summary_fields_are_a_closed_allowlist() -> None:
    assert {field.name for field in fields(contract().DiagnosticSummaryV1)} == {
        "versions",
        "health",
        "readiness",
        "configuration_presence",
        "generated_at",
        "valid_until",
        "availability",
        "reason_codes",
        "correlation_id",
    }
    assert (
        QueryAvailabilityV1("partial", "operations_health_partial", NOW).state
        == "partial"
    )


def test_dashboard_overview_keeps_unavailable_sections_null() -> None:
    c = contract()
    unavailable = QueryAvailabilityV1(
        "unknown", "operations_component_unavailable", NOW
    )
    view = c.DashboardOverviewV1(
        "global",
        None,
        NOW,
        None,
        None,
        None,
        None,
        None,
        None,
        unavailable,
        unavailable,
        unavailable,
        unavailable,
        unavailable,
        unavailable,
        unavailable,
        CORRELATION,
    )
    assert view.alerts is None
    assert view.capacity is None
    with pytest.raises(ValueError, match="operations_overview_invalid"):
        c.DashboardOverviewV1(
            "global",
            None,
            NOW,
            None,
            None,
            None,
            None,
            None,
            None,
            QueryAvailabilityV1("available", "operations_health_complete", NOW),
            unavailable,
            unavailable,
            unavailable,
            unavailable,
            unavailable,
            unavailable,
            CORRELATION,
        )

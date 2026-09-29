"""M05 pure exact-value and health evidence; examples perform no I/O."""

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from agentmonitor.contracts.capacity_v1 import (
    CapacityHealthPolicyV1,
    CapacityObservationProvenanceViewV1,
    CapacitySubjectV1,
    ExactMetricFieldV1,
    InvalidCapacityContractV1,
    ProviderQuotaInputV1,
    ProviderQuotaWindowInputV1,
    QuotaWindowViewV1,
)
from agentmonitor.contracts.common_quantity_v1 import (
    CanonicalDecimalV1,
    ExactQuantityV1,
    InvalidExactQuantityV1,
)
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.modules.capacity.application.commit import (
    CapacityCommitValidationErrorV1,
    validate_capacity_payload_digest,
)
from agentmonitor.modules.capacity.domain.health import (
    CapacityConstraintInputV1,
    classify_capacity_health,
    classify_capacity_windows_v1,
    default_capacity_health_policy_v1,
)
from agentmonitor.modules.capacity.domain.payload_digest import (
    capacity_payload_digest,
)


def test_exact_quantity_is_canonical_and_binary_float_is_rejected() -> None:
    """M05-PURE-053..055: exact values never accept binary floating point."""
    value = ExactQuantityV1.from_decimal(Decimal("001.2300"), unit="percent")

    assert value.amount == CanonicalDecimalV1(coefficient="123", scale=2)
    assert value.as_decimal() == Decimal("1.23")

    try:
        ExactQuantityV1.from_decimal(1.23, unit="percent")  # type: ignore[arg-type]
    except InvalidExactQuantityV1 as error:
        assert error.code == "exact_decimal_required"
    else:
        raise AssertionError("binary float was accepted")

    try:
        CanonicalDecimalV1.from_decimal(Decimal("1E+1000000"))
    except InvalidExactQuantityV1 as error:
        assert error.code == "exact_decimal_coefficient_too_large"
    else:
        raise AssertionError("oversized positive exponent was expanded")


def test_metric_field_distinguishes_zero_from_unknown() -> None:
    """M05-PURE-009: exact zero is a value and absence remains explicit."""
    zero = ExactMetricFieldV1(
        availability=FieldAvailabilityV1("available"),
        value=ExactQuantityV1.from_decimal(Decimal("0"), unit="ratio"),
        precision="exact",
        confidence="confirmed",
        value_kind="provider_reported",
        reason_code=None,
    )
    unknown = ExactMetricFieldV1(
        availability=FieldAvailabilityV1("unknown"),
        value=None,
        precision="unknown",
        confidence="unknown",
        value_kind="unknown",
        reason_code="source_value_unknown",
    )

    assert zero.value is not None and zero.value.as_decimal() == Decimal("0")
    assert unknown.value is None
    assert zero != unknown


def test_collection_unavailability_is_not_accepted_as_a_metric_field_state() -> None:
    """M05-PURE-009: unavailable is a run condition, never a numeric field."""
    try:
        ExactMetricFieldV1(
            availability=FieldAvailabilityV1("unavailable"),
            value=None,
            precision="unknown",
            confidence="unknown",
            value_kind="unknown",
            reason_code="collection_unavailable",
        )
    except InvalidCapacityContractV1 as error:
        assert error.code == "capacity_field_availability_invalid"
    else:
        raise AssertionError("collection unavailability was accepted as a field")


def _available(value: str, unit: str) -> ExactMetricFieldV1:
    return ExactMetricFieldV1(
        availability=FieldAvailabilityV1("available"),
        value=ExactQuantityV1.from_decimal(Decimal(value), unit=unit),
        precision="exact",
        confidence="confirmed",
        value_kind="provider_reported",
        reason_code=None,
    )


def _unknown() -> ExactMetricFieldV1:
    return ExactMetricFieldV1(
        availability=FieldAvailabilityV1("unknown"),
        value=None,
        precision="unknown",
        confidence="unknown",
        value_kind="unknown",
        reason_code="source_value_unknown",
    )


def _window(
    key: str, *, used: str = "1", remaining_unit: str = "percent"
) -> ProviderQuotaWindowInputV1:
    return ProviderQuotaWindowInputV1(
        window_key=key,
        safe_label=None,
        semantic_role="native_window",
        is_constraining=True,
        used=_available(used, "percent"),
        remaining=_available("2", remaining_unit),
        limit=_available("3", "percent"),
        remaining_ratio=_unknown(),
        reset_at=None,
        reset_precision="unknown",
    )


def test_quota_windows_reject_negative_incompatible_and_unbounded_inputs() -> None:
    """M05-PURE-001/004/056: native fields are bounded and unit-compatible."""
    factories: tuple[Callable[[], ProviderQuotaWindowInputV1], ...] = (
        lambda: _window("negative", used="-1"),
        lambda: _window("mixed-units", remaining_unit="tokens"),
    )
    for factory in factories:
        try:
            invalid = factory()
            ProviderQuotaInputV1(
                subject=CapacitySubjectV1(
                    provider_key="claude",
                    installation_id=OpaqueIdV1("installation-one"),
                    account_id=OpaqueIdV1("account-one"),
                    resource_id=OpaqueIdV1("resource-one"),
                ),
                registry_revision=1,
                capability_schema_version="1.0",
                completeness="complete_scope",
                windows=(invalid,),
            )
        except InvalidCapacityContractV1:
            pass
        else:
            raise AssertionError("invalid quota window was accepted")

    try:
        ProviderQuotaInputV1(
            subject=CapacitySubjectV1(
                provider_key="claude",
                installation_id=OpaqueIdV1("installation-one"),
                account_id=OpaqueIdV1("account-one"),
                resource_id=OpaqueIdV1("resource-one"),
            ),
            registry_revision=1,
            capability_schema_version="1.0",
            completeness="complete_scope",
            windows=tuple(_window(f"window-{index}") for index in range(33)),
        )
    except InvalidCapacityContractV1 as error:
        assert error.code == "capacity_quota_batch_invalid"
    else:
        raise AssertionError("unbounded quota batch was accepted")


def test_capacity_payload_digest_is_canonical_and_value_sensitive() -> None:
    """M05-PURE-008: idempotency compares a recomputed canonical payload."""
    subject = CapacitySubjectV1(
        provider_key="claude",
        installation_id=OpaqueIdV1("installation-one"),
        account_id=OpaqueIdV1("account-one"),
        resource_id=OpaqueIdV1("resource-one"),
    )
    first = ProviderQuotaInputV1(
        subject=subject,
        registry_revision=1,
        capability_schema_version="1.0",
        completeness="complete_scope",
        windows=(_window("current-session", used="1"),),
    )
    changed = ProviderQuotaInputV1(
        subject=subject,
        registry_revision=1,
        capability_schema_version="1.0",
        completeness="complete_scope",
        windows=(_window("current-session", used="2"),),
    )

    assert capacity_payload_digest(first) == capacity_payload_digest(first)
    assert capacity_payload_digest(first) != capacity_payload_digest(changed)

    reordered = ProviderQuotaInputV1(
        subject=subject,
        registry_revision=1,
        capability_schema_version="1.0",
        completeness="complete_scope",
        windows=(
            _window("weekly", used="2"),
            _window("current-session", used="1"),
        ),
    )
    ordered = ProviderQuotaInputV1(
        subject=subject,
        registry_revision=1,
        capability_schema_version="1.0",
        completeness="complete_scope",
        windows=(
            _window("current-session", used="1"),
            _window("weekly", used="2"),
        ),
    )
    assert capacity_payload_digest(reordered) == capacity_payload_digest(ordered)

    try:
        validate_capacity_payload_digest(first, capacity_payload_digest(changed))
    except CapacityCommitValidationErrorV1 as error:
        assert error.code == "capacity_payload_digest_mismatch"
    else:
        raise AssertionError("mismatched caller payload digest was accepted")


def test_partial_quota_scope_requires_explicit_omission_codes() -> None:
    """M05-PURE-006: partial never silently means complete native scope."""
    try:
        ProviderQuotaInputV1(
            subject=CapacitySubjectV1(
                provider_key="claude",
                installation_id=OpaqueIdV1("installation-one"),
                account_id=OpaqueIdV1("account-one"),
                resource_id=OpaqueIdV1("resource-one"),
            ),
            registry_revision=1,
            capability_schema_version="1.0",
            completeness="partial_scope",
            windows=(_window("current-session"),),
        )
    except InvalidCapacityContractV1 as error:
        assert error.code == "capacity_partial_omissions_required"
    else:
        raise AssertionError("partial capacity scope omitted no explicit reason")


def test_capacity_health_preserves_partial_and_unknown_semantics() -> None:
    """M05-PURE-014..019/021: explicit policy drives deterministic health."""
    policy = CapacityHealthPolicyV1(
        policy_id="capacity-health-test-policy",
        policy_version="1.0.0",
        constrained_remaining_ratio=CanonicalDecimalV1("3", 1),
        critical_remaining_ratio=CanonicalDecimalV1("15", 2),
    )
    critical = CapacityConstraintInputV1(
        window_id="window-critical",
        remaining_ratio=CanonicalDecimalV1("1", 1),
        freshness="fresh",
        is_constraining=True,
    )
    unknown = CapacityConstraintInputV1(
        window_id="window-unknown",
        remaining_ratio=None,
        freshness="freshness_unknown",
        is_constraining=True,
    )

    partial = classify_capacity_health((critical, unknown), policy=policy)
    assert partial.state == "critical"
    assert partial.completeness == "partial"
    assert partial.constraining_window_id == "window-critical"

    available = CapacityConstraintInputV1(
        window_id="window-available",
        remaining_ratio=CanonicalDecimalV1("8", 1),
        freshness="fresh",
        is_constraining=True,
    )
    unresolved = classify_capacity_health((available, unknown), policy=policy)
    assert unresolved.state == "unknown"
    assert unresolved.completeness == "partial"


def test_capacity_health_auth_and_exhausted_precedence_is_explicit() -> None:
    """M05-PURE-014/016: auth and exact exhaustion cannot appear available."""
    policy = CapacityHealthPolicyV1(
        policy_id="capacity-health-test-policy",
        policy_version="1.0.0",
        constrained_remaining_ratio=CanonicalDecimalV1("3", 1),
        critical_remaining_ratio=CanonicalDecimalV1("15", 2),
    )
    exhausted = CapacityConstraintInputV1(
        window_id="window-exhausted",
        remaining_ratio=CanonicalDecimalV1("0", 0),
        freshness="fresh",
        is_constraining=True,
    )

    result = classify_capacity_health((exhausted,), policy=policy)
    assert result.state == "exhausted"
    assert result.constraining_window_id == "window-exhausted"

    auth = classify_capacity_health(
        (exhausted,),
        policy=policy,
        is_reauthentication_required=True,
    )
    assert auth.state == "reauthentication_required"
    assert auth.constraining_window_id is None


def _quota_view() -> QuotaWindowViewV1:
    now = datetime(2026, 9, 24, 12, tzinfo=UTC)
    return QuotaWindowViewV1(
        window_id=OpaqueIdV1("window-view"),
        subject=CapacitySubjectV1(
            "claude",
            OpaqueIdV1("installation-one"),
            OpaqueIdV1("account-one"),
            OpaqueIdV1("resource-one"),
        ),
        window_key="current-session",
        safe_label=None,
        used=_available("20", "percent"),
        remaining=_unknown(),
        limit=_unknown(),
        remaining_ratio=_available("0.8", "ratio"),
        provenance=CapacityObservationProvenanceViewV1(
            "quota",
            "1.0.0",
            "capacity-test-adapter",
            "1.0.0",
            "1.0.0",
            "capacity-test-source",
            "supported_cli",
            "1.0.0",
            None,
            None,
            now + timedelta(minutes=5),
            "capacity-test-freshness",
            "rounded",
            "high",
            "capacity-test-report",
            False,
            "capacity-test-decision",
        ),
        freshness="fresh",
        current_observation_id=OpaqueIdV1("observation-one"),
        collection_run_id=OpaqueIdV1("run-one"),
        observed_at=now,
        collected_at=now,
        stored_at=now,
        is_constraining=True,
        completeness="complete",
    )


def test_default_capacity_health_policy_has_exact_admitted_thresholds() -> None:
    policy = default_capacity_health_policy_v1()
    assert policy.policy_id == "capacity-health-default-v1"
    assert policy.policy_version == "1.0.0"
    assert policy.constrained_remaining_ratio.as_decimal() == Decimal("0.30")
    assert policy.critical_remaining_ratio.as_decimal() == Decimal("0.15")


def test_quota_window_health_uses_exact_remaining_and_used_fallback() -> None:
    policy = default_capacity_health_policy_v1()
    available = _quota_view()
    result = classify_capacity_windows_v1((available,), policy=policy)
    assert (result.state, result.completeness, result.freshness) == (
        "available",
        "complete",
        "fresh",
    )
    assert result.constraining_window_id == "window-view"
    used_fallback = replace(
        available,
        used=_available("90", "percent"),
        remaining_ratio=_unknown(),
    )
    result = classify_capacity_windows_v1((used_fallback,), policy=policy)
    assert (result.state, result.constraining_window_id) == ("critical", "window-view")
    exhausted = replace(available, remaining_ratio=_available("0", "ratio"))
    assert (
        classify_capacity_windows_v1((exhausted,), policy=policy).state == "exhausted"
    )


def test_quota_window_health_does_not_invent_missing_constraints() -> None:
    policy = default_capacity_health_policy_v1()
    available = _quota_view()
    missing = replace(available, used=_unknown(), remaining_ratio=_unknown())
    unknown = classify_capacity_windows_v1((missing,), policy=policy)
    assert (unknown.state, unknown.completeness, unknown.freshness) == (
        "unknown",
        "partial",
        "freshness_unknown",
    )
    ignored = replace(available, is_constraining=False)
    assert classify_capacity_windows_v1((ignored,), policy=policy).state == "unknown"
    undecided = replace(available, is_constraining=None)
    assert classify_capacity_windows_v1((undecided,), policy=policy).state == "unknown"
    stale = replace(available, freshness="stale")
    assert classify_capacity_windows_v1((stale,), policy=policy).freshness == "stale"
    unobserved = replace(available, freshness="no_observation")
    assert (
        classify_capacity_windows_v1((unobserved,), policy=policy).freshness
        == "freshness_unknown"
    )


def test_quota_window_health_preserves_incomplete_and_reauth_precedence() -> None:
    policy = default_capacity_health_policy_v1()
    available = _quota_view()
    incomplete = replace(available, completeness="partial")
    result = classify_capacity_windows_v1((incomplete,), policy=policy)
    assert (result.state, result.completeness, result.explanation_codes) == (
        "unknown",
        "partial",
        ("incomplete_constraints",),
    )
    critical = replace(
        incomplete,
        remaining_ratio=_available("0.1", "ratio"),
    )
    result = classify_capacity_windows_v1((critical,), policy=policy)
    assert (result.state, result.completeness) == ("critical", "partial")
    reauth = classify_capacity_windows_v1(
        (critical,), policy=policy, is_reauthentication_required=True
    )
    assert (reauth.state, reauth.completeness) == (
        "reauthentication_required",
        "unknown",
    )

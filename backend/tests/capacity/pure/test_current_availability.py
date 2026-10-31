"""I04 capability truth is pure; constructed values never cross I/O."""

from agentmonitor.modules.capacity.domain import current_projection


def test_identity_binding_is_required_even_for_fresh_complete_native_value() -> None:
    classify = getattr(current_projection, "classify_capability_availability_v1", None)
    assert callable(classify), "capability availability classifier is absent"
    assert classify("fresh", "complete", "available", identity_bound=False) == (
        "unknown",
        "identity_binding_unproven",
    )
    assert classify("fresh", "complete", "available", identity_bound=True) == (
        "available",
        "capability_observed_current",
    )


def test_stale_and_partial_evidence_cannot_prove_recovery() -> None:
    classify = current_projection.classify_capability_availability_v1
    assert classify("stale", "complete", "available", identity_bound=True) == (
        "stale",
        "capability_reading_stale",
    )
    assert classify("fresh", "partial", "available", identity_bound=True) == (
        "unknown",
        "capability_reading_partial",
    )

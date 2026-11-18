"""Pure fixed selection of mandatory retention and installed proof boundaries."""

import pytest

from tools.automation.implementations import auto_m7

LIVE = "backend/tests/live/ollama/test_budget_retention_live.py::"
MANDATORY = (
    "backend/tests/integration/capacity/test_budget_retention_boundary.py",
    "backend/tests/integration/collection_control/test_budget_retention_guard.py",
    "backend/tests/integration/operations/test_budget_retention_checkpoint.py",
    "backend/tests/integration/operations/test_budget_retention_task.py",
    "backend/tests/integration/registry/test_billing_retention_scope.py",
    LIVE + "test_genuine_retention_preserves_receipt_and_checkpoint",
    LIVE + "test_genuine_monetary_bundle_expires_with_original_receipt",
    LIVE + "test_changed_checkpoint_cannot_purge_genuine_facts",
    LIVE
    + "test_real_latest_contexts_survive_without_preserving_every_historical_window",
    LIVE + "test_unknown_project_metadata_cannot_be_dropped_by_retention",
    LIVE + "test_new_genuine_fact_reference_invalidates_preview_before_purge[current]",
    LIVE
    + "test_new_genuine_fact_reference_invalidates_preview_before_purge[derivation]",
)


def test_retention_persistence_requires_all_available_mechanics() -> None:
    assert set(MANDATORY) <= set(auto_m7.TECHNICAL_BOUNDARY_TARGETS["persistence"])


def test_retention_pure_and_compatibility_boundaries_are_required() -> None:
    assert {
        "backend/tests/capacity/pure/test_budget_retention.py",
        "backend/tests/capacity/pure/test_budget_retention_codec.py",
        "backend/tests/contracts/test_budget_retention_contract.py",
    } <= set(auto_m7.PURE_TARGETS)
    assert (
        "backend/tests/persistence/sqlite/migrations/test_m05_budget_retention.py"
        in auto_m7.TECHNICAL_BOUNDARY_TARGETS["compatibility"]
    )


def test_configured_inventory_uses_real_all_provider_inventory() -> None:
    assert auto_m7.CONFIGURED_INVENTORY_TARGETS == (
        "backend/tests/live/test_m7_configured_inventory.py",
    )
    auto_m7.validate_selection("live", "configured_inventory", None)
    with pytest.raises(ValueError, match="m7_selection_invalid"):
        auto_m7.validate_selection("technical", "configured_inventory", None)


@pytest.mark.parametrize("check", ["registry_http", "persistence", "compatibility"])
def test_bounded_batches_preserve_every_required_case_exactly_once(check: str) -> None:
    batches = auto_m7.technical_target_batches(check)
    flattened = tuple(target for _, targets in batches for target in targets)
    assert len(flattened) == len(set(flattened))
    assert set(flattened) == set(auto_m7.TECHNICAL_BOUNDARY_TARGETS[check])
    assert all(targets for _, targets in batches)
    for _, targets in batches:
        if any(target.startswith(LIVE) for target in targets):
            assert len(targets) == 1


def test_installed_retention_proof_is_explicit_read_only_live_selection() -> None:
    auto_m7.validate_selection("live", "retention_invocation", None)
    with pytest.raises(ValueError, match="m7_selection_invalid"):
        auto_m7.validate_selection("deploy", "retention_invocation", None)
    assert auto_m7.RETENTION_INVOCATION_TARGETS == (
        "backend/tests/live/test_m7_retention_invocation.py",
    )


def test_live_aggregate_cannot_pass_without_installed_retention_invocation() -> None:
    checks = tuple(
        auto_m7.CheckResult(name, "passed")
        for name in auto_m7.REQUIRED_CHECKS["live"]
        if name != "retention_invocation"
    )
    assert auto_m7.evaluate_lane("live", checks).status == "blocked"

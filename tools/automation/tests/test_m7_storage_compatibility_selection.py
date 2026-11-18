"""Pure exact M7 boundary selection; no fabricated execution outcomes or I/O."""

import pytest

from tools.automation.implementations import auto_m7


@pytest.mark.parametrize("check", ["registry_http", "persistence", "compatibility"])
def test_storage_checks_are_explicit_technical_selections(check: str) -> None:
    auto_m7.validate_selection("technical", check, None)


@pytest.mark.parametrize("check", ["registry_http", "persistence", "compatibility"])
@pytest.mark.parametrize(
    "lane",
    [
        "pure",
        "registry_metadata",
        "persistence_schema",
        "live",
        "browser",
        "deploy",
        "exit",
    ],
)
def test_storage_checks_cannot_cross_lanes(lane: str, check: str) -> None:
    with pytest.raises(ValueError, match="m7_selection_invalid"):
        auto_m7.validate_selection(lane, check, None)


@pytest.mark.parametrize("check", ["registry_http", "persistence", "compatibility"])
def test_storage_checks_cannot_claim_revision_activation(check: str) -> None:
    with pytest.raises(ValueError, match="m7_selection_invalid"):
        auto_m7.validate_selection("technical", check, "a" * 40)


def test_registry_http_targets_include_actual_owner_and_authority_boundaries() -> None:
    assert auto_m7.TECHNICAL_BOUNDARY_TARGETS["registry_http"] == (
        "backend/tests/integration/api/test_financial_pools_http.py",
        "backend/tests/integration/api/test_billing_enrollment_http.py",
        "backend/tests/integration/api/test_billing_reconnect_http.py",
        "backend/tests/integration/api/test_billing_monitoring_http.py",
        "backend/tests/integration/api/test_billing_actions_http.py",
    )


def test_persistence_targets_require_real_retained_money_and_storage_guards() -> None:
    targets = auto_m7.TECHNICAL_BOUNDARY_TARGETS["persistence"]
    assert len(targets) == len(set(targets))
    assert {
        "backend/tests/integration/capacity/test_budget_report_schema.py",
        "backend/tests/integration/collection_control/test_budget_run_schema.py",
        "backend/tests/integration/capacity/test_budget_repository_empty.py",
        "backend/tests/integration/capacity/test_budget_funds_empty.py",
        "backend/tests/integration/capacity/test_budget_current_empty.py",
        "backend/tests/integration/capacity/test_budget_account_empty.py",
        "backend/tests/live/ollama/test_budget_monetary_persistence.py",
        "backend/tests/live/ollama/test_model_report_persistence.py",
        "backend/tests/live/ollama/test_budget_source_evidence.py",
        "backend/tests/live/ollama/test_budget_daily_history_live.py",
        "backend/tests/live/ollama/test_budget_overview_history_snapshot.py",
    } <= set(targets)
    assert all("interrupted_receipt" not in target for target in targets)


def test_compatibility_has_legacy_v2_guards_and_three_bounded_update_cases() -> None:
    targets = auto_m7.TECHNICAL_BOUNDARY_TARGETS["compatibility"]
    assert {
        "backend/tests/integration/capacity/test_capacity_schema_chain.py",
        "backend/tests/integration/capacity/test_budget_report_schema.py",
        "backend/tests/integration/api/test_billing_actions_http.py",
        "backend/tests/persistence/sqlite/migrations/test_m05_model_remainder.py",
        "backend/tests/live/ollama/test_model_remainder_migration.py",
        "backend/tests/integration/persistence/test_auto_migrate.py"
        "::test_auto_migrate_retention_preserves_schema_and_verified_backup",
    } <= set(targets)
    update = "tools/automation/tests/test_m6_same_schema_update.py"
    assert {target for target in targets if target.startswith(update)} == {
        update + "::test_real_same_schema_dashboard_update_and_finalization[False]",
        update + "::test_real_same_schema_dashboard_update_and_finalization[True]",
        update + "::test_real_same_schema_dashboard_update_and_finalization[candidate]",
    }
    assert len(targets) == len(set(targets)) == 11


def test_model_grouping_pure_boundaries_remain_in_canonical_selection() -> None:
    assert {
        "backend/tests/capacity/pure/test_budget_remainder.py",
        "backend/tests/api/pure/test_cloud_model_wire.py",
        "backend/tests/adapters/providers/ollama/api/test_ollama_model_groups.py",
    } <= set(auto_m7.PURE_TARGETS)


def test_new_technical_boundaries_do_not_complete_other_checks_or_lanes() -> None:
    names = ("registry_http", "persistence", "compatibility")
    assert set(auto_m7.TECHNICAL_BOUNDARY_TARGETS) == set(names)
    partial = tuple(auto_m7.CheckResult(name, "passed") for name in names)
    assert auto_m7.evaluate_lane("technical", partial).status == "blocked"
    missing_collection = tuple(
        auto_m7.CheckResult(name, "not_run" if name == "collection" else "passed")
        for name in auto_m7.REQUIRED_CHECKS["technical"]
    )
    assert auto_m7.evaluate_lane("technical", missing_collection).status == "blocked"
    statuses: tuple[auto_m7.Status, ...] = ("not_run", "blocked", "failed")
    for status in statuses:
        checks = tuple(
            auto_m7.CheckResult(name, status if name == "persistence" else "passed")
            for name in auto_m7.REQUIRED_CHECKS["technical"]
        )
        assert auto_m7.evaluate_lane("technical", checks).status == (
            "failed" if status == "failed" else "blocked"
        )


def test_collection_guards_execute_persisted_dispatch_fairness() -> None:
    module = (
        "backend/tests/integration/collection_control/"
        "test_budget_dispatch_snapshot_real_metadata.py"
    )
    selected = tuple(
        target
        for target in auto_m7.COLLECTION_GUARD_TARGETS
        if target.partition("::")[0] == module
    )
    assert selected == (
        module
        + "::test_real_snapshot_selects_exact_later_run_and_updates_only_its_service_age",
        module
        + "::test_real_dispatch_service_age_survives_reopen_expiry_and_budget_refusal",
    )

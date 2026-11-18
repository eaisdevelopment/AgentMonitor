"""Pure aggregate selection and result reduction; no execution is simulated."""

import pytest

from tools.automation.implementations import auto_m7


def test_history_selection_includes_populated_model_browser_and_real_recovery() -> None:
    targets = getattr(auto_m7, "SOURCE_HISTORY_TARGETS", ())
    assert "backend/tests/live/ollama/test_model_history_browser.py" in targets
    assert (
        "backend/tests/live/ollama/test_budget_history_recovery_browser.py" in targets
    )


@pytest.mark.parametrize("lane", ["browser", "deploy", "exit"])
def test_aggregate_accepts_explicit_exact_installed_revision(lane: str) -> None:
    auto_m7.validate_selection(lane, None, "a" * 40)


@pytest.mark.parametrize("lane", ["browser", "deploy", "exit"])
@pytest.mark.parametrize("revision", ["short", "A" * 40, "a" * 39, "a" * 41])
def test_aggregate_rejects_invalid_revision(lane: str, revision: str) -> None:
    with pytest.raises(ValueError, match="m7_selection_invalid"):
        auto_m7.validate_selection(lane, None, revision)


@pytest.mark.parametrize("lane", ["technical", "pure"])
def test_aggregate_revision_does_not_authorize_other_operations(lane: str) -> None:
    with pytest.raises(ValueError, match="m7_selection_invalid"):
        auto_m7.validate_selection(lane, None, "a" * 40)


@pytest.mark.parametrize(
    "check", ["setup_activation", "financial_activation", "model_activation"]
)
def test_deployment_activation_selection_remains_unchanged(check: str) -> None:
    auto_m7.validate_selection("deploy", check, "a" * 40)
    with pytest.raises(ValueError, match="m7_selection_invalid"):
        auto_m7.validate_selection("browser", check, "a" * 40)


def test_overview_uses_complete_executor_status_not_metadata_child() -> None:
    result = auto_m7.LaneResult(
        "browser/overview",
        "failed",
        (
            auto_m7.CheckResult("overview_metadata", "passed"),
            auto_m7.CheckResult("monetary_journey", "failed", "actual_check_failure"),
        ),
    )
    assert auto_m7.required_boundary_check("overview", result) == auto_m7.CheckResult(
        "overview", "failed", "actual_check_failure"
    )


def test_complete_overview_result_can_satisfy_only_its_named_boundary() -> None:
    result = auto_m7.LaneResult(
        "browser/overview", "passed", (auto_m7.CheckResult("overview", "passed"),)
    )
    check = auto_m7.required_boundary_check("overview", result)
    assert check == auto_m7.CheckResult("overview", "passed")
    assert auto_m7.evaluate_lane("browser", (check,)).status == "blocked"


@pytest.mark.parametrize(
    "name,reason",
    [
        (
            "detail_history",
            "m7_populated_provider_dimension_history_browser_required",
        ),
        ("collection", "m7_current_scheduling_lifecycle_evidence_required"),
    ],
)
def test_passed_partial_proof_preserves_named_unmet_scope(
    name: str, reason: str
) -> None:
    result = auto_m7.LaneResult(
        "partial", "passed", (auto_m7.CheckResult("actual_partial_boundary", "passed"),)
    )
    assert auto_m7.required_boundary_check(name, result, reason) == auto_m7.CheckResult(
        name, "not_run", reason
    )


@pytest.mark.parametrize("status", ["failed", "blocked", "not_run"])
def test_unmet_scope_cannot_hide_real_nonpass(status: auto_m7.Status) -> None:
    result = auto_m7.LaneResult(
        "partial", status, (auto_m7.CheckResult("proof", status, "actual_reason"),)
    )
    assert auto_m7.required_boundary_check(
        "detail_history", result, "remaining_requirement"
    ) == auto_m7.CheckResult("detail_history", status, "actual_reason")


def test_owner_setup_keeps_real_transport_loss_recovery_boundary() -> None:
    assert getattr(auto_m7, "OWNER_SETUP_RECOVERY_TARGETS", ()) == (
        "backend/tests/integration/api/test_billing_setup_network_recovery.py",
    )


def test_strict_setup_witness_is_current_state_not_rotation_or_removal() -> None:
    payload: dict[str, object] = {
        "record_type": "agentmonitor.m7_installed_setup_probe.v1",
        "status": "passed",
        "reason_code": "installed_owner_setup_verified",
        "source_revision": "a" * 40,
        "expected_revision": "a" * 40,
        "unsafe_requests": 0,
        "evidence_scope": "current_verified_billing_state",
        "resources_verified": 1,
        "physical_rotation_removal": "not_verified",
        "check_click_provenance": "not_verified",
        "checks": {
            name: "passed"
            for name in (
                "authentication",
                "revision",
                "overview",
                "setup_form",
                "account_layout",
                "scope_contract",
                "continuity",
                "read_only",
                "credential_stored",
                "connection_verified",
                "monitoring_enabled",
                "retained_report",
            )
        },
    }
    assert auto_m7.owner_setup_probe_result(0, payload, "a" * 40).status == "passed"
    for key, value in (
        ("resources_verified", 0),
        ("source_revision", "b" * 40),
        ("reason_code", "installed_setup_surface_verified"),
        ("unsafe_requests", 1),
    ):
        assert (
            auto_m7.owner_setup_probe_result(0, payload | {key: value}, "a" * 40).status
            == "failed"
        )
    blocked = payload | {
        "status": "blocked",
        "source_revision": None,
        "reason_code": "authentication_required",
    }
    assert auto_m7.owner_setup_probe_result(3, blocked, "a" * 40).status == "blocked"

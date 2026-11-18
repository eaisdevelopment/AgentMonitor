"""First-provider scheduling selection cannot accept absent browser/live proof."""

from tools.automation.implementations import auto_m7


def test_current_scheduling_targets_require_real_installed_lineage() -> None:
    targets = getattr(auto_m7, "SCHEDULED_COLLECTION_TARGETS", ())
    assert targets == (
        "backend/tests/live/ollama/test_m7_scheduled_collection_lifecycle.py",
    )
    assert (
        "tools/automation/tests/test_m7_collection_selection.py" in auto_m7.PURE_TARGETS
    )


def test_retained_scheduling_cannot_accept_unobserved_browser_closure() -> None:
    retained = auto_m7.LaneResult(
        "current_scheduling",
        "passed",
        (auto_m7.CheckResult("current_scheduling", "passed"),),
    )
    actual = auto_m7.required_boundary_check(
        "collection", retained, "m7_browser_closed_scheduling_observation_required"
    )
    assert actual.status == "not_run"
    assert actual.reason_code == "m7_browser_closed_scheduling_observation_required"
    states: tuple[auto_m7.Status, ...] = ("failed", "blocked", "not_run")
    for state in states:
        result = auto_m7.LaneResult(
            "current_scheduling",
            state,
            (
                auto_m7.CheckResult(
                    "current_scheduling", state, "specific_missing_evidence"
                ),
            ),
        )
        actual = auto_m7.required_boundary_check("collection", result)
        assert actual.status == state
        assert actual.reason_code == "specific_missing_evidence"


def test_first_provider_collection_does_not_close_all_provider_acceptance() -> None:
    assert (
        auto_m7.evaluate_lane(
            "technical", (auto_m7.CheckResult("collection", "passed"),)
        ).status
        == "blocked"
    )
    assert (
        auto_m7.evaluate_lane("live", (auto_m7.CheckResult("ollama", "passed"),)).status
        != "passed"
    )


def test_browser_closed_and_cross_provider_progress_remain_mandatory_at_exit() -> None:
    assert "collection" in auto_m7.REQUIRED_CHECKS["technical"]
    assert "continuity" in auto_m7.REQUIRED_CHECKS["deploy"]
    assert "deploy" in auto_m7.REQUIRED_CHECKS["exit"]
    assert auto_m7.BROWSER_CLOSED_TARGETS == (
        "backend/tests/live/ollama/test_m7_browser_closed_collection.py"
        "::test_new_scheduled_financial_receipt_after_controlled_window_closes",
    )
    absent = tuple(
        auto_m7.CheckResult(name, "not_run" if name == "continuity" else "passed")
        for name in auto_m7.REQUIRED_CHECKS["deploy"]
    )
    assert auto_m7.evaluate_lane("deploy", absent).status != "passed"

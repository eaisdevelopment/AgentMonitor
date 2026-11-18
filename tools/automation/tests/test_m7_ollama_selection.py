"""Pure retained-boundary admission; no simulated tests or provider execution."""

import pytest

from tools.automation.implementations import auto_m7


def test_existing_ollama_live_selector_accepts_optional_exact_revision() -> None:
    for revision in (None, "a" * 40):
        auto_m7.validate_selection("live", "ollama", revision)
    for lane, revision in (("browser", None), ("technical", "a" * 40), ("live", "bad")):
        with pytest.raises(ValueError, match="m7_selection_invalid"):
            auto_m7.validate_selection(lane, "ollama", revision)


def test_retained_ollama_selection_keeps_each_real_boundary_separate() -> None:
    targets = dict(auto_m7.OLLAMA_RETAINED_TARGETS)
    assert targets == {
        "ollama_scheduled_ranges": auto_m7.SCHEDULED_COLLECTION_TARGETS,
        "ollama_current_funds": (
            "backend/tests/live/ollama/test_stored_funds_lineage_live.py",
        ),
        "ollama_monetary_storage": (
            "backend/tests/live/ollama/test_budget_monetary_persistence.py",
        ),
        "ollama_source_provenance": (
            "backend/tests/live/ollama/test_budget_source_evidence.py",
        ),
        "ollama_model_storage": (
            "backend/tests/live/ollama/test_model_report_persistence.py",
        ),
    }
    assert "tools/automation/tests/test_m7_ollama_selection.py" in auto_m7.PURE_TARGETS


def test_retained_reports_cannot_replace_independent_comparison_or_browser_action() -> (
    None
):
    proofs = tuple(
        auto_m7.CheckResult(name, "passed")
        for name, _ in auto_m7.OLLAMA_RETAINED_TARGETS
    )
    result = auto_m7.ollama_retained_result(proofs)
    assert result.lane == "live/ollama"
    assert result.status == "not_run"
    assert result.checks[0].name == "ollama"
    assert result.checks[1:6] == proofs
    assert result.checks[-2:] == (
        auto_m7.CheckResult(
            "independent_native_monetary_comparison",
            "not_run",
            "m7_ollama_independent_monetary_comparison_required",
        ),
        auto_m7.CheckResult(
            "installed_manual_usage_action",
            "not_run",
            "m7_ollama_manual_browser_evidence_required",
        ),
    )


@pytest.mark.parametrize("status", ("failed", "blocked", "not_run"))
def test_actual_retained_nonpass_keeps_original_boundary_reason(
    status: auto_m7.Status,
) -> None:
    proofs = (
        auto_m7.CheckResult("ollama_scheduled_ranges", "passed"),
        auto_m7.CheckResult(
            "ollama_current_funds", status, "actual_funds_lineage_absent"
        ),
    )
    result = auto_m7.ollama_retained_result(proofs)
    assert result.status == status
    assert result.checks[0].reason_code == "actual_funds_lineage_absent"
    assert result.checks[1:] == proofs


def test_unexecuted_retained_selection_cannot_be_admitted() -> None:
    result = auto_m7.ollama_retained_result(())
    assert result.status == "not_run"
    assert result.checks[0].reason_code == "m7_ollama_retained_checks_incomplete"


def _manual_result() -> dict[str, object]:
    context = {
        "scope": "self",
        "range_key": "7d",
        "interval_start": "2026-11-05T00:00:00Z",
        "interval_end": "2026-11-12T00:00:00Z",
        "grouping": [],
    }
    return {
        "record_type": "agentmonitor.m7_cloud_collect_probe.v1",
        "status": "passed",
        "reason": None,
        "revision": "a" * 40,
        "scope": "one_real_cloud_usage_action",
        "range": "7d",
        "usage_scope": "self",
        "grouping": [],
        "posts": 1,
        "unsafe": 0,
        "checks": {
            name: True
            for name in (
                "authentication",
                "controls",
                "eligibility",
                "reload",
                "collection",
                "report",
                "balance_continuity",
            )
        },
        "run": {
            "account_id": "account",
            "resource_id": "resource",
            "run_id": "run",
            "state": "succeeded",
            "report_id": "report",
            "report_context": context,
        },
        "report": {
            "account_id": "account",
            "resource_id": "resource",
            "report_id": "report",
            "provider_key": "ollama",
            "source_id": "ollama.cloud.usage.v1",
            "source_category": "self_requests_and_cost",
            "completeness": "complete",
            "grouping": [],
            "requested_period": {
                "start": context["interval_start"],
                "end": context["interval_end"],
            },
            "covered_period": {
                "start": context["interval_start"],
                "end": context["interval_end"],
            },
        },
    }


def test_complete_manual_witness_passes_only_its_own_boundary() -> None:
    assert (
        auto_m7.ollama_manual_result(0, _manual_result(), "a" * 40).status == "passed"
    )
    proofs = tuple(
        auto_m7.CheckResult(name, "passed")
        for name, _ in auto_m7.OLLAMA_RETAINED_TARGETS
    )
    result = auto_m7.ollama_retained_result(
        proofs, auto_m7.CheckResult("installed_manual_usage_action", "passed")
    )
    assert result.status == "not_run"
    assert result.checks[-1].status == "passed"
    assert result.checks[-2].name == "independent_native_monetary_comparison"
    assert result.checks[-2].status == "not_run"


@pytest.mark.parametrize(
    ("section", "field", "value"),
    (
        (None, "revision", "b" * 40),
        (None, "scope", "cloud_usage_read_only_controls"),
        (None, "range", "30d"),
        (None, "usage_scope", "team"),
        (None, "grouping", ["model"]),
        (None, "posts", 0),
        (None, "posts", 2),
        (None, "posts", True),
        (None, "unsafe", 1),
        ("checks", "report", False),
        ("checks", "collection", 1),
        ("run", "state", "partial"),
        ("run", "report_id", None),
        ("report", "completeness", "partial"),
        ("report", "account_id", "other"),
        ("report", "resource_id", "other"),
        ("report", "report_id", "other"),
        ("report", "grouping", ["model"]),
        ("report", "covered_period", None),
    ),
)
def test_partial_wrong_or_replayed_manual_result_cannot_pass(
    section: str | None, field: str, value: object
) -> None:
    payload = _manual_result()
    target = payload if section is None else payload[section]
    assert isinstance(target, dict)
    target[field] = value
    assert auto_m7.ollama_manual_result(0, payload, "a" * 40).status == "failed"


def test_manual_auth_before_revision_is_blocked_without_submission() -> None:
    payload = _manual_result() | {
        "status": "blocked",
        "reason": "authentication_required",
        "revision": None,
        "posts": 0,
        "run": None,
        "report": None,
    }
    actual = auto_m7.ollama_manual_result(3, payload, "a" * 40)
    assert (
        actual.status == "blocked" and actual.reason_code == "authentication_required"
    )
    assert auto_m7.ollama_manual_result(0, payload, "a" * 40).status == "failed"
    assert (
        auto_m7.ollama_manual_result(3, payload | {"posts": 1}, "a" * 40).status
        == "failed"
    )


def test_manual_success_cannot_use_an_invalid_expected_revision() -> None:
    payload = _manual_result() | {"revision": "bad"}
    assert auto_m7.ollama_manual_result(0, payload, "bad").status == "failed"


def test_native_and_manual_results_are_independent_required_boundaries() -> None:
    assert auto_m7.OLLAMA_NATIVE_COMPARISON_TARGETS == (
        "backend/tests/live/ollama/test_m7_native_usage_comparison.py"
        "::test_one_due_real_usage_read_matches_native_completed_usd",
    )
    proofs = tuple(
        auto_m7.CheckResult(name, "passed")
        for name, _ in auto_m7.OLLAMA_RETAINED_TARGETS
    )
    native = auto_m7.CheckResult("independent_native_monetary_comparison", "passed")
    manual = auto_m7.CheckResult("installed_manual_usage_action", "passed")
    assert auto_m7.ollama_retained_result(proofs, manual, native).status == "passed"
    blocked = auto_m7.CheckResult(
        "installed_manual_usage_action", "blocked", "authentication_required"
    )
    result = auto_m7.ollama_retained_result(proofs, blocked, native)
    assert result.status == "blocked"
    assert result.checks[-2:] == (native, blocked)
    absent = auto_m7.CheckResult(
        "independent_native_monetary_comparison",
        "not_run",
        "m7_expected_installed_revision_required",
    )
    assert auto_m7.ollama_retained_result(proofs, manual, absent).status == "not_run"

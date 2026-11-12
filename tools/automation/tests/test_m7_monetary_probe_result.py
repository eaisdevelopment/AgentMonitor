"""Pure policy for admitting an actual monetary browser result, never telemetry."""

from copy import deepcopy

import pytest

from tools.automation.implementations.auto_m7 import monetary_probe_result

REVISION = "a" * 40


def _result() -> dict:
    return {
        "record_type": "agentmonitor.m7_overview_probe.v1",
        "status": "passed",
        "reason_code": "real_monetary_overview_detail_history_verified",
        "source_revision": REVISION,
        "unsafe_requests": 0,
        "checks": {
            name: "passed"
            for name in (
                "monetary",
                "authentication",
                "overview",
                "filters",
                "navigation",
                "financial_entry",
                "source_history",
                "history_windows",
                "responsive",
                "pool_controls",
                "read_only",
            )
        },
    }


def test_exact_monetary_journey_result_is_admitted_without_closing_overview() -> None:
    result = monetary_probe_result(0, _result(), REVISION)
    assert result.name == "monetary_journey"
    assert result.status == "passed"


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("record_type", "other"),
        ("source_revision", "b" * 40),
        ("unsafe_requests", 1),
        ("unsafe_requests", False),
        ("reason_code", "real_overview_api_dom_navigation_verified"),
        ("checks", {"monetary": "passed"}),
        ("checks", None),
    ),
)
def test_wrong_or_incomplete_result_cannot_certify_money(field: str, value) -> None:
    payload = _result()
    payload[field] = value
    assert monetary_probe_result(0, payload, REVISION).status == "failed"


def test_generic_counts_only_success_does_not_prove_money() -> None:
    payload = deepcopy(_result())
    payload["checks"]["monetary"] = "not_run"
    assert monetary_probe_result(0, payload, REVISION).status == "failed"


@pytest.mark.parametrize("value", (None, [], "not a result"))
def test_non_result_cannot_pass(value) -> None:
    assert monetary_probe_result(0, value, REVISION).status == "failed"


def test_process_failure_cannot_be_hidden_by_success_payload() -> None:
    assert monetary_probe_result(1, _result(), REVISION).status == "failed"


def test_missing_real_money_remains_blocked_not_a_pass() -> None:
    payload = _result()
    payload.update(
        status="blocked", reason_code="genuine_complete_monetary_report_required"
    )
    payload["checks"]["monetary"] = "not_run"
    result = monetary_probe_result(3, payload, REVISION)
    assert result.status == "blocked"
    assert result.reason_code == "genuine_complete_monetary_report_required"


def test_arbitrary_child_error_text_is_not_published() -> None:
    payload = _result()
    payload.update(status="failed", reason_code="untrusted text with an address")
    result = monetary_probe_result(1, payload, REVISION)
    assert result.status == "failed"
    assert result.reason_code == "m7_monetary_probe_failed"

"""Keep retained provider evidence distinct from complete live acceptance."""

import pytest

from tools.automation.implementations import auto_m7


@pytest.mark.parametrize("provider", ["anthropic", "openai"])
def test_provider_retained_checks_are_explicit_live_selections(provider: str) -> None:
    auto_m7.validate_selection("live", provider, None)
    assert auto_m7.PROVIDER_REPORT_TARGETS[provider] == (
        f"backend/tests/live/{provider}/test_{provider}_budget_reports.py"
        f"::test_{provider}_retained_reports_cover_reviewed_mappings_and_ranges",
    )


@pytest.mark.parametrize("provider", ["anthropic", "openai"])
@pytest.mark.parametrize("lane", ["pure", "technical", "browser", "deploy", "exit"])
def test_provider_report_selection_cannot_cross_lanes(lane: str, provider: str) -> None:
    with pytest.raises(ValueError, match="m7_selection_invalid"):
        auto_m7.validate_selection(lane, provider, None)


@pytest.mark.parametrize("provider", ["anthropic", "openai"])
def test_provider_comparison_requires_valid_optional_installed_revision(
    provider: str,
) -> None:
    auto_m7.validate_selection("live", provider, "a" * 40)
    with pytest.raises(ValueError, match="m7_selection_invalid"):
        auto_m7.validate_selection("live", provider, "bad")


@pytest.mark.parametrize("provider", ["anthropic", "openai"])
def test_retained_integrity_without_native_comparison_is_not_provider_success(
    provider: str,
) -> None:
    retained = auto_m7.CheckResult(provider, "passed")
    result = auto_m7.provider_reports_result(provider, retained)
    assert result.status == "not_run"
    assert result.checks[1] == retained
    assert (
        result.checks[-1].reason_code
        == "m7_fresh_provider_access_and_source_comparison_required"
    )


@pytest.mark.parametrize("provider", ["anthropic", "openai"])
def test_independent_comparison_and_all_retained_mappings_are_both_required(
    provider: str,
) -> None:
    native = auto_m7.CheckResult(provider + "_native_comparison", "passed")
    retained = auto_m7.CheckResult(provider, "passed")
    assert (
        auto_m7.provider_reports_result(provider, retained, native).status == "passed"
    )
    for status in ("failed", "blocked", "not_run"):
        unavailable = auto_m7.CheckResult(provider, status, "retained_incomplete")
        result = auto_m7.provider_reports_result(provider, unavailable, native)
        assert result.status == status
        assert result.checks[0].reason_code == "retained_incomplete"
        unavailable_native = auto_m7.CheckResult(
            provider + "_native_comparison", status, "native_incomplete"
        )
        result = auto_m7.provider_reports_result(provider, retained, unavailable_native)
        assert result.status == status
        assert result.checks[0].reason_code == "native_incomplete"


def test_provider_result_rejects_cross_provider_proof() -> None:
    with pytest.raises(ValueError, match="m7_provider_proof_mismatch"):
        auto_m7.provider_reports_result(
            "anthropic",
            auto_m7.CheckResult("openai", "passed"),
            auto_m7.CheckResult("anthropic_native_comparison", "passed"),
        )
    with pytest.raises(ValueError, match="m7_provider_proof_mismatch"):
        auto_m7.provider_reports_result(
            "anthropic",
            auto_m7.CheckResult("anthropic", "passed"),
            auto_m7.CheckResult("openai_native_comparison", "passed"),
        )

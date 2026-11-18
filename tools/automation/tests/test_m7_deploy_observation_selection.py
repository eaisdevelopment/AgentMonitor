"""Pure selection and result semantics; no invented service or test execution."""

import pytest

from tools.automation.implementations import auto_m7


@pytest.mark.parametrize("check", [None, "candidate", "installed_revision"])
def test_read_only_deploy_observation_requires_explicit_revision(
    check: str | None,
) -> None:
    auto_m7.validate_selection("deploy", check, "a" * 40)
    if check is not None:
        with pytest.raises(ValueError, match="m7_selection_invalid"):
            auto_m7.validate_selection("deploy", check, None)
        with pytest.raises(ValueError, match="m7_selection_invalid"):
            auto_m7.validate_selection("technical", check, "a" * 40)
    with pytest.raises(ValueError, match="m7_selection_invalid"):
        auto_m7.validate_selection("deploy", check, "bad")


def test_financial_recovery_reuses_exact_existing_required_proofs() -> None:
    auto_m7.validate_selection("live", "recovery", None)
    assert auto_m7.RECOVERY_PROOFS == (
        "collection_guards",
        "queued_expiry_history",
        "receipt_recovery",
        "backup_recovery",
    )
    checks = tuple(
        auto_m7.CheckResult(name, "passed") for name in auto_m7.RECOVERY_PROOFS
    )
    result = auto_m7.recovery_result(checks)
    assert result.status != "passed"
    assert result.checks[0].name == "recovery"
    assert (
        result.checks[0].reason_code == "m7_source_failure_isolation_evidence_required"
    )
    assert result.checks[1:5] == checks
    assert any(
        check.name == "uncertain_financial_dispatch" and check.status == "not_run"
        for check in result.checks
    )


@pytest.mark.parametrize("status", ["failed", "blocked", "not_run"])
def test_recovery_keeps_the_original_nonpass_reason(status: auto_m7.Status) -> None:
    checks = (
        auto_m7.CheckResult("collection_guards", "passed"),
        auto_m7.CheckResult(
            "queued_expiry_history", status, "observed_boundary_failure"
        ),
    )
    result = auto_m7.recovery_result(checks)
    assert result.status == status
    assert result.checks[0].reason_code == "observed_boundary_failure"
    assert result.checks[1:] == checks


def test_missing_recovery_execution_is_not_converted_to_pass() -> None:
    result = auto_m7.recovery_result(())
    assert result.status == "not_run"
    assert result.checks[0].reason_code == "m7_recovery_proofs_incomplete"


def test_recovery_needs_actual_isolation_and_preserves_conditional_dispatch() -> None:
    proofs = tuple(
        auto_m7.CheckResult(name, "passed") for name in auto_m7.RECOVERY_PROOFS
    )
    actual = auto_m7.recovery_result(
        proofs, auto_m7.CheckResult("source_failure_isolation", "passed")
    )
    assert actual.status == "passed"
    assert actual.checks[-1].name == "uncertain_financial_dispatch"
    assert actual.checks[-1].status == "not_run"
    unavailable = auto_m7.recovery_result(
        proofs,
        auto_m7.CheckResult(
            "source_failure_isolation", "blocked", "authentication_required"
        ),
    )
    assert unavailable.status == "blocked"
    assert unavailable.checks[0].reason_code == "authentication_required"


def test_recovery_reports_verified_unknown_dispatch_without_waiving_isolation() -> None:
    proofs = tuple(
        auto_m7.CheckResult(name, "passed") for name in auto_m7.RECOVERY_PROOFS
    )
    actual = auto_m7.recovery_result(
        proofs,
        auto_m7.CheckResult(
            "source_failure_isolation",
            "passed",
            "m7_financial_uncertain_source_recovered",
        ),
    )
    assert actual.status == "passed"
    assert actual.checks[-1] == auto_m7.CheckResult(
        "uncertain_financial_dispatch",
        "passed",
        "m7_genuine_abandoned_financial_dispatch_recovered",
    )

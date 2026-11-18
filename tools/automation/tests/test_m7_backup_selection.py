"""Pure backup-check selection never substitutes for full installed recovery."""

import pytest

from tools.automation.implementations.auto_m7 import (
    CheckResult,
    evaluate_lane,
    validate_selection,
)


def test_isolated_backup_check_accepts_explicit_deploy_selection() -> None:
    validate_selection("deploy", "backup_recovery", None)


@pytest.mark.parametrize("lane", ["pure", "technical", "live", "browser", "exit"])
def test_backup_check_rejects_other_lanes(lane: str) -> None:
    with pytest.raises(ValueError, match="m7_selection_invalid"):
        validate_selection(lane, "backup_recovery", None)


def test_isolated_backup_does_not_claim_installed_revision() -> None:
    with pytest.raises(ValueError, match="m7_selection_invalid"):
        validate_selection("deploy", "backup_recovery", "a" * 40)
    assert (
        evaluate_lane("deploy", (CheckResult("backup_recovery", "passed"),)).status
        == "blocked"
    )

"""Pure selection for populated HTTP evidence, separate from provider access."""

import pytest

from tools.automation.implementations.auto_m7 import (
    CheckResult,
    evaluate_lane,
    validate_selection,
)


def test_populated_http_selection_is_explicit() -> None:
    validate_selection("technical", "budget_http", None)


@pytest.mark.parametrize("lane", ["pure", "live", "browser", "deploy", "exit"])
def test_populated_http_refuses_other_lanes(lane: str) -> None:
    with pytest.raises(ValueError, match="m7_selection_invalid"):
        validate_selection(lane, "budget_http", None)


def test_populated_http_does_not_claim_live_provider_or_full_technical() -> None:
    with pytest.raises(ValueError, match="m7_selection_invalid"):
        validate_selection("technical", "budget_http", "a" * 40)
    assert (
        evaluate_lane("technical", (CheckResult("budget_http", "passed"),)).status
        == "blocked"
    )

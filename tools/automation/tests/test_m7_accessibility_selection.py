"""Real keyboard and native zoom must both run for the M7 browser check."""

import pytest

from tools.automation.implementations import auto_m7


def test_accessibility_selection_requires_keyboard_and_native_zoom() -> None:
    auto_m7.validate_selection("browser", "accessibility", None)
    assert auto_m7.BROWSER_ACCESSIBILITY_TARGETS == (
        "backend/tests/live/ollama/test_m7_accessibility_browser.py",
        "backend/tests/live/ollama/test_m7_native_zoom_browser.py",
    )


@pytest.mark.parametrize("lane", ["pure", "technical", "live", "deploy", "exit"])
def test_accessibility_is_not_other_lifecycle_evidence(lane: str) -> None:
    with pytest.raises(ValueError, match="m7_selection_invalid"):
        auto_m7.validate_selection(lane, "accessibility", None)


def test_accessibility_is_not_installed_revision_or_complete_browser_evidence() -> None:
    with pytest.raises(ValueError, match="m7_selection_invalid"):
        auto_m7.validate_selection("browser", "accessibility", "a" * 40)
    assert (
        auto_m7.evaluate_lane(
            "browser", (auto_m7.CheckResult("accessibility", "passed"),)
        ).status
        == "blocked"
    )

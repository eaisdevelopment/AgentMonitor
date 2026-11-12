"""Pure selection cannot turn owner-metadata browser proof into full M7."""

import pytest

from tools.automation.implementations.auto_m7 import (
    CheckResult,
    evaluate_lane,
    validate_selection,
)


@pytest.mark.parametrize("check", ["owner_pool_controls", "source_history"])
def test_pool_browser_slice_is_explicit_and_cannot_close_browser(check: str) -> None:
    validate_selection("browser", check, None)
    assert (
        evaluate_lane("browser", (CheckResult("owner_setup", "passed"),)).status
        != "passed"
    )
    for lane in ("technical", "exit", "live", "deploy"):
        with pytest.raises(ValueError, match="m7_selection_invalid"):
            validate_selection(lane, check, None)
    with pytest.raises(ValueError, match="m7_selection_invalid"):
        validate_selection("browser", check, "a" * 40)

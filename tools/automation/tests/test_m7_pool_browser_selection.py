"""Pure selection cannot turn owner-metadata browser proof into full M7."""

import pytest

from tools.automation.implementations.auto_m7 import (
    CheckResult,
    evaluate_lane,
    validate_selection,
)


def test_pool_browser_slice_is_explicit_and_cannot_close_browser() -> None:
    validate_selection("browser", "owner_pool_controls", None)
    assert (
        evaluate_lane("browser", (CheckResult("owner_setup", "passed"),)).status
        != "passed"
    )
    for lane in ("technical", "exit", "live", "deploy"):
        with pytest.raises(ValueError, match="m7_selection_invalid"):
            validate_selection(lane, "owner_pool_controls", None)
    with pytest.raises(ValueError, match="m7_selection_invalid"):
        validate_selection("browser", "owner_pool_controls", "a" * 40)

"""Pure selection policy for the actual revision-bound Overview browser check."""

import pytest

from tools.automation.implementations.auto_m7 import validate_selection


def test_overview_check_accepts_exact_installed_revision() -> None:
    validate_selection("browser", "overview", "a" * 40)


@pytest.mark.parametrize(
    ("lane", "revision"),
    (("browser", None), ("browser", "short"), ("technical", "a" * 40)),
)
def test_overview_check_rejects_ambiguous_revision_or_lane(
    lane: str,
    revision: str | None,
) -> None:
    with pytest.raises(ValueError, match="m7_selection_invalid"):
        validate_selection(lane, "overview", revision)


def test_overview_runner_executes_available_real_pool_test_node() -> None:
    """Select real populated evidence without requiring absent extra examples."""
    from tools.automation.implementations.auto_m7 import _run_pytest

    result = _run_pytest(
        "available_pool_totals",
        (
            "backend/tests/live/ollama/test_budget_pool_totals_live.py"
            "::test_genuine_available_filtered_pool_totals",
        ),
    )
    assert result.status == "passed", result.reason_code

"""Pure structural checks for the bounded Claude quota screen parser."""

from decimal import Decimal

import pytest
from agentmonitor.adapters.providers.claude.subscription.source import (
    _IncompleteRender,
    _parse_complete_usage_segment,
)


def test_model_specific_weekly_window_is_a_bounded_omission() -> None:
    """CLA-PARSER-001: V1 keeps known windows and reports the new card."""
    result = _parse_complete_usage_segment(
        (
            "Current session",
            "12% used",
            "Resets in 2 hr",
            "Current week (all models)",
            "33% used",
            "Resets Oct 9",
            "Current week (Example model)",
            "44% used",
            "Resets Oct 9",
        )
    )

    assert tuple(window.window_key for window in result.windows) == (
        "current_session",
        "current_week_all_models",
    )
    assert result.windows[1].percent_used == Decimal("33")
    assert result.omission_codes == ("claude_model_specific_window_unsupported",)


def test_missing_provider_reset_is_preserved_as_unknown() -> None:
    """FR-COL-004/007: a reported percentage never invents a reset value."""
    result = _parse_complete_usage_segment(
        (
            "Current session",
            "12% used",
            "Current week (all models)",
            "33% used",
            "Resets Oct 9",
        )
    )

    assert result.windows[0].window_key == "current_session"
    assert result.windows[0].percent_used == Decimal("12")
    assert result.windows[0].reset_display is None


@pytest.mark.parametrize(
    "malformed_reset",
    ("Resets: tomorrow", "Reset tomorrow", "Resets"),
)
def test_malformed_reset_shaped_line_fails_closed(malformed_reset: str) -> None:
    """FR-COL-006/008: malformed reset text is data, not an absent field."""
    with pytest.raises(_IncompleteRender, match="^usage_reset_display_invalid$"):
        _parse_complete_usage_segment(
            (
                "Current session",
                "12% used",
                malformed_reset,
                "Current week (all models)",
                "33% used",
                "Resets Oct 9",
            )
        )


def test_malformed_reset_beyond_six_lines_fails_closed() -> None:
    """FR-COL-006/008: the complete bounded window region is validated."""
    with pytest.raises(_IncompleteRender, match="^usage_reset_display_invalid$"):
        _parse_complete_usage_segment(
            (
                "Current session",
                "12% used",
                "Usage detail one",
                "Usage detail two",
                "Usage detail three",
                "Usage detail four",
                "Usage detail five",
                "Resets: tomorrow",
                "Current week (all models)",
                "33% used",
                "Resets Oct 9",
            )
        )


def test_usage_segment_larger_than_terminal_surface_fails_closed() -> None:
    """FR-COL-006/008: direct parser calls retain the terminal row bound."""
    oversized = (
        "Current session",
        "12% used",
        *(f"Usage detail {index}" for index in range(36)),
        "Current week (all models)",
        "33% used",
        "Resets Oct 9",
    )

    with pytest.raises(_IncompleteRender, match="^usage_window_set_invalid$"):
        _parse_complete_usage_segment(oversized)


def test_multiple_model_specific_weekly_windows_fail_closed() -> None:
    """FR-COL-006/008: ambiguous model cards cannot become a reading."""
    with pytest.raises(
        _IncompleteRender,
        match="^usage_window_conflicting_duplicate$",
    ):
        _parse_complete_usage_segment(
            (
                "Current session",
                "12% used",
                "Resets in 2 hr",
                "Current week (all models)",
                "33% used",
                "Resets Oct 9",
                "Current week (Example model)",
                "44% used",
                "Resets Oct 9",
                "Current week (Another model)",
                "55% used",
                "Resets Oct 9",
            )
        )


def test_unallowlisted_current_week_label_fails_closed() -> None:
    """FR-COL-006/008: a shaped but unbounded label cannot be ignored."""
    unallowlisted = "Current week (" + "A" * 49 + ")"
    with pytest.raises(_IncompleteRender, match="^usage_window_label_invalid$"):
        _parse_complete_usage_segment(
            (
                "Current session",
                "12% used",
                "Resets in 2 hr",
                "Current week (all models)",
                "33% used",
                "Resets Oct 9",
                unallowlisted,
                "33% used",
                "Resets Oct 9",
            )
        )


@pytest.mark.parametrize(
    "unallowlisted",
    (
        "Current week",
        "Current week - Example model",
        "Current week [Example model]",
    ),
)
def test_every_unallowlisted_current_week_shape_fails_closed(
    unallowlisted: str,
) -> None:
    """FR-COL-006/008: alternate weekly labels cannot reuse prior values."""
    with pytest.raises(_IncompleteRender, match="^usage_window_label_invalid$"):
        _parse_complete_usage_segment(
            (
                "Current session",
                "12% used",
                "Resets in 2 hr",
                "Current week (all models)",
                "33% used",
                "Resets Oct 9",
                unallowlisted,
                "33% used",
                "Resets Oct 9",
            )
        )

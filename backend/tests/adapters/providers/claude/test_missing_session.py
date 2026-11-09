"""Pure bounded-render/availability decisions; no provider responses replayed."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from agentmonitor.adapters.providers.claude.subscription import source
from agentmonitor.adapters.providers.claude.subscription.mapper import (
    SanitizedClaudeUsageSnapshot,
    SanitizedClaudeUsageWindow,
    map_subscription_quota,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def _weekly() -> bytes:
    return b"Current week (all models)\r\n24% used\r\nResets Nov 12\r\nUsage credits"


def _parse(
    raw: bytes,
    *,
    post_command_offset: int = 0,
    deadline_reached: bool = True,
    quiet_seconds: float = 1.5,
) -> SanitizedClaudeUsageSnapshot:
    return source._parse_missing_session_at_deadline(
        raw,
        post_command_offset=post_command_offset,
        deadline_reached=deadline_reached,
        quiet_seconds=quiet_seconds,
    )


def test_complete_settled_weekly_surface_retains_unknown_session() -> None:
    snapshot = _parse(_weekly())
    session, weekly = snapshot.windows
    assert session.window_key == "current_session"
    assert session.percent_used is None and session.reset_display is None
    assert weekly.percent_used == Decimal("24")
    assert "claude_current_session_not_reported" in snapshot.omission_codes


@pytest.mark.parametrize(
    "deadline_reached,quiet_seconds,post_command_offset",
    [
        (False, 1.5, 0),
        (True, 0.9, 0),
        (True, float("nan"), 0),
        (True, 1.5, -1),
        (True, 1.5, len(_weekly())),
    ],
)
def test_unsettled_or_unbound_capture_cannot_become_partial(
    deadline_reached: bool, quiet_seconds: float, post_command_offset: int
) -> None:
    with pytest.raises(source._IncompleteRender):
        _parse(
            _weekly(),
            deadline_reached=deadline_reached,
            quiet_seconds=quiet_seconds,
            post_command_offset=post_command_offset,
        )


@pytest.mark.parametrize(
    "prefix",
    [
        b"Current session\r\n",
        b"Current\x1b[0m session\r\n",
        b"Current session: loading\r\n",
        b"Current\r\nsession\r\n",
        b"Current\x1b[1Csession\r\n",
        b"session\r\x1b[8G\rCurrent session\r\n",
    ],
)
def test_session_label_erased_or_scrolled_out_cannot_be_called_absent(
    prefix: bytes,
) -> None:
    with pytest.raises(source._IncompleteRender):
        _parse(prefix + b"\x1b[2J\x1b[H" + _weekly())


@pytest.mark.parametrize(
    "raw",
    [
        b"Usage credits",
        b"Current week (all models)\r\nUsage credits",
        _weekly().replace(b"24% used", b"101% used"),
        _weekly().replace(b"Resets Nov 12", b"Resets: invalid"),
        b"not logged in\r\n" + _weekly(),
        b"Error: quota fetch failed\r\n" + _weekly(),
        _weekly().replace(b"Usage credits", b""),
        b"\x1b[?999h" + _weekly(),
    ],
)
def test_invalid_or_incomplete_weekly_surface_remains_failed(raw: bytes) -> None:
    with pytest.raises(source._IncompleteRender):
        _parse(raw)


def test_old_completion_marker_is_not_a_post_command_observation() -> None:
    old = _weekly()
    with pytest.raises(source._IncompleteRender):
        _parse(old + b"\r\nLoading", post_command_offset=len(old))


def test_fresh_marker_cannot_make_precommand_weekly_values_current() -> None:
    old = _weekly().replace(b"Usage credits", b"")
    with pytest.raises(source._IncompleteRender):
        _parse(old + b"Usage credits", post_command_offset=len(old))


@pytest.mark.parametrize("label", [b"Current sessio", b"Current sess", b"Current se"])
def test_truncated_session_label_is_not_a_missing_session(label: bytes) -> None:
    with pytest.raises(source._IncompleteRender):
        _parse(label + b"\r\n" + _weekly())


def test_unknown_session_maps_without_a_synthetic_percentage() -> None:
    now = datetime(2026, 11, 9, tzinfo=UTC)
    snapshot = SanitizedClaudeUsageSnapshot(
        (
            SanitizedClaudeUsageWindow("current_session", None, None),
            SanitizedClaudeUsageWindow("current_week_all_models", Decimal("24"), None),
        ),
        now,
        now,
        ("claude_current_session_not_reported",),
    )
    value = map_subscription_quota(
        snapshot,
        account_ref=OpaqueIdV1("account-one"),
        resource_ref=OpaqueIdV1("resource-one"),
    )
    assert value.windows[0].percent_used.value is None
    assert value.windows[0].percent_used.availability.state == "unknown"
    assert value.windows[1].percent_used.value == Decimal("24")

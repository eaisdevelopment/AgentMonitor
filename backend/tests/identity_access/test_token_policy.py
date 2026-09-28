"""Pure frozen M2 API-token policy; constructed UTC values have no I/O."""

from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.modules.identity_access.domain.policy import (
    canonical_token_name,
    may_issue_scopes,
    may_manage_token,
    token_deadline,
    token_should_touch,
    token_state,
)


def test_token_name_trims_without_weakening_codepoint_or_utf8_boundaries() -> None:
    assert canonical_token_name("  Café  ") == "Café"
    assert canonical_token_name("x" * 80) == "x" * 80
    assert canonical_token_name("😀" * 64) == "😀" * 64
    for invalid in ("", "   ", "x" * 81, "😀" * 65, "name\nline", "\ud800"):
        assert canonical_token_name(invalid) is None


def test_token_expiry_uses_independent_frozen_limits_and_default() -> None:
    issued = datetime(2026, 1, 1, tzinfo=UTC)
    assert token_deadline(issued, None) == issued + timedelta(days=90)
    assert token_deadline(issued, 3600) == issued + timedelta(hours=1)
    assert token_deadline(issued, 31_536_000) == issued + timedelta(days=365)
    for invalid in (True, 3599, 31_536_001):
        with pytest.raises(ValueError, match="token_expiry_invalid"):
            token_deadline(issued, invalid)


def test_observed_terminal_token_never_reactivates_when_clock_moves_backward() -> None:
    issued = datetime(2026, 1, 1, tzinfo=UTC)
    expires = issued + timedelta(hours=1)
    assert token_state(expires, expires, None, None) == "expired"
    assert (
        token_state(issued + timedelta(seconds=1), expires, expires, "expired")
        == "expired"
    )
    assert (
        token_state(issued + timedelta(seconds=1), expires, expires, "rotation")
        == "rotated"
    )
    assert (
        token_state(issued + timedelta(seconds=1), expires, expires, "administrator")
        == "revoked"
    )
    assert token_should_touch(issued, None)
    assert not token_should_touch(issued + timedelta(seconds=59), issued)
    assert token_should_touch(issued + timedelta(seconds=60), issued)


def test_bearer_target_management_is_closed_to_held_scopes() -> None:
    held = frozenset({"read:diagnostics", "write:tokens"})
    assert may_manage_token(held, frozenset({"write:tokens"}))
    assert not may_manage_token(held, frozenset({"read:status"}))
    assert not may_manage_token(
        frozenset({"read:diagnostics"}), frozenset({"read:diagnostics"})
    )


def test_admin_can_issue_narrow_account_write_scope_without_escalation() -> None:
    held = frozenset({"read:accounts", "write:accounts", "write:tokens"})
    assert may_issue_scopes(held, frozenset({"write:accounts"}))
    assert not may_issue_scopes(
        frozenset({"read:accounts", "write:tokens"}),
        frozenset({"write:accounts"}),
    )

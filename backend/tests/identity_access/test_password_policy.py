"""M01-PURE-001..005: deterministic identity policy, with no I/O."""

from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.modules.identity_access.domain import policy


@pytest.mark.parametrize(
    ("candidate", "expected"),
    [
        ("a" * 14, "too_short"),
        ("a" * 15, None),
        ("é" * 512, None),
        ("é" * 513, "too_large"),
        ("a" * 1025, "too_large"),
    ],
)
def test_password_creation_bounds(candidate: str, expected: str | None) -> None:
    assert policy.password_creation_error(candidate) == expected


def test_password_policy_counts_codepoints_without_normalization() -> None:
    composed = "é" * 15
    decomposed = "e\u0301" * 15
    assert composed != decomposed
    assert policy.password_creation_error(composed) is None
    assert policy.password_creation_error(decomposed) is None
    assert policy.password_creation_error(composed) != "too_short"


def test_password_policy_rejects_unencodable_unicode_without_exception() -> None:
    assert policy.password_creation_error("\ud800" * 15) == "invalid_unicode"


def test_bootstrap_precondition_distinguishes_initialized_from_incompatible() -> None:
    assert policy.bootstrap_state_error("uninitialized") is None
    assert policy.bootstrap_state_error("initialized") == (
        "administrator_already_initialized"
    )
    assert policy.bootstrap_state_error("incompatible") == "iam_repository_unavailable"


def test_expiry_is_terminal_at_either_deadline() -> None:
    issued = datetime(2026, 1, 1, tzinfo=UTC)
    idle = issued + timedelta(minutes=30)
    absolute = issued + timedelta(hours=12)
    assert not policy.session_expired(idle - timedelta(microseconds=1), idle, absolute)
    assert policy.session_expired(idle, idle, absolute)
    assert policy.session_expired(absolute, absolute, absolute)


def test_token_scope_attenuation_and_unknown_scope_denial() -> None:
    held = frozenset({"read:diagnostics", "write:tokens"})
    assert policy.may_issue_scopes(held, frozenset({"read:diagnostics"}))
    assert not policy.may_issue_scopes(held, frozenset({"read:status"}))
    assert not policy.may_issue_scopes(
        frozenset({"read:diagnostics"}), frozenset({"read:diagnostics"})
    )


def test_retention_cutoff_preserves_recent_and_active_records() -> None:
    now = datetime(2026, 9, 20, tzinfo=UTC)
    cutoff = policy.terminal_record_cutoff(now)
    assert cutoff == datetime(2025, 9, 20, tzinfo=UTC)
    assert not policy.terminal_record_eligible(None, cutoff)
    assert not policy.terminal_record_eligible(
        cutoff + timedelta(microseconds=1), cutoff
    )
    assert policy.terminal_record_eligible(cutoff, cutoff)

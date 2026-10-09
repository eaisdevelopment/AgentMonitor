"""Pure M01 session deadlines and authorization facts, with explicit UTC time."""

from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.identity_access_v1 import PrincipalV1
from agentmonitor.modules.identity_access.application.authorization import (
    AuthorizePrincipalV1,
)
from agentmonitor.modules.identity_access.domain.policy import (
    SESSION_TOUCH_SECONDS,
    idempotency_receipt_expired,
    session_deadlines,
    session_state,
    should_touch_session,
)


def test_idle_deadline_is_capped_by_absolute_and_touch_is_coalesced() -> None:
    issued = datetime(2026, 1, 1, tzinfo=UTC)
    initial_idle, absolute = session_deadlines(issued)
    assert initial_idle == issued + timedelta(seconds=86400)
    assert absolute == issued + timedelta(seconds=86400)
    assert not should_touch_session(issued + timedelta(seconds=59), issued)
    assert should_touch_session(issued + timedelta(seconds=60), issued)
    near_absolute = absolute - timedelta(seconds=60)
    refreshed_idle, unchanged_absolute = session_deadlines(
        near_absolute,
        absolute_expires_at=absolute,
        persisted_activity_at=issued,
        persisted_idle_expires_at=absolute,
    )
    assert refreshed_idle == unchanged_absolute == absolute
    assert SESSION_TOUCH_SECONDS == 60


def test_touch_preserves_the_idle_window_persisted_for_each_session() -> None:
    issued = datetime(2026, 1, 1, tzinfo=UTC)
    touched = issued + timedelta(seconds=60)
    legacy_absolute = issued + timedelta(seconds=43_200)
    legacy_idle, unchanged_legacy_absolute = session_deadlines(
        touched,
        persisted_activity_at=issued,
        persisted_idle_expires_at=issued + timedelta(seconds=1_800),
        absolute_expires_at=legacy_absolute,
    )
    assert legacy_idle == touched + timedelta(seconds=1_800)
    assert unchanged_legacy_absolute == legacy_absolute
    current_absolute = issued + timedelta(seconds=86_400)
    current_idle, unchanged_current_absolute = session_deadlines(
        touched,
        persisted_activity_at=issued,
        persisted_idle_expires_at=current_absolute,
        absolute_expires_at=current_absolute,
    )
    assert current_idle == unchanged_current_absolute == current_absolute


def test_existing_absolute_deadline_requires_its_persisted_idle_window() -> None:
    issued = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match="session_idle_window_incomplete"):
        session_deadlines(
            issued + timedelta(seconds=60),
            absolute_expires_at=issued + timedelta(seconds=43_200),
        )


def test_idempotency_receipt_expires_at_exact_24_hour_deadline() -> None:
    created = datetime(2026, 1, 1, tzinfo=UTC)
    deadline = created + timedelta(seconds=86400)
    assert not idempotency_receipt_expired(
        deadline - timedelta(microseconds=1), deadline
    )
    assert idempotency_receipt_expired(deadline, deadline)


def test_observed_expiry_remains_terminal_even_if_clock_moves_backward() -> None:
    issued = datetime(2026, 1, 1, tzinfo=UTC)
    idle = issued + timedelta(seconds=86400)
    absolute = issued + timedelta(seconds=86400)
    observed = idle
    assert session_state(observed, idle, absolute, None, None) == "expired"
    assert (
        session_state(
            issued + timedelta(seconds=1), idle, absolute, observed, "expired"
        )
        == "expired"
    )
    assert (
        session_state(issued + timedelta(seconds=1), idle, absolute, observed, "logout")
        == "revoked"
    )


def test_authorization_never_conflates_dashboard_with_provider_auth() -> None:
    instant = datetime(2026, 1, 1, tzinfo=UTC)
    browser = PrincipalV1(
        OpaqueIdV1("administrator"),
        "browser_session",
        OpaqueIdV1("session"),
        ("read:self", "write:self", "write:sessions", "write:tokens"),
        instant,
        instant,
        instant + timedelta(hours=12),
    )
    bearer = PrincipalV1(
        OpaqueIdV1("administrator"),
        "api_bearer",
        OpaqueIdV1("token"),
        ("read:diagnostics",),
        instant,
        instant,
        instant + timedelta(days=1),
    )
    authorize = AuthorizePrincipalV1()
    allowed = authorize(
        browser, "write:self", correlation_id=OpaqueIdV1("auth-browser")
    )
    denied = authorize(bearer, "write:self", correlation_id=OpaqueIdV1("auth-bearer"))
    diagnostics = authorize(
        bearer, "read:diagnostics", correlation_id=OpaqueIdV1("auth-read")
    )
    assert allowed.allowed is True
    assert denied.allowed is False
    assert denied.reason_code == "permission_denied"
    assert diagnostics.allowed is True


def test_registry_write_requires_explicit_browser_or_bearer_scope() -> None:
    """M01/P01: admin CRUD has one narrow permission, not a role bypass."""
    instant = datetime(2026, 1, 1, tzinfo=UTC)
    authorize = AuthorizePrincipalV1()
    browser = PrincipalV1(
        OpaqueIdV1("administrator"),
        "browser_session",
        OpaqueIdV1("session"),
        ("read:accounts", "write:accounts"),
        instant,
        instant,
        instant + timedelta(hours=12),
    )
    bearer = PrincipalV1(
        OpaqueIdV1("administrator"),
        "api_bearer",
        OpaqueIdV1("token"),
        ("write:accounts",),
        instant,
        instant,
        instant + timedelta(days=1),
    )
    read_only = PrincipalV1(
        OpaqueIdV1("administrator"),
        "api_bearer",
        OpaqueIdV1("read-token"),
        ("read:accounts",),
        instant,
        instant,
        instant + timedelta(days=1),
    )
    assert authorize(
        browser, "write:accounts", correlation_id=OpaqueIdV1("browser-write")
    ).allowed
    assert authorize(
        bearer, "write:accounts", correlation_id=OpaqueIdV1("bearer-write")
    ).allowed
    assert not authorize(
        read_only, "write:accounts", correlation_id=OpaqueIdV1("bearer-read")
    ).allowed


def test_browser_permission_registry_does_not_grant_future_scopes() -> None:
    instant = datetime(2026, 1, 1, tzinfo=UTC)
    principal = PrincipalV1(
        OpaqueIdV1("administrator"),
        "browser_session",
        OpaqueIdV1("session"),
        ("write:backup",),
        instant,
        instant,
        instant + timedelta(hours=12),
    )
    decision = AuthorizePrincipalV1()(
        principal, "write:backup", correlation_id=OpaqueIdV1("future-denial")
    )
    assert decision.allowed is False
    assert decision.reason_code == "permission_denied"


def test_authorization_fails_closed_for_corrupt_authentication_method() -> None:
    instant = datetime(2026, 1, 1, tzinfo=UTC)
    principal = PrincipalV1(
        OpaqueIdV1("administrator"),
        "api_bearer",
        OpaqueIdV1("token"),
        ("read:diagnostics",),
        instant,
        instant,
        instant + timedelta(hours=12),
    )
    # Exercise defensive authorization if an already-constructed internal
    # value is corrupted after the contract constructor has validated it.
    object.__setattr__(principal, "authentication_method", "unknown")
    decision = AuthorizePrincipalV1()(
        principal, "read:diagnostics", correlation_id=OpaqueIdV1("corrupt-method")
    )
    assert decision.allowed is False

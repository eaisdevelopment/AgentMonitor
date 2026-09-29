"""M4 alert authorization, pure constructed principals with no I/O."""

from datetime import UTC, datetime

import pytest
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.identity_access_v1 import PrincipalV1
from agentmonitor.modules.identity_access.application.authorization import (
    BROWSER_PERMISSIONS_V1,
    AuthorizePrincipalV1,
)
from agentmonitor.modules.identity_access.domain.policy import may_issue_scopes


def test_browser_administrator_can_manage_dashboard_alerts() -> None:
    when = datetime(2026, 9, 29, tzinfo=UTC)
    principal = PrincipalV1(
        OpaqueIdV1("administrator"),
        "browser_session",
        OpaqueIdV1("session"),
        BROWSER_PERMISSIONS_V1,
        when,
        when,
        None,
    )
    decision = AuthorizePrincipalV1()(
        principal, "write:alerts", correlation_id=OpaqueIdV1("alert-command")
    )
    assert decision.allowed


@pytest.mark.parametrize(
    ("scopes", "allowed"),
    [
        (("write:alerts",), True),
        (("read:status",), False),
        (("write:accounts",), False),
        (("write:tokens",), False),
        ((), False),
    ],
)
def test_bearer_alert_permission_never_implied_by_other_scopes(
    scopes: tuple[str, ...], allowed: bool
) -> None:
    when = datetime(2026, 9, 29, tzinfo=UTC)
    principal = PrincipalV1(
        OpaqueIdV1("administrator"),
        "api_bearer",
        OpaqueIdV1("token"),
        scopes,
        when,
        when,
        None,
    )
    decision = AuthorizePrincipalV1()(
        principal, "write:alerts", correlation_id=OpaqueIdV1("alert-command")
    )
    assert decision.allowed is allowed


def test_alert_scope_delegation_requires_held_alert_and_token_permissions() -> None:
    requested = frozenset({"write:alerts"})
    assert may_issue_scopes(frozenset({"write:alerts", "write:tokens"}), requested)
    assert not may_issue_scopes(
        frozenset({"write:accounts", "write:tokens"}), requested
    )
    assert not may_issue_scopes(frozenset({"write:alerts"}), requested)


@pytest.mark.parametrize(
    ("scopes", "allowed"),
    [
        (("read:alerts",), True),
        (("write:alerts",), False),
        (("read:status",), False),
    ],
)
def test_bearer_alert_read_is_independently_scoped(
    scopes: tuple[str, ...], allowed: bool
) -> None:
    when = datetime(2026, 9, 29, tzinfo=UTC)
    principal = PrincipalV1(
        OpaqueIdV1("administrator"),
        "api_bearer",
        OpaqueIdV1("token"),
        scopes,
        when,
        when,
        None,
    )
    decision = AuthorizePrincipalV1()(
        principal, "read:alerts", correlation_id=OpaqueIdV1("alert-read")
    )
    assert decision.allowed is allowed

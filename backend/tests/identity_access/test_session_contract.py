"""Published M01 session outcomes reject impossible or unsafe pairings."""

from datetime import UTC, datetime, timedelta
from inspect import signature

import pytest
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.identity_access_v1 import (
    AuthenticationFailureV1,
    BrowserSessionResolutionV1,
    IamSecurityEventViewV1,
    PrincipalV1,
    SessionMutationOutcomeV1,
    SessionSummaryV1,
)
from agentmonitor.modules.identity_access.application.sessions import (
    ListSessionsV1,
    ResolveBrowserSessionV1,
    VerifyCsrfV1,
)


def test_expiry_observing_ports_require_request_correlation() -> None:
    for port in (ResolveBrowserSessionV1, VerifyCsrfV1, ListSessionsV1):
        parameter = signature(port.__call__).parameters.get("correlation_id")
        assert parameter is not None
        assert parameter.kind.name == "KEYWORD_ONLY"


@pytest.mark.parametrize("retry", [True, 0, -1, 901])
def test_throttle_retry_is_positive_bounded_exact_integer(retry: object) -> None:
    with pytest.raises(ValueError, match="authentication_retry_pair_invalid"):
        AuthenticationFailureV1("login_throttled", retry)  # type: ignore[arg-type]


def test_failure_resolution_has_neither_principal_nor_session() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    principal = PrincipalV1(
        OpaqueIdV1("admin"),
        "browser_session",
        OpaqueIdV1("session"),
        ("read:self",),
        now,
        now,
        now + timedelta(hours=12),
    )
    summary = SessionSummaryV1(
        OpaqueIdV1("session"),
        now,
        now,
        now + timedelta(minutes=30),
        now + timedelta(hours=12),
        "active",
        True,
        1,
    )
    with pytest.raises(ValueError, match="session_resolution_pair_invalid"):
        BrowserSessionResolutionV1("dashboard_authentication_required", principal, None)
    with pytest.raises(ValueError, match="session_resolution_pair_invalid"):
        BrowserSessionResolutionV1("dashboard_authentication_required", None, summary)


def test_authenticated_resolution_requires_matching_browser_principal() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    summary = SessionSummaryV1(
        OpaqueIdV1("session-a"),
        now,
        now,
        now + timedelta(minutes=30),
        now + timedelta(hours=12),
        "active",
        True,
        1,
    )
    for method, credential_id in (
        ("api_bearer", "session-a"),
        ("browser_session", "session-b"),
    ):
        principal = PrincipalV1(
            OpaqueIdV1("admin"),
            method,  # type: ignore[arg-type]
            OpaqueIdV1(credential_id),
            ("read:self",),
            now,
            now,
            now + timedelta(hours=12),
        )
        with pytest.raises(ValueError, match="session_resolution_pair_invalid"):
            BrowserSessionResolutionV1("authenticated", principal, summary)


@pytest.mark.parametrize(
    ("count", "error"), [(True, ValueError), (-1, ValueError), (1.5, TypeError)]
)
def test_session_mutation_count_is_exact_nonnegative_integer(
    count: object, error: type[Exception]
) -> None:
    with pytest.raises(error):
        SessionMutationOutcomeV1("revoked", count)  # type: ignore[arg-type]


def test_failed_session_mutation_never_claims_affected_rows() -> None:
    with pytest.raises(ValueError, match="session_mutation_count_invalid"):
        SessionMutationOutcomeV1("csrf_validation_failed", 1)


@pytest.mark.parametrize("retry", [None, True, 0, -1, 901])
def test_password_change_throttle_retry_is_bounded_exact_integer(
    retry: object,
) -> None:
    with pytest.raises(ValueError, match="session_mutation_retry_invalid"):
        SessionMutationOutcomeV1(
            "login_throttled",
            retry_after_seconds=retry,  # type: ignore[arg-type]
        )


def test_observed_expiry_has_one_closed_audit_shape() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    event = IamSecurityEventViewV1(
        OpaqueIdV1("event"),
        "browser_session_expired",
        now,
        now,
        None,
        None,
        "session",
        OpaqueIdV1("session"),
        "expired",
        None,
        OpaqueIdV1("correlation"),
        1,
        None,
    )
    assert event.event_type == "browser_session_expired"

"""M01 V1 identity policy; deterministic decisions without I/O or framework types."""

from datetime import datetime, timedelta
from typing import Literal

PASSWORD_MIN_CODEPOINTS = 15
PASSWORD_MAX_UTF8_BYTES = 1024
M2_ISSUABLE_SCOPES = frozenset({"read:diagnostics", "write:tokens"})
TERMINAL_RETENTION_DAYS = 365


def password_creation_error(candidate: str) -> str | None:
    """Validate new administrator material without altering its Unicode form."""
    try:
        encoded_size = len(candidate.encode("utf-8"))
    except UnicodeEncodeError:
        return "invalid_unicode"
    if encoded_size > PASSWORD_MAX_UTF8_BYTES:
        return "too_large"
    if len(candidate) < PASSWORD_MIN_CODEPOINTS:
        return "too_short"
    return None


def bootstrap_state_error(
    state: Literal["uninitialized", "initialized", "incompatible"],
) -> Literal["administrator_already_initialized", "iam_repository_unavailable"] | None:
    """Only an actually uninitialized store may accept a bootstrap claim."""
    if state == "uninitialized":
        return None
    if state == "initialized":
        return "administrator_already_initialized"
    return "iam_repository_unavailable"


def session_expired(
    as_of: datetime, idle_expires_at: datetime, absolute_expires_at: datetime
) -> bool:
    """An expiry instant is exclusive; either deadline terminates the session."""
    return as_of >= idle_expires_at or as_of >= absolute_expires_at


def may_issue_scopes(
    held_scopes: frozenset[str], requested_scopes: frozenset[str]
) -> bool:
    """M2 bearer token management must be explicitly held and attenuated."""
    return (
        "write:tokens" in held_scopes
        and bool(requested_scopes)
        and requested_scopes <= held_scopes
        and requested_scopes <= M2_ISSUABLE_SCOPES
    )


def terminal_record_cutoff(as_of: datetime) -> datetime:
    """One-year retention is a fixed 365-day UTC duration for M2."""
    return as_of - timedelta(days=TERMINAL_RETENTION_DAYS)


def terminal_record_eligible(terminal_at: datetime | None, cutoff: datetime) -> bool:
    """Never purge active state; equality at cutoff is eligible."""
    return terminal_at is not None and terminal_at <= cutoff

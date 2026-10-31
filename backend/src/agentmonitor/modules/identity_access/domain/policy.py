"""M01 V1 identity policy; deterministic decisions without I/O or framework types."""

import re
from datetime import datetime, timedelta
from typing import Literal

PASSWORD_MIN_CODEPOINTS = 15
PASSWORD_MAX_UTF8_BYTES = 1024
M2_ISSUABLE_SCOPES = frozenset(
    {
        "read:accounts",
        "read:alerts",
        "write:accounts",
        "write:alerts",
        "read:diagnostics",
        "read:status",
        "read:telemetry",
        "write:tokens",
    }
)
TERMINAL_RETENTION_DAYS = 365
SESSION_IDLE_SECONDS = 86_400
SESSION_ABSOLUTE_SECONDS = 86_400
SESSION_TOUCH_SECONDS = 60
TOKEN_MIN_SECONDS = 3600
TOKEN_MAX_SECONDS = 31_536_000
TOKEN_DEFAULT_SECONDS = 7_776_000
TOKEN_TOUCH_SECONDS = 60
_CORRELATION_ID = re.compile(r"[A-Za-z0-9._:-]{1,64}\Z")


def valid_correlation_id(value: object) -> bool:
    """Accept exactly the frozen P01 request-ID grammar, not resource-ID grammar."""
    return type(value) is str and _CORRELATION_ID.fullmatch(value) is not None


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


def session_state(
    as_of: datetime,
    idle_expires_at: datetime,
    absolute_expires_at: datetime,
    revoked_at: datetime | None,
    revocation_reason: str | None,
) -> Literal["active", "expired", "revoked"]:
    """An observed terminal transition cannot resurrect on a later clock rollback."""
    if revoked_at is not None:
        return "expired" if revocation_reason == "expired" else "revoked"
    return (
        "expired"
        if session_expired(as_of, idle_expires_at, absolute_expires_at)
        else "active"
    )


def session_deadlines(
    as_of: datetime,
    *,
    absolute_expires_at: datetime | None = None,
    persisted_activity_at: datetime | None = None,
    persisted_idle_expires_at: datetime | None = None,
) -> tuple[datetime, datetime]:
    """Return persisted idle/absolute deadlines; absolute never slides."""
    if absolute_expires_at is None:
        if persisted_activity_at is not None or persisted_idle_expires_at is not None:
            raise ValueError("session_idle_window_incomplete")
        absolute = as_of + timedelta(seconds=SESSION_ABSOLUTE_SECONDS)
        idle_window = timedelta(seconds=SESSION_IDLE_SECONDS)
    else:
        if persisted_activity_at is None or persisted_idle_expires_at is None:
            raise ValueError("session_idle_window_incomplete")
        absolute = absolute_expires_at
        idle_window = persisted_idle_expires_at - persisted_activity_at
    return min(as_of + idle_window, absolute), absolute


def should_touch_session(as_of: datetime, persisted_activity_at: datetime) -> bool:
    """Only a durable 60-second activity write may slide the idle deadline."""
    return as_of >= persisted_activity_at + timedelta(seconds=SESSION_TOUCH_SECONDS)


def idempotency_receipt_expired(as_of: datetime, expires_at: datetime) -> bool:
    """Receipts become reusable at their persisted 24-hour deadline."""
    return as_of >= expires_at


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


def canonical_token_name(candidate: str) -> str | None:
    """Trim a safe display label; never use it as token identity or audit text."""
    name = candidate.strip()
    try:
        size = len(name.encode("utf-8"))
    except UnicodeEncodeError:
        return None
    if not 1 <= len(name) <= 80 or size > 256 or not name.isprintable():
        return None
    return name


def token_deadline(as_of: datetime, lifetime_seconds: int | None) -> datetime:
    """Enforce the fixed M2 issuance interval without a test/config override."""
    if lifetime_seconds is None:
        lifetime_seconds = TOKEN_DEFAULT_SECONDS
    if type(lifetime_seconds) is not int or not (
        TOKEN_MIN_SECONDS <= lifetime_seconds <= TOKEN_MAX_SECONDS
    ):
        raise ValueError("token_expiry_invalid")
    return as_of + timedelta(seconds=lifetime_seconds)


def token_state(
    as_of: datetime,
    expires_at: datetime,
    revoked_at: datetime | None,
    revocation_reason: str | None,
) -> Literal["active", "expired", "revoked", "rotated"]:
    """A recorded terminal transition wins even if the clock later retreats."""
    if revoked_at is not None:
        if revocation_reason == "expired":
            return "expired"
        if revocation_reason == "rotation":
            return "rotated"
        return "revoked"
    return "expired" if as_of >= expires_at else "active"


def token_should_touch(as_of: datetime, last_used_at: datetime | None) -> bool:
    return last_used_at is None or as_of >= last_used_at + timedelta(
        seconds=TOKEN_TOUCH_SECONDS
    )


def may_manage_token(
    held_scopes: frozenset[str], target_scopes: frozenset[str]
) -> bool:
    """A bearer may manage only targets no broader than itself."""
    return (
        "write:tokens" in held_scopes
        and target_scopes <= held_scopes
        and target_scopes <= M2_ISSUABLE_SCOPES
    )


def terminal_record_cutoff(as_of: datetime) -> datetime:
    """One-year retention is a fixed 365-day UTC duration for M2."""
    return as_of - timedelta(days=TERMINAL_RETENTION_DAYS)


def terminal_record_eligible(terminal_at: datetime | None, cutoff: datetime) -> bool:
    """Never purge active state; equality at cutoff is eligible."""
    return terminal_at is not None and terminal_at <= cutoff

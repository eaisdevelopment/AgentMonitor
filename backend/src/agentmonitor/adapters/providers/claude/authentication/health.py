"""Safe classification of fixed Claude authentication failure signals."""

from typing import Literal

ClaudeAuthFailureV1 = Literal[
    "reauthentication_required", "authorization_insufficient", "unclassified"
]

_REAUTH_SIGNALS = (
    b"please run /login",
    b"not logged in",
    b"authentication failed",
    b"authentication required",
    b"choose a login method",
)
_AUTHORIZATION_SIGNALS = (b"access denied", b"permission denied", b"unauthorized")


def classify_auth_failure(raw_lowercase: bytes) -> ClaudeAuthFailureV1:
    """Inspect only closed fixed tokens and return no provider text."""
    if any(signal in raw_lowercase for signal in _REAUTH_SIGNALS):
        return "reauthentication_required"
    if any(signal in raw_lowercase for signal in _AUTHORIZATION_SIGNALS):
        return "authorization_insufficient"
    return "unclassified"

"""Pure status policy; no keyring, HTTP, registry, or provider I/O."""

from agentmonitor.modules.registry.domain.cloud_connection_status import (
    derive_connection_status,
)


def test_verified_binding_never_claims_provider_identity() -> None:
    assert derive_connection_status(True, True, None, None, "ready", True) == (
        "access_valid_owner_confirmed",
        False,
    )


def test_unready_or_active_work_cannot_offer_verification() -> None:
    assert derive_connection_status(True, False, None, None, "ready", False) == (
        "pending",
        False,
    )
    assert derive_connection_status(True, False, "claimed", None, "busy", True) == (
        "pending",
        False,
    )
    assert derive_connection_status(True, False, None, None, "unresolved", True) == (
        "unavailable",
        False,
    )


def test_missing_binding_and_rate_limit_remain_explicit() -> None:
    assert derive_connection_status(False, False, None, None, "ready", True) == (
        "not_configured",
        False,
    )
    assert derive_connection_status(
        True, False, "terminal", "rate_limited", "not_due", True
    ) == ("rate_limited", False)


def test_completed_rate_limit_becomes_retryable_only_after_gate_is_ready() -> None:
    assert derive_connection_status(
        True, False, "terminal", "rate_limited", "ready", True
    ) == ("pending", True)

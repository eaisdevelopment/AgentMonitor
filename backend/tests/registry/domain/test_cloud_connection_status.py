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
        "unavailable",
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
    ) == ("retry_available", True)


def test_historical_verification_is_not_current_when_authorization_is_unavailable() -> (
    None
):
    assert derive_connection_status(True, True, None, None, "ready", False) == (
        "unavailable",
        False,
    )


def test_current_signal_can_invalidate_historical_access() -> None:
    from agentmonitor.modules.provider_system.domain.protocol import (
        current_access_from_signal,
    )

    assert current_access_from_signal("verified_success")
    assert not current_access_from_signal("rate_limited")
    assert not current_access_from_signal("transient_failure")
    assert not current_access_from_signal("credential_unauthorized")
    assert not current_access_from_signal("provider_schema_incompatible")
    assert not current_access_from_signal("outcome_unresolved")


def test_stale_and_transient_states_are_not_reported_as_pending() -> None:
    assert derive_connection_status(
        True, False, "terminal", "last_check_stale", "ready", True
    ) == ("stale", True)
    assert derive_connection_status(
        True, False, "terminal", "transient_failure", "ready", True
    ) == ("retry_available", True)


def test_scheduled_state_never_follows_preference_or_old_receipt_alone() -> None:
    from agentmonitor.modules.registry.domain.cloud_connection_status import (
        scheduled_monitoring_state,
    )

    assert scheduled_monitoring_state(False, True, True, True, True) == (
        "off",
        "monitoring_disabled",
    )
    assert scheduled_monitoring_state(True, False, True, True, True) == (
        "unavailable",
        "worker_unavailable",
    )
    assert scheduled_monitoring_state(True, True, True, False, True) == (
        "unavailable",
        "source_not_admitted",
    )
    assert scheduled_monitoring_state(True, True, True, True, False) == (
        "waiting",
        "schedule_not_registered",
    )
    assert scheduled_monitoring_state(True, True, True, True, True) == (
        "scheduled",
        "scheduled",
    )

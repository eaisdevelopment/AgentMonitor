"""Pure state-policy checks for the Codex dashboard connection view."""

import pytest
from agentmonitor.composition.codex_dashboard_connection import (
    resolve_codex_connection_status_v1,
)


@pytest.mark.parametrize(
    (
        "provider_key",
        "lifecycle",
        "identity_state",
        "graph_state",
        "monitoring",
        "expected",
    ),
    [
        (
            "codex",
            "pending",
            "unresolved",
            "absent",
            False,
            ("idle", True, "pending_profile"),
        ),
        (
            "codex",
            "active",
            "matched",
            "absent",
            False,
            ("idle", False, "account_not_connectable"),
        ),
        (
            "codex",
            "active",
            "owner_confirmed",
            "complete",
            False,
            ("connected", False, "account_not_connectable"),
        ),
        (
            "codex",
            "active",
            "matched",
            "complete",
            True,
            ("connected", False, "account_not_connectable"),
        ),
        (
            "claude",
            "pending",
            "unresolved",
            "absent",
            False,
            ("idle", False, "account_not_connectable"),
        ),
    ],
)
def test_no_flow_status_is_derived_without_io(
    provider_key: str,
    lifecycle: str,
    identity_state: str,
    graph_state: str,
    monitoring: bool,
    expected: tuple[str, bool, str],
) -> None:
    """M5-CDX-CONNECT-004/008/010: static account state is deterministic."""
    decision = resolve_codex_connection_status_v1(
        provider_key=provider_key,
        lifecycle=lifecycle,
        identity_state=identity_state,
        graph_state=graph_state,
        monitoring_enabled=monitoring,
        flow_state=None,
        flow_reason_code=None,
    )

    assert (decision.state, decision.can_connect, decision.reason_code) == expected


def test_wrong_account_flow_is_terminal_without_io() -> None:
    """M5-CDX-CONNECT-009: wrong-account state cannot start another flow."""
    decision = resolve_codex_connection_status_v1(
        provider_key="codex",
        lifecycle="pending",
        identity_state="unresolved",
        graph_state="absent",
        monitoring_enabled=False,
        flow_state="wrong_account",
        flow_reason_code="wrong_account_detected",
    )

    assert decision.state == "wrong_account"
    assert not decision.can_connect
    assert decision.reason_code == "wrong_account_detected"


def test_interrupted_bound_enrollment_can_resume_only_with_durable_flow() -> None:
    """M5-CDX-CONNECT-008: a bound but incomplete graph needs its flow receipt."""
    decision = resolve_codex_connection_status_v1(
        provider_key="codex",
        lifecycle="active",
        identity_state="matched",
        graph_state="absent",
        monitoring_enabled=False,
        flow_state="cancelled",
        flow_reason_code="service_restarted",
    )

    assert decision.state == "cancelled"
    assert decision.can_connect
    assert decision.reason_code == "service_restarted"


def test_complete_disabled_graph_overrides_stale_flow_state() -> None:
    """FR-ACC-003: monitoring off cannot turn a completed graph into setup."""
    decision = resolve_codex_connection_status_v1(
        provider_key="codex",
        lifecycle="active",
        identity_state="owner_confirmed",
        graph_state="complete",
        monitoring_enabled=False,
        flow_state="cancelled",
        flow_reason_code="service_restarted",
    )

    assert decision.state == "connected"
    assert not decision.can_connect
    assert decision.reason_code == "account_not_connectable"

"""Pure failure-policy checks; no provider output, process, or I/O is simulated."""

from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.adapters.providers.claude.subscription.source import (
    is_transient_claude_usage_failure_v1,
)
from agentmonitor.modules.collection_control.domain.polling import poll_is_due


@pytest.mark.parametrize(
    "code",
    [
        "usage_process_exited_before_complete_render",
        "usage_deadline_after_command_echo",
        "usage_deadline_before_command_echo",
    ],
)
def test_transient_read_waits_full_cadence_before_a_new_observation(code: str) -> None:
    """FR-COL-001/003: an interrupted read preserves bounded periodic monitoring."""
    started = datetime(2026, 11, 4, tzinfo=UTC)
    admitted = is_transient_claude_usage_failure_v1(code)
    assert not poll_is_due(
        started + timedelta(seconds=299),
        started,
        "failed",
        300,
        transient_read_failure=admitted,
    )
    assert poll_is_due(
        started + timedelta(seconds=300),
        started,
        "failed",
        300,
        transient_read_failure=admitted,
    )
    assert not poll_is_due(
        started + timedelta(days=1),
        started,
        "blocked",
        300,
        transient_read_failure=admitted,
    )


@pytest.mark.parametrize(
    "code",
    [
        None,
        "",
        "claude_reauthentication_required",
        "claude_authorization_insufficient",
        "claude_onboarding_required",
        "claude_trust_required",
        "claude_permission_denied",
        "claude_version_unverified",
        "usage_output_limit_exceeded",
        "usage_percent_invalid",
        "usage_window_set_invalid",
        "usage_process_invocation_failed",
        "usage_process_exited_before_complete_render_extra",
        "unknown_failure",
    ],
)
def test_other_failure_classes_never_gain_automatic_retry(code: str | None) -> None:
    """FR-SAFE-001: auth, user action, version and unknown failures stay closed."""
    started = datetime(2026, 11, 4, tzinfo=UTC)
    admitted = is_transient_claude_usage_failure_v1(code)
    assert not admitted
    assert not poll_is_due(
        started + timedelta(days=1),
        started,
        "failed",
        300,
        transient_read_failure=admitted,
    )

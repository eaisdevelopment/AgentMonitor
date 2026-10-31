"""Pure provider-action policy for scheduled Codex collection."""

from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.composition.codex_dashboard_collection import (
    _is_transient_failure,
    codex_tick_provider_action_v1,
)
from agentmonitor.modules.collection_control.domain.polling import poll_is_due


@pytest.mark.parametrize(
    ("source_poll_due", "expected"),
    [(False, "none"), (True, "durable_collection")],
)
def test_only_due_durable_collection_can_start_codex_provider_io(
    source_poll_due: bool,
    expected: str,
) -> None:
    """M5-CDX-COL-004: startup/restart never schedules an unadmitted read."""
    assert codex_tick_provider_action_v1(source_poll_due=source_poll_due) == expected


def test_interrupted_local_commit_allows_a_new_run_after_full_cadence() -> None:
    """M5-CDX-COL-004: a recovered local commit cannot block the account forever."""
    assert _is_transient_failure("collection_commit_interrupted") is True
    assert _is_transient_failure("codex_app_server_unavailable") is True
    assert _is_transient_failure("codex_identity_binding_unavailable") is False
    assert _is_transient_failure(None) is False


def test_timeout_allows_only_a_new_scheduled_run_after_full_cadence() -> None:
    """M5-CDX-COL-014: a timeout cannot strand an enabled account forever."""
    failed_at = datetime(2026, 10, 25, 22, 5, tzinfo=UTC)
    retryable = _is_transient_failure("codex_app_server_deadline_exceeded")
    assert retryable is True
    for elapsed, expected in ((0, False), (299, False), (300, True), (86400, True)):
        assert (
            poll_is_due(
                failed_at + timedelta(seconds=elapsed),
                failed_at,
                "failed",
                300,
                transient_read_failure=retryable,
            )
            is expected
        )
    # A later timeout resets cadence; the old failure is not replayed.
    later_attempt = failed_at + timedelta(seconds=300)
    assert not poll_is_due(
        later_attempt + timedelta(seconds=299),
        later_attempt,
        "failed",
        300,
        transient_read_failure=retryable,
    )
    for code in (
        "codex_managed_authentication_required",
        "codex_identity_binding_unavailable",
        "codex_executable_changed",
        "codex_app_server_protocol_invalid",
        "unknown_failure",
        None,
    ):
        assert not _is_transient_failure(code)
        assert not poll_is_due(
            failed_at + timedelta(days=2),
            failed_at,
            "failed",
            300,
            transient_read_failure=_is_transient_failure(code),
        )

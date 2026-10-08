"""Pure provider-action policy for scheduled Codex collection."""

import pytest
from agentmonitor.composition.codex_dashboard_collection import (
    _is_transient_failure,
    codex_tick_provider_action_v1,
)


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

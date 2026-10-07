"""Pure provider-action policy for scheduled Codex collection."""

import pytest
from agentmonitor.composition.codex_dashboard_collection import (
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

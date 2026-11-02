"""Pure generation reconciliation keeps an in-flight schedule immutable."""

import pytest

from agentmonitor.modules.collection_control.domain.ollama_rate_policy import (
    cloud_schedule_generation_action,
)


def test_generation_may_advance_only_without_active_work() -> None:
    assert cloud_schedule_generation_action(4, 4, False) == "unchanged"
    assert cloud_schedule_generation_action(4, 5, False) == "advance"
    with pytest.raises(ValueError, match="ollama_cloud_schedule_conflict"):
        cloud_schedule_generation_action(4, 3, False)
    with pytest.raises(ValueError, match="ollama_cloud_schedule_busy"):
        cloud_schedule_generation_action(4, 5, True)

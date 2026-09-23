"""Real Claude quota execution through the production M04 route."""

from datetime import timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.tests.integration.conftest import RealClaudeMonitoringContextV1


def test_real_claude_quota_collection_commits_owner_confirmed_target(
    real_claude_monitoring_context: "RealClaudeMonitoringContextV1",
) -> None:
    """M04-LIVE-004/009..011: durable admission precedes one real collection."""
    result = real_claude_monitoring_context.result

    assert result.queued_run.state == "queued"
    assert result.completed_run.state in {"succeeded", "partial"}
    assert result.completed_run.account_id == result.graph.account.account_id
    assert result.completed_run.resource_id == result.graph.resource.resource_id
    assert result.completed_run.observation_ids
    assert result.completed_run.started_at == result.collection_started_at
    assert result.completed_run.completed_at is not None
    assert result.completed_run.completed_at > result.collection_started_at
    assert result.completed_run.duration_ms is not None
    assert result.completed_run.duration_ms > 0
    assert result.collection_started_at - result.discovery_collected_at >= (
        timedelta(seconds=300)
    )

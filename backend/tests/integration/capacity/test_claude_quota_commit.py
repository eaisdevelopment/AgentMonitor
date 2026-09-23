"""Real Claude quota persistence through the production M05 sink."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.tests.integration.conftest import RealClaudeMonitoringContextV1


def test_real_claude_quota_commit_projects_current_windows_and_health(
    real_claude_monitoring_context: "RealClaudeMonitoringContextV1",
) -> None:
    """M05 live commit keeps real run/account/observation lineage intact."""
    result = real_claude_monitoring_context.result
    receipt = result.capacity_receipt

    assert receipt.run_id == result.completed_run.run_id
    assert set(receipt.observation_ids) == set(result.completed_run.observation_ids)
    assert result.capacities
    assert all(
        item.subject.account_id == result.graph.account.account_id
        for item in result.capacities
    )
    assert all(item.health is not None for item in result.capacities)
    assert result.quota_windows
    assert all(
        item.subject.account_id == result.graph.account.account_id
        and item.collection_run_id == result.completed_run.run_id
        and item.current_observation_id in receipt.observation_ids
        for item in result.quota_windows
    )

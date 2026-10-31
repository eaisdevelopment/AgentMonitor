"""Real Claude quota persistence through the production M05 sink."""

from typing import TYPE_CHECKING

from agentmonitor.adapters.providers.claude.manifest import (
    CLAUDE_ADAPTER_VERSION,
    CLAUDE_PROVIDER_VERSION,
    CLAUDE_USAGE_SOURCE_ID,
)

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
        and item.provenance.source_id == CLAUDE_USAGE_SOURCE_ID
        and item.provenance.source_class == "supported_cli"
        and item.provenance.adapter_version == CLAUDE_ADAPTER_VERSION
        and item.provenance.provider_version == CLAUDE_PROVIDER_VERSION
        and item.provenance.mechanism_version == "1"
        and item.provenance.freshness_deadline is not None
        and item.provenance.precision == "rounded"
        and item.provenance.confidence == "confirmed"
        for item in result.quota_windows
    )

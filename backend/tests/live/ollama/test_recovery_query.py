"""Real read-only M04 history query; no invented rows or provider requests."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.collection_control.sqlite.recovery import (
    SqliteCollectionRecoveryQueryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.probe_descriptor import (
    ollama_cloud_scheduled_policy,
)
from agentmonitor.contracts.collection_recovery_v1 import (
    CollectionRecoveryQueryV1,
    CollectionRecoveryScopeV1,
)


def test_actual_terminal_run_history_is_bounded_and_source_exact() -> None:
    root = Path("/home/dev/.local/share/agentmonitor")
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    registry = SqliteRegistryRepositoryV1(reference)
    cloud = SqliteCloudCredentialRegistryV1(reference)
    policy = ollama_cloud_scheduled_policy()
    accounts = registry.list_accounts("ollama", page_size=100)
    graphs = [cloud.read_monitoring_target(account.account_id) for account in accounts]
    actual = next(
        graph for graph in graphs if graph is not None and graph.lifecycle == "active"
    )
    scope = CollectionRecoveryScopeV1(
        actual.account_id,
        actual.access_target_id,
        actual.binding.generation,
        policy.capability_id,
        policy.source_id,
        policy.adapter_version,
        policy.source_fingerprint,
        policy.payload_schema,
        "ollama",
    )
    now = datetime.now(UTC)
    query = CollectionRecoveryQueryV1("ollama", now - timedelta(days=1), now, scope, 1)

    result = SqliteCollectionRecoveryQueryV1(reference).read_recovery_runs(query)

    assert len(result.items) == 1
    item = result.items[0]
    assert item.account_id == actual.account_id
    assert item.access_target_id == actual.access_target_id
    assert item.binding_generation == actual.binding.generation
    assert item.source_fingerprint == policy.source_fingerprint
    assert item.source_id == policy.source_id
    assert query.from_at <= item.requested_at < query.before_at
    assert item.completed_at < query.before_at
    assert result.has_more

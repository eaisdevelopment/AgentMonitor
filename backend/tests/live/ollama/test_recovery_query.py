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


def test_quota_continuity_query_survives_genuine_large_billing_report(
    tmp_path: Path,
) -> None:
    """A billing receipt must not prevent reading unrelated subscription runs.

    Empty quota history is valid query evidence, never successful continuity.
    """
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        open_sqlite_database,
    )

    from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
        _private_real_copy,
    )
    from tools.automation.implementations.m6_recovery_interval import _runs

    reference = _private_real_copy(tmp_path)
    now = datetime.now(UTC)
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            oversized = connection.exec_driver_sql(
                "SELECT r.provider_key,r.requested_at,count(o.observation_id) "
                "FROM collection_run r JOIN collection_run_observation_ref o "
                "ON o.run_id=r.run_id WHERE r.provider_key IN ('claude','codex') "
                "AND r.capability_id='api.usage' AND r.state='succeeded' "
                "AND r.requested_at>=? GROUP BY r.run_id "
                "HAVING count(o.observation_id)>200 "
                "ORDER BY r.requested_at DESC LIMIT 1",
                (
                    (now - timedelta(days=1))
                    .isoformat(timespec="microseconds")
                    .replace("+00:00", "Z"),
                ),
            ).first()
            assert oversized is not None, "genuine_large_billing_receipt_required"
            provider, raw_start, count = oversized
            assert count > 200
            start = datetime.fromisoformat(raw_start)
            expected = connection.exec_driver_sql(
                "SELECT run_id FROM collection_run WHERE provider_key=? "
                "AND capability_id='subscription.quota' AND requested_at>=? "
                "AND requested_at<? AND completed_at<? AND state IN "
                "('succeeded','partial','failed','blocked','cancelled','unsupported') "
                "ORDER BY requested_at DESC,run_id DESC LIMIT 501",
                (
                    provider,
                    raw_start,
                    now.isoformat(timespec="microseconds").replace("+00:00", "Z"),
                    now.isoformat(timespec="microseconds").replace("+00:00", "Z"),
                ),
            ).fetchall()
            assert len(expected) <= 500, "genuine_quota_history_bound_exceeded"

    actual = _runs(SqliteCollectionRecoveryQueryV1(reference), provider, start, now)

    assert tuple(item.run_id.value for item in actual) == tuple(
        row[0] for row in expected
    )
    assert all(item.capability_id == "subscription.quota" for item in actual)

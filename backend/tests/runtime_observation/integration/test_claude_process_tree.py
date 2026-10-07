"""ST-FLEET-003: genuine persisted Claude process/session topology."""

from datetime import UTC, datetime

from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.persistence.runtime_observation.sqlite.repository import (
    SqliteRuntimeObservationRepositoryV1,
)
from agentmonitor.modules.registry.application.accounts import ListAccountsV1
from agentmonitor.modules.runtime_observation.application.queries import (
    GetSessionTreeV1,
    ListAgentProcessesV1,
    ListAgentSessionsV1,
)

from backend.tests.integration.collection_control.fleet_support import (
    selected_owner_fleet,
)


def test_real_claude_session_tree_keeps_account_correlation_explicit() -> None:
    selected = selected_owner_fleet()
    assert all(item.disposition == "verified" for item in selected.outcomes), (
        "m4_owner_unavailable_blocks_full_fleet"
    )
    expected = {item.account_id for item in selected.outcomes}
    repository = SqliteRuntimeObservationRepositoryV1(selected.reference)
    known_accounts = {
        item.account_id.value
        for item in ListAccountsV1(SqliteRegistryRepositoryV1(selected.reference))(
            "claude"
        )
    }
    assert expected <= known_accounts
    as_of = datetime.now(UTC)
    sessions = ListAgentSessionsV1(repository)(
        provider_key="claude", as_of=as_of, page_size=200
    )
    processes = ListAgentProcessesV1(repository)(
        provider_key="claude", as_of=as_of, page_size=200
    )
    assert sessions and processes, "m4_real_claude_runtime_history_required"
    assert all(
        session.account_id is None or session.account_id in known_accounts
        for session in sessions
    ), "m4_runtime_association_orphaned"
    assert all(item.provenance.source_id for item in sessions + processes)
    assert all(item.provenance.collected_at <= as_of for item in sessions + processes)
    tree = GetSessionTreeV1(repository)(
        sessions[0].session_id,
        as_of=as_of,
        depth_limit=8,
        node_limit=200,
    )
    assert tree.root_session_id == sessions[0].session_id
    assert tree.nodes and tree.included_count == len(tree.nodes)
    assert tree.excluded_count >= 0
    assert 0 <= tree.unknown_count <= tree.included_count
    assert len({node.session.session_id for node in tree.nodes}) == len(tree.nodes)
    assert all(
        node.session.account_id is None or node.session.account_id in known_accounts
        for node in tree.nodes
    )

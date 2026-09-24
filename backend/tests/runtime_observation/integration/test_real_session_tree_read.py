"""Read-only CTR-RUN-003 checks against naturally persisted runtime data."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.runtime_observation.sqlite.repository import (
    SqliteRuntimeObservationRepositoryV1,
)
from agentmonitor.modules.runtime_observation.application.queries import (
    GetSessionTreeV1,
    ListAgentSessionsV1,
)


def _real_data_root() -> Path:
    value = os.environ.get("AGENTMONITOR_TEST_DATA_ROOT")
    if value is None:
        pytest.skip("NOT RUN: AGENTMONITOR_TEST_DATA_ROOT is not selected")
    root = Path(value)
    if not root.is_absolute():
        pytest.fail("AGENTMONITOR_TEST_DATA_ROOT must be absolute")
    return root


def test_real_persisted_session_tree_has_truthful_topology_counts() -> None:
    """M06-DB-011/API-HTTP-022: current real rows form one bounded tree view."""

    root = _real_data_root()
    repository = SqliteRuntimeObservationRepositoryV1(
        DatabaseRefV1(root / "agentmonitor.db", root)
    )
    as_of = datetime.now(UTC)
    sessions = ListAgentSessionsV1(repository)(
        provider_key="claude", as_of=as_of, page_size=200
    )
    if not sessions:
        pytest.skip("BLOCKED: selected real database has no current Claude session")

    tree = GetSessionTreeV1(repository)(
        sessions[0].session_id,
        as_of=as_of,
        depth_limit=8,
        node_limit=200,
    )

    assert tree.root_session_id == sessions[0].session_id
    assert tree.included_count == len(tree.nodes)
    assert tree.included_count >= 1
    assert tree.excluded_count >= 0
    assert 0 <= tree.unknown_count <= tree.included_count
    if len(sessions) == 1:
        assert tree.unknown_count == 1
        assert tree.nodes[0].orphan_reason is not None
    assert len({node.session.session_id for node in tree.nodes}) == len(tree.nodes)
    assert all(node.session.provenance.source_id for node in tree.nodes)
    assert all(node.session.provenance.collected_at <= as_of for node in tree.nodes)

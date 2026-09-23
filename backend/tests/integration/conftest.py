"""Shared real-provider vertical fixtures; no provider outcome is constructed."""

import os
from dataclasses import dataclass

import pytest
from _pytest.tmpdir import TempPathFactory
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.composition.claude_live_monitoring import (
    ClaudeLiveMonitoringResultV1,
    run_owner_confirmed_claude_collection,
)


@dataclass(frozen=True, slots=True)
class RealClaudeMonitoringContextV1:
    reference: DatabaseRefV1
    result: ClaudeLiveMonitoringResultV1


@pytest.fixture(scope="session")
def real_claude_monitoring_context(
    tmp_path_factory: TempPathFactory,
) -> RealClaudeMonitoringContextV1:
    opt_in = os.environ.get("AGENTMONITOR_RUN_CLAUDE_OWNER_VERTICAL")
    if opt_in is None:
        pytest.skip(
            "NOT RUN: set AGENTMONITOR_RUN_CLAUDE_OWNER_VERTICAL=1 for the "
            "two-call real Claude owner vertical"
        )
    if opt_in != "1":
        pytest.fail("claude_owner_vertical_opt_in_invalid")
    root = tmp_path_factory.mktemp("real-claude-monitoring")
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    migrate_to_head(reference)
    return RealClaudeMonitoringContextV1(
        reference,
        run_owner_confirmed_claude_collection(reference),
    )

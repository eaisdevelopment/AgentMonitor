"""Real Linux process collection through M04 into M06 persistence."""

import os
from pathlib import Path

import pytest


def _live_data_root() -> Path:
    value = os.environ.get("AGENTMONITOR_RUN_LINUX_RUNTIME_DATA_ROOT")
    if value is None:
        pytest.skip(
            "NOT RUN: set AGENTMONITOR_RUN_LINUX_RUNTIME_DATA_ROOT to the "
            "owner-approved migrated AgentMonitor data root"
        )
    root = Path(value)
    if not root.is_absolute() or root in {Path("/"), Path.home()}:
        pytest.fail("linux_runtime_data_root_invalid")
    if not (root / "agentmonitor.db").is_file():
        pytest.fail("linux_runtime_database_missing")
    return root


def test_real_linux_claude_processes_commit_through_collection_run() -> None:
    """AC-PROC-001/003: exact executable facts persist without account guessing."""
    from agentmonitor.composition.linux_runtime_monitoring import (
        run_linux_runtime_collection,
    )

    result = run_linux_runtime_collection(_live_data_root())

    assert result.inspected_process_count > 0
    assert result.completed_run.state in {"succeeded", "partial"}
    assert result.completed_run.account_id is None
    assert result.completed_run.capability_id == "local.process.observation"
    assert result.receipt.run_id == result.completed_run.run_id
    assert result.receipt.observation_ids == result.completed_run.observation_ids
    assert result.processes
    assert all(process.provider_key == "claude" for process in result.processes)
    assert all(process.installation_id is not None for process in result.processes)
    assert all(process.presence == "running" for process in result.processes)
    assert all(
        process.provenance.source_id == "linux.proc.process.v1"
        for process in result.processes
    )
    assert all(
        process.provenance.provider_version_availability.state == "available"
        for process in result.processes
    )

"""Real Ollama procfs observation commits through M04 into M06 SQLite."""

from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.composition.linux_runtime_monitoring import (
    run_ollama_runtime_collection,
)
from agentmonitor.composition.ollama_installation_reconciliation import (
    reconcile_ollama_installation_v1,
)


def test_real_ollama_processes_commit_without_account_or_model_guessing(
    tmp_path: Path,
) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    installation = reconcile_ollama_installation_v1(reference)

    result = run_ollama_runtime_collection(tmp_path)

    assert result.inspected_process_count > 0
    assert result.completed_run.state in {"succeeded", "partial"}
    assert result.completed_run.provider_key == "ollama"
    assert result.completed_run.account_id is None
    assert result.completed_run.capability_id == "local.process.observation"
    assert result.receipt.run_id == result.completed_run.run_id
    assert result.receipt.observation_ids == result.completed_run.observation_ids
    assert result.processes
    assert all(process.provider_key == "ollama" for process in result.processes)
    assert all(
        process.installation_id == installation.provider_installation_id.value
        for process in result.processes
    )
    assert all(process.presence == "running" for process in result.processes)
    assert all(
        process.provenance.source_id == "linux.proc.process.v1"
        and process.provenance.provider_key == "ollama"
        and process.provenance.confidence_reason_code
        == "exact_executable_verified_account_unresolved"
        for process in result.processes
    )
    assert all(not hasattr(process, "account_id") for process in result.processes)
    assert all(not hasattr(process, "model_id") for process in result.processes)

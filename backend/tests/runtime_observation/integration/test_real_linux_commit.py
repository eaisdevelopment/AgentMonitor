"""M06 real procfs -> production repository -> file-backed SQLite evidence."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.runtime_observation.sqlite.repository import (
    RuntimeRepositoryErrorV1,
    SqliteRuntimeObservationRepositoryV1,
)
from agentmonitor.adapters.platform.linux.processes import InspectLinuxProcessesV1
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.contracts.runtime_observation_v1 import (
    PlatformInspectionRequestV1,
    RuntimeCommitRequestV1,
    RuntimeObservationBatchV1,
)
from agentmonitor.modules.runtime_observation.application.commit import (
    CommitRuntimeCollectionOutcomeV1,
)
from agentmonitor.modules.runtime_observation.application.payload_digest import (
    runtime_payload_digest,
)
from agentmonitor.modules.runtime_observation.application.queries import (
    GetRuntimeCommitStatusV1,
    ListAgentProcessesV1,
    ListAgentSessionsV1,
    ListProcessHistoryV1,
)


def _database(tmp_path: Path) -> DatabaseRefV1:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    return reference


def _collect() -> tuple[RuntimeObservationBatchV1, ObservationProvenanceV1]:
    collection_started_at = datetime.now(UTC)
    outcome = InspectLinuxProcessesV1()(
        PlatformInspectionRequestV1(
            operation_id="m3-runtime-db",
            correlation_id="m3-runtime-db",
            provider_key=None,
            installation_id=None,
            provider_version=None,
            source_id="linux.proc.process.v1",
            selector_id="linux.proc.claude-process.v1",
            executable_identity="claude",
            requested_fields=(
                "kernel_state",
                "parent_pid",
                "resident_pages",
                "system_cpu_ticks",
                "thread_count",
                "user_cpu_ticks",
            ),
            maximum_candidates=4096,
            maximum_results=128,
            deadline_at=collection_started_at + timedelta(seconds=5),
        )
    )
    if not outcome.processes:
        pytest.skip(
            "BLOCKED / NOT RUN: no naturally running same-UID comm candidate is visible"
        )
    collected_at = datetime.now(UTC)
    batch = RuntimeObservationBatchV1(
        process_snapshots=outcome.processes,
        session_observations=(),
        correlation_evidence=(),
        completeness="partial_scope"
        if outcome.state == "partial"
        else "complete_scope",
        omission_codes=outcome.omission_codes,
    )
    provenance = ObservationProvenanceV1(
        provider_key="claude",
        capability_id="local.process.observation",
        capability_schema_version="1.0",
        adapter_id="agentmonitor.linux",
        adapter_version="1.0.0",
        provider_protocol_version="1.0.0",
        source_id="linux.proc.process.v1",
        source_class="approved_local_metadata",
        mechanism_version="1",
        parser_version="1.0.0",
        provider_version=None,
        provider_version_availability=FieldAvailabilityV1("unavailable"),
        observed_at=outcome.observed_at,
        observed_at_availability=FieldAvailabilityV1("available"),
        collected_at=collected_at,
        freshness_deadline=collected_at + timedelta(minutes=1),
        freshness_availability=FieldAvailabilityV1("available"),
        freshness_policy_id="runtime-process-one-minute-v1",
        precision="exact",
        confidence="confirmed",
        confidence_reason_code=(
            "procfs_fields_confirmed_provider_attribution_unresolved"
        ),
        value_kind="authoritative",
        is_experimental=False,
        fallback_lineage=(),
        warnings=outcome.omission_codes,
        operation_id=OpaqueIdV1("m3-runtime-db"),
        correlation_id=OpaqueIdV1("m3-runtime-db"),
        decision_reference="REF-M0-LNX-CAPABILITY-DECISIONS-001",
        derivation_method=None,
        input_observation_ids=(),
    )
    return batch, provenance


def _request(run_id: str, generation: int = 1) -> RuntimeCommitRequestV1:
    batch, provenance = _collect()
    return RuntimeCommitRequestV1(
        run_id=OpaqueIdV1(run_id),
        target_generation=generation,
        capability_id="local.process.observation",
        payload_schema="runtime-observation-batch.v1",
        payload_digest=runtime_payload_digest(batch),
        terminal_state="partial"
        if batch.completeness == "partial_scope"
        else "succeeded",
        payload=batch,
        provenance=provenance,
    )


def test_real_linux_process_commit_replays_and_queries_history(tmp_path: Path) -> None:
    """M06-DB-002/004/011 and M06-LNX-001/002: real facts persist once."""
    repository = SqliteRuntimeObservationRepositoryV1(_database(tmp_path))
    commit = CommitRuntimeCollectionOutcomeV1(repository)
    request = _request("runtime-real-run")

    first = commit(request)
    replay = commit(request)
    status = GetRuntimeCommitStatusV1(repository)(request.run_id, request.capability_id)
    processes = ListAgentProcessesV1(repository)(
        provider_key=None, as_of=datetime.now(UTC), page_size=128
    )

    assert replay == first
    assert status.state == "committed"
    assert status.receipt == first
    assert processes
    assert all(item.provider_key is None for item in processes)
    assert all(item.installation_id is None for item in processes)
    assert all(item.executable_label.value == "claude" for item in processes)
    assert all(
        item.provenance.source_id == "linux.proc.process.v1" for item in processes
    )
    assert all(item.provenance.provider_version is None for item in processes)
    assert all(item.provenance.provider_key == "claude" for item in processes)
    assert all(
        item.provenance.confidence_reason_code
        == "procfs_fields_confirmed_provider_attribution_unresolved"
        for item in processes
    )
    assert all(
        item.provenance.decision_reference == "REF-M0-LNX-CAPABILITY-DECISIONS-001"
        for item in processes
    )
    assert all(
        item.provenance.provider_version_availability.state == "unavailable"
        for item in processes
    )
    assert all(
        item.provenance.operation_id == OpaqueIdV1("m3-runtime-db")
        for item in processes
    )
    assert all(
        item.identity.pid > 0 and item.identity.start_time_ticks > 0
        for item in processes
    )
    history = ListProcessHistoryV1(repository)(
        processes[0].process_id, as_of=datetime.now(UTC), page_size=128
    )
    assert history
    assert history[0].process_id == processes[0].process_id
    assert history[0].provenance == processes[0].provenance


def test_same_run_with_new_real_payload_is_a_hard_conflict(tmp_path: Path) -> None:
    """M06-DB-005: a later real observation cannot overwrite the receipt."""
    repository = SqliteRuntimeObservationRepositoryV1(_database(tmp_path))
    commit = CommitRuntimeCollectionOutcomeV1(repository)
    first = _request("runtime-conflict-run")
    commit(first)
    second = _request("runtime-conflict-run", generation=2)
    if second.payload_digest == first.payload_digest:
        pytest.skip("BLOCKED / NOT RUN: real procfs observation did not advance")

    with pytest.raises(RuntimeRepositoryErrorV1, match="runtime_commit_conflict"):
        commit(second)


def test_empty_session_provenance_query_executes_against_real_schema(
    tmp_path: Path,
) -> None:
    """CTR-RUN-002: the provenance join is valid before a source is approved."""
    repository = SqliteRuntimeObservationRepositoryV1(_database(tmp_path))

    result = ListAgentSessionsV1(repository)(
        provider_key="claude", as_of=datetime.now(UTC), page_size=128
    )

    assert result == ()

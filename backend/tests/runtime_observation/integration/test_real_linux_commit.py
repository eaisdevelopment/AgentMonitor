"""M06 real procfs -> production repository -> file-backed SQLite evidence."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.runtime_observation.sqlite.repository import (
    RuntimeRepositoryErrorV1,
    SqliteRuntimeObservationRepositoryV1,
)
from agentmonitor.adapters.platform.linux.processes import (
    LINUX_PROCESS_ADAPTER_VERSION,
    LINUX_PROCESS_SOURCE_VERSION,
    ApprovedLinuxExecutableSelectorV1,
    InspectLinuxProcessesV1,
)
from agentmonitor.adapters.providers.claude.installation import (
    discover_default_installation,
)
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.contracts.runtime_observation_v1 import (
    PlatformInspectionRequestV1,
    RuntimeCommitRequestV1,
    RuntimeObservationBatchV1,
)
from agentmonitor.modules.runtime_observation.application.commit import (
    CommitRuntimeCollectionOutcomeV1,
    RuntimeCommitValidationErrorV1,
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
    adapter_versions = {item.adapter_version for item in outcome.processes}
    source_ids = {item.source_id for item in outcome.processes}
    assert len(adapter_versions) == 1
    assert source_ids == {"linux.proc.process.v1"}
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
        adapter_version=next(iter(adapter_versions)),
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
    snapshots_by_identity = {
        snapshot.identity: snapshot for snapshot in request.payload.process_snapshots
    }
    for process in processes:
        snapshot = snapshots_by_identity[process.identity]
        assert process.parent_pid == snapshot.parent_pid
        assert process.user_cpu_ticks == snapshot.user_cpu_ticks
        assert process.system_cpu_ticks == snapshot.system_cpu_ticks
        assert process.resident_pages == snapshot.resident_pages
        assert process.thread_count == snapshot.thread_count
        assert process.kernel_state == snapshot.kernel_state
        assert process.clock_ticks_per_second == snapshot.clock_ticks_per_second
        assert process.page_size_bytes == snapshot.page_size_bytes
        assert process.last_observed_at == snapshot.observed_at
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


def test_real_batch_terminal_state_must_match_completeness(tmp_path: Path) -> None:
    """M06-DB-003/008: contradictory outcome metadata stores no rows."""
    repository = SqliteRuntimeObservationRepositoryV1(_database(tmp_path))
    commit = CommitRuntimeCollectionOutcomeV1(repository)
    request = _request("runtime-terminal-mismatch")
    contradictory_request = (
        replace(request, terminal_state="partial")
        if request.payload.completeness == "complete_scope"
        else replace(request, terminal_state="succeeded")
    )

    with pytest.raises(
        RuntimeCommitValidationErrorV1, match="runtime_terminal_state_mismatch"
    ):
        commit(contradictory_request)

    status = GetRuntimeCommitStatusV1(repository)(request.run_id, request.capability_id)
    assert status.state == "not_committed"
    assert (
        ListAgentProcessesV1(repository)(
            provider_key=None, as_of=datetime.now(UTC), page_size=128
        )
        == ()
    )


def test_real_batch_rejects_an_incompatible_payload_schema(tmp_path: Path) -> None:
    """M06-DB-003 and NFR-COMP-001: M06 accepts only its V1 batch schema."""
    repository = SqliteRuntimeObservationRepositoryV1(_database(tmp_path))
    commit = CommitRuntimeCollectionOutcomeV1(repository)
    request = _request("runtime-schema-mismatch")

    with pytest.raises(
        RuntimeCommitValidationErrorV1, match="runtime_input_schema_incompatible"
    ):
        commit(replace(request, payload_schema="runtime-observation-batch.v2"))

    status = GetRuntimeCommitStatusV1(repository)(request.run_id, request.capability_id)
    assert status.state == "not_committed"


def test_repository_rejects_incompatible_schema_when_called_directly(
    tmp_path: Path,
) -> None:
    """M06-DB-003: persistence remains fail closed behind the application port."""
    repository = SqliteRuntimeObservationRepositoryV1(_database(tmp_path))
    request = _request("runtime-repository-schema-mismatch")

    with pytest.raises(
        RuntimeRepositoryErrorV1, match="runtime_input_schema_incompatible"
    ):
        repository.commit(
            replace(request, payload_schema="runtime-observation-batch.v2")
        )

    status = GetRuntimeCommitStatusV1(repository)(request.run_id, request.capability_id)
    assert status.state == "not_committed"


def test_repository_rejects_contradictory_terminal_state_when_called_directly(
    tmp_path: Path,
) -> None:
    """M06-DB-008: persistence cannot bypass outcome/completeness atomicity."""
    repository = SqliteRuntimeObservationRepositoryV1(_database(tmp_path))
    request = _request("runtime-repository-terminal-mismatch")
    contradictory_request = (
        replace(request, terminal_state="partial")
        if request.payload.completeness == "complete_scope"
        else replace(request, terminal_state="succeeded")
    )

    with pytest.raises(
        RuntimeRepositoryErrorV1, match="runtime_terminal_state_mismatch"
    ):
        repository.commit(contradictory_request)

    status = GetRuntimeCommitStatusV1(repository)(request.run_id, request.capability_id)
    assert status.state == "not_committed"


def test_repository_rejects_noncanonical_payload_digest_when_called_directly(
    tmp_path: Path,
) -> None:
    """M06-DB-003/005: repository callers cannot bypass digest validation."""
    repository = SqliteRuntimeObservationRepositoryV1(_database(tmp_path))
    request = _request("runtime-repository-digest-mismatch")
    mismatched_digest = "0" * 64 if request.payload_digest != "0" * 64 else "1" * 64

    with pytest.raises(
        RuntimeRepositoryErrorV1, match="runtime_payload_digest_mismatch"
    ):
        repository.commit(replace(request, payload_digest=mismatched_digest))

    status = GetRuntimeCommitStatusV1(repository)(request.run_id, request.capability_id)
    assert status.state == "not_committed"


def test_same_run_and_real_payload_with_changed_provenance_is_a_conflict(
    tmp_path: Path,
) -> None:
    """M06-DB-004/005: replay identity includes the complete safe lineage."""
    repository = SqliteRuntimeObservationRepositoryV1(_database(tmp_path))
    commit = CommitRuntimeCollectionOutcomeV1(repository)
    original = _request("runtime-provenance-conflict")
    first = commit(original)
    changed_provenance = replace(
        original.provenance,
        operation_id=OpaqueIdV1("m3-runtime-db-conflicting-operation"),
    )

    with pytest.raises(RuntimeRepositoryErrorV1, match="runtime_commit_conflict"):
        commit(replace(original, provenance=changed_provenance))

    status = GetRuntimeCommitStatusV1(repository)(
        original.run_id, original.capability_id
    )
    assert status.state == "committed"
    assert status.receipt == first


def test_real_attributed_process_fingerprint_persists_in_migrated_sqlite(
    tmp_path: Path,
) -> None:
    """M06-DB-002/003: real evidence safely upgrades frozen v1_0600."""
    reference = _database(tmp_path)
    repository = SqliteRuntimeObservationRepositoryV1(reference)
    generic_request = _request("runtime-generic-before-attribution")
    CommitRuntimeCollectionOutcomeV1(repository)(generic_request)
    generic_identities = {
        item.identity for item in generic_request.payload.process_snapshots
    }

    installation = discover_default_installation()
    selector = ApprovedLinuxExecutableSelectorV1.from_executable(
        selector_id="linux.proc.claude-process.v1",
        executable_identity="claude",
        provider_key="claude",
        installation_id=installation.installation_ref.value,
        provider_version=installation.provider_version,
        executable=installation.executable_for_adapter,
    )
    started_at = datetime.now(UTC)
    outcome = InspectLinuxProcessesV1(approved_executable_selectors=(selector,))(
        PlatformInspectionRequestV1(
            operation_id="m3-runtime-attributed-db",
            correlation_id="m3-runtime-attributed-db",
            provider_key="claude",
            installation_id=installation.installation_ref.value,
            provider_version=installation.provider_version,
            source_id="linux.proc.process.v1",
            selector_id="linux.proc.claude-process.v1",
            executable_identity="claude",
            requested_fields=("parent_pid",),
            maximum_candidates=4096,
            maximum_results=128,
            deadline_at=started_at + timedelta(seconds=5),
        )
    )
    if not outcome.processes:
        pytest.skip(
            "BLOCKED / NOT RUN: no naturally running process matches the "
            "reviewed Claude executable"
        )
    if not {item.identity for item in outcome.processes} <= generic_identities:
        pytest.skip(
            "BLOCKED / NOT RUN: attributed process identity changed between "
            "the two real observations"
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
        adapter_version=LINUX_PROCESS_ADAPTER_VERSION,
        provider_protocol_version="1.0.0",
        source_id="linux.proc.process.v1",
        source_class="approved_local_metadata",
        mechanism_version=LINUX_PROCESS_SOURCE_VERSION,
        parser_version=LINUX_PROCESS_ADAPTER_VERSION,
        provider_version=installation.provider_version,
        provider_version_availability=FieldAvailabilityV1("available"),
        observed_at=outcome.observed_at,
        observed_at_availability=FieldAvailabilityV1("available"),
        collected_at=collected_at,
        freshness_deadline=collected_at + timedelta(minutes=1),
        freshness_availability=FieldAvailabilityV1("available"),
        freshness_policy_id="runtime-process-one-minute-v1",
        precision="exact",
        confidence="confirmed",
        confidence_reason_code="exact_executable_verified_account_unresolved",
        value_kind="authoritative",
        is_experimental=False,
        fallback_lineage=(),
        warnings=outcome.omission_codes,
        operation_id=OpaqueIdV1("m3-runtime-attributed-db"),
        correlation_id=OpaqueIdV1("m3-runtime-attributed-db"),
        decision_reference="REF-M0-LNX-CAPABILITY-DECISIONS-001",
        derivation_method=None,
        input_observation_ids=(),
    )
    request = RuntimeCommitRequestV1(
        run_id=OpaqueIdV1("runtime-attributed-real-run"),
        target_generation=1,
        capability_id="local.process.observation",
        payload_schema="runtime-observation-batch.v1",
        payload_digest=runtime_payload_digest(batch),
        terminal_state="partial"
        if batch.completeness == "partial_scope"
        else "succeeded",
        payload=batch,
        provenance=provenance,
    )
    receipt = CommitRuntimeCollectionOutcomeV1(repository)(request)
    queried = ListAgentProcessesV1(repository)(
        provider_key="claude", as_of=datetime.now(UTC), page_size=128
    )

    assert receipt.observation_ids
    assert queried
    assert all(
        item.installation_id == installation.installation_ref.value for item in queried
    )
    assert all(item.parent_pid.state == "present" for item in queried)
    for item in queried:
        for field in (
            item.user_cpu_ticks,
            item.system_cpu_ticks,
            item.resident_pages,
            item.thread_count,
        ):
            assert field.state == "not_requested"
            assert field.value is None
            assert field.unit is None
            assert field.reason_code == "field_not_requested"
        assert item.kernel_state.state == "not_requested"
        assert item.kernel_state.value is None
        assert item.kernel_state.reason_code == "field_not_requested"
    expected_fingerprints = {item.executable_identity for item in outcome.processes}
    assert None not in expected_fingerprints
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            stored = set(
                connection.exec_driver_sql(
                    "SELECT p.executable_identity FROM runtime_process_instance AS p "
                    "JOIN runtime_process_snapshot AS s "
                    "ON s.process_id=p.process_id WHERE s.collection_run_id=?",
                    (request.run_id.value,),
                ).scalars()
            )
    assert stored == expected_fingerprints

    later_generic = _request("runtime-generic-after-attribution")
    attributed_identities = {item.identity for item in outcome.processes}
    later_generic_identities = {
        item.identity for item in later_generic.payload.process_snapshots
    }
    common_identities = attributed_identities & later_generic_identities
    if not common_identities:
        pytest.skip(
            "BLOCKED / NOT RUN: attributed process identity changed before "
            "the later generic observation"
        )
    CommitRuntimeCollectionOutcomeV1(repository)(later_generic)
    current_after_generic = {
        item.identity: item
        for item in ListAgentProcessesV1(repository)(
            provider_key="claude", as_of=datetime.now(UTC), page_size=128
        )
    }
    for identity in common_identities:
        current = current_after_generic[identity]
        assert current.provider_key == "claude"
        assert current.installation_id == installation.installation_ref.value
        assert current.provenance.provider_version == installation.provider_version
        assert (
            current.provenance.confidence_reason_code
            == "exact_executable_verified_account_unresolved"
        )


def test_expired_running_process_is_queried_with_unknown_presence(
    tmp_path: Path,
) -> None:
    """FR-HIST-002/R-007: expired evidence cannot claim current running state."""
    repository = SqliteRuntimeObservationRepositoryV1(_database(tmp_path))
    request = _request("runtime-expired-current-process")
    CommitRuntimeCollectionOutcomeV1(repository)(request)
    freshness_deadline = request.provenance.freshness_deadline
    assert freshness_deadline is not None

    processes = ListAgentProcessesV1(repository)(
        provider_key=None,
        as_of=freshness_deadline + timedelta(microseconds=1),
        page_size=128,
    )

    assert processes
    assert all(item.presence == "unknown" for item in processes)
    assert all(
        item.provenance.freshness_deadline == freshness_deadline for item in processes
    )


def test_empty_session_provenance_query_executes_against_real_schema(
    tmp_path: Path,
) -> None:
    """CTR-RUN-002: the provenance join is valid before a source is approved."""
    repository = SqliteRuntimeObservationRepositoryV1(_database(tmp_path))

    result = ListAgentSessionsV1(repository)(
        provider_key="claude", as_of=datetime.now(UTC), page_size=128
    )

    assert result == ()

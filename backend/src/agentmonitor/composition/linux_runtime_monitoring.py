"""One real read-only Linux Claude process collection through M04 into M06.

The composition resolves a registered installation through M02's published
application port, verifies the exact installed Claude executable, and admits a
durable M04 run before reading procfs.  Executable evidence attributes a process
to the installation only; no account, profile, or resource is inferred.
"""

from __future__ import annotations

import hashlib
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.persistence.runtime_observation.sqlite.repository import (
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
from agentmonitor.contracts.collection_control_v1 import (
    CollectionCommitReceiptV1,
    CollectionFailedV1,
    CollectionRunAdmissionV1,
    CollectionRunViewV1,
)
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    CollectionOutcomeV1,
    MissingFieldV1,
    RetryAdviceV1,
    SanitizedWarningV1,
)
from agentmonitor.contracts.runtime_observation_v1 import (
    AgentProcessRecordV1,
    PlatformInspectionOutcomeV1,
    PlatformInspectionRequestV1,
    RuntimeCommitReceiptV1,
    RuntimeCommitRequestV1,
    RuntimeObservationBatchV1,
)
from agentmonitor.modules.collection_control.application.executor import (
    ExecuteCollectionRunV1,
)
from agentmonitor.modules.collection_control.application.runner import (
    RequestManualCollectionV1,
    RunOneCollectionV1,
)
from agentmonitor.modules.registry.application.discovery import (
    ListProviderInstallationsV1,
)
from agentmonitor.modules.runtime_observation.application.commit import (
    CommitRuntimeCollectionOutcomeV1,
)
from agentmonitor.modules.runtime_observation.application.payload_digest import (
    runtime_payload_digest,
)
from agentmonitor.modules.runtime_observation.application.queries import (
    ListAgentProcessesV1,
)

_SOURCE_ID = "linux.proc.process.v1"
_SELECTOR_ID = "linux.proc.claude-process.v1"
_CAPABILITY_ID = "local.process.observation"
_PAYLOAD_SCHEMA = "runtime-observation-batch.v1"
_OWNER_PRINCIPAL_ID = "agentmonitor-owner"
_MAXIMUM_RECOVERY_RUNS = 8
_RECOVERY_OWNER_STALE_AFTER = timedelta(seconds=30)
_RECOVERY_LEASE_DURATION = timedelta(seconds=30)
_REQUESTED_FIELDS = (
    "kernel_state",
    "parent_pid",
    "resident_pages",
    "system_cpu_ticks",
    "thread_count",
    "user_cpu_ticks",
)


class LinuxRuntimeMonitoringErrorV1(RuntimeError):
    """Safe composition failure without paths, process data, or provider output."""


@dataclass(frozen=True, slots=True)
class LinuxRuntimeMonitoringResultV1:
    """Safe persisted receipts and projections from one real inspection."""

    inspected_process_count: int
    queued_run: CollectionRunViewV1
    completed_run: CollectionRunViewV1
    receipt: RuntimeCommitReceiptV1
    processes: tuple[AgentProcessRecordV1, ...]


def _digest(*values: str) -> str:
    return hashlib.sha256("\x00".join(values).encode("utf-8")).hexdigest()


def _operation_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def _registered_claude_installation(
    reference: DatabaseRefV1,
) -> tuple[OpaqueIdV1, str, int]:
    installations = ListProviderInstallationsV1(SqliteRegistryRepositoryV1(reference))(
        "claude"
    )
    current = tuple(
        installation
        for installation in installations
        if installation.provider_key == "claude"
        and installation.platform_key == "linux-x86_64"
        and installation.presence_state == "present"
        and installation.version.state == "known_masked"
        and installation.version.masked_value is not None
    )
    if len(current) != 1:
        raise LinuxRuntimeMonitoringErrorV1(
            "linux_runtime_registered_installation_unresolved"
        )
    installation = current[0]
    assert installation.version.masked_value is not None
    return (
        installation.provider_installation_id,
        installation.version.masked_value,
        installation.registry_revision,
    )


def _build_admission(
    *,
    installation_id: OpaqueIdV1,
    provider_version: str,
    registry_revision: int,
    requested_at: datetime,
    run_id: str,
    request_id: str,
    correlation_id: str,
) -> CollectionRunAdmissionV1:
    target_digest = _digest(
        "linux-runtime-target-v1",
        "claude",
        installation_id.value,
        _SOURCE_ID,
        _SELECTOR_ID,
    )
    return CollectionRunAdmissionV1(
        run_id=OpaqueIdV1(run_id),
        schedule_id=OpaqueIdV1("claude-linux-runtime-manual-schedule"),
        request_id=OpaqueIdV1(request_id),
        trigger="manual",
        operation_family="collect.local.process.observation",
        requested_capability_ids=(_CAPABILITY_ID,),
        capability_set_version="1.0.0",
        request_auth_method="owner_local_operator",
        request_principal_id=OpaqueIdV1(_OWNER_PRINCIPAL_ID),
        correlation_id=OpaqueIdV1(correlation_id),
        causation_id=None,
        target_key_digest=target_digest,
        provider_key="claude",
        installation_id=installation_id,
        account_id=None,
        profile_id=None,
        resource_id=None,
        capability_id=_CAPABILITY_ID,
        source_id=_SOURCE_ID,
        adapter_version=LINUX_PROCESS_ADAPTER_VERSION,
        provider_version=provider_version,
        adapter_protocol_version="1.0.0",
        manifest_fingerprint=_digest(
            "linux-process-manifest-v1",
            LINUX_PROCESS_ADAPTER_VERSION,
            LINUX_PROCESS_SOURCE_VERSION,
            provider_version,
        ),
        collection_policy_version="1.0.0",
        registry_revision=registry_revision,
        retry_chain_id=OpaqueIdV1(_operation_id("linux-runtime-retry-chain")),
        attempt_ordinal=1,
        target_generation=registry_revision,
        scheduler_instance_id=OpaqueIdV1("agentmonitor-local-manual"),
        lease_policy_version="1.0.0",
        budget_policy_id="local-process-inspection-v1",
        budget_policy_version="1.0.0",
        budget_scope_digest=target_digest,
        budget_dimension="local_process_inspections",
        budget_unit="inspection",
        budget_units=1,
        budget_limit_units=1,
        budget_window_start=requested_at,
        budget_window_end=requested_at + timedelta(minutes=1),
        payload_schema=_PAYLOAD_SCHEMA,
        idempotency_key_digest=_digest(request_id),
        request_digest=_digest(request_id, target_digest, _CAPABILITY_ID),
        requested_at=requested_at,
        deadline_at=requested_at + timedelta(seconds=10),
    )


def _provenance(
    *,
    outcome: PlatformInspectionOutcomeV1,
    provider_version: str,
    operation_id: str,
    correlation_id: str,
    collected_at: datetime,
) -> ObservationProvenanceV1:
    return ObservationProvenanceV1(
        provider_key="claude",
        capability_id=_CAPABILITY_ID,
        capability_schema_version="1.0",
        adapter_id="agentmonitor.linux",
        adapter_version=LINUX_PROCESS_ADAPTER_VERSION,
        provider_protocol_version="1.0.0",
        source_id=_SOURCE_ID,
        source_class="approved_local_metadata",
        mechanism_version=LINUX_PROCESS_SOURCE_VERSION,
        parser_version=LINUX_PROCESS_ADAPTER_VERSION,
        provider_version=provider_version,
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
        operation_id=OpaqueIdV1(operation_id),
        correlation_id=OpaqueIdV1(correlation_id),
        decision_reference="REF-M0-LNX-CAPABILITY-DECISIONS-001",
        derivation_method=None,
        input_observation_ids=(),
    )


def _inspection_outcome(
    *,
    inspector: InspectLinuxProcessesV1,
    request: PlatformInspectionRequestV1,
    provider_version: str,
) -> CollectionOutcomeV1[RuntimeObservationBatchV1]:
    inspected = inspector(request)
    if inspected.state not in {"success", "partial"} or not inspected.processes:
        state: Literal[
            "unsupported",
            "unverified_provider_version",
            "authorization_insufficient",
            "provider_unavailable",
            "invalid_provider_data",
            "deadline_exceeded",
            "internal_adapter_error",
        ]
        if inspected.state == "unsupported":
            state = "unsupported"
        elif inspected.state == "unverified_platform_version":
            state = "unverified_provider_version"
        elif inspected.state == "permission_denied":
            state = "authorization_insufficient"
        elif inspected.state == "deadline_exceeded":
            state = "deadline_exceeded"
        elif inspected.state in {"invalid_request", "invalid_platform_data"}:
            state = "invalid_provider_data"
        elif inspected.state == "internal_adapter_error":
            state = "internal_adapter_error"
        else:
            state = "provider_unavailable"
        retry = (
            RetryAdviceV1("after_version_review")
            if state == "unverified_provider_version"
            else RetryAdviceV1("after_user_action")
            if state == "authorization_insufficient"
            else RetryAdviceV1("never")
        )
        return CollectionOutcomeV1.failure(
            state=state,
            code=inspected.error_code or "linux_claude_process_not_observed",
            retry=retry,
        )

    collected_at = datetime.now(UTC)
    batch = RuntimeObservationBatchV1(
        process_snapshots=inspected.processes,
        session_observations=(),
        correlation_evidence=(),
        completeness=(
            "partial_scope" if inspected.omission_codes else "complete_scope"
        ),
        omission_codes=inspected.omission_codes,
    )
    provenance = _provenance(
        outcome=inspected,
        provider_version=provider_version,
        operation_id=request.operation_id,
        correlation_id=request.correlation_id,
        collected_at=collected_at,
    )
    if inspected.omission_codes:
        return CollectionOutcomeV1.partial(
            batch,
            omissions=tuple(
                MissingFieldV1(code, FieldAvailabilityV1("unavailable"))
                for code in inspected.omission_codes
            ),
            warnings=tuple(
                SanitizedWarningV1(code) for code in inspected.omission_codes
            ),
            provenance=provenance,
        )
    return CollectionOutcomeV1.success(batch, provenance)


def _prepare_commit(
    admission: CollectionRunAdmissionV1,
    outcome: CollectionOutcomeV1[RuntimeObservationBatchV1],
    completed_at: datetime,
) -> RuntimeCommitRequestV1 | CollectionFailedV1:
    if outcome.state not in {"success", "partial"}:
        assert outcome.error is not None
        terminal_state: Literal["failed", "blocked", "unsupported"] = (
            "unsupported"
            if outcome.state == "unsupported"
            else "blocked"
            if outcome.state
            in {
                "unverified_provider_version",
                "authorization_insufficient",
                "blocked_user_action_required",
            }
            else "failed"
        )
        return CollectionFailedV1(
            run_id=admission.run_id,
            terminal_state=terminal_state,
            error_code=outcome.error.code,
            completed_at=completed_at,
        )
    assert outcome.value is not None and outcome.provenance is not None
    return RuntimeCommitRequestV1(
        run_id=admission.run_id,
        target_generation=admission.target_generation,
        capability_id=admission.capability_id,
        payload_schema=admission.payload_schema,
        payload_digest=runtime_payload_digest(outcome.value),
        terminal_state="partial" if outcome.state == "partial" else "succeeded",
        payload=outcome.value,
        provenance=outcome.provenance,
    )


def recover_pending_linux_runtime_commits(
    reference: DatabaseRefV1,
    *,
    as_of: datetime,
    maximum_runs: int = _MAXIMUM_RECOVERY_RUNS,
) -> tuple[CollectionCommitReceiptV1 | CollectionFailedV1, ...]:
    """Resolve prior runtime commits through M04/M06 without reading procfs."""
    collection_repository = SqliteCollectionRepositoryV1(reference)
    runtime_repository = SqliteRuntimeObservationRepositoryV1(reference)
    executor = ExecuteCollectionRunV1[
        RuntimeObservationBatchV1, RuntimeObservationBatchV1
    ](
        collection_repository,
        CommitRuntimeCollectionOutcomeV1(runtime_repository),
    )
    return executor.recover_pending_commits(
        provider_key="claude",
        capability_id=_CAPABILITY_ID,
        source_id=_SOURCE_ID,
        as_of=as_of,
        owner_stale_before=as_of - _RECOVERY_OWNER_STALE_AFTER,
        recovery_instance_id=OpaqueIdV1(_operation_id("linux-runtime-recovery")),
        recovery_lease_expires_at=as_of + _RECOVERY_LEASE_DURATION,
        maximum_runs=maximum_runs,
    )


def run_linux_runtime_collection(data_root: Path) -> LinuxRuntimeMonitoringResultV1:
    """Inspect and persist current real Claude processes without account guessing."""
    if not data_root.is_absolute() or data_root in {Path("/"), Path.home()}:
        raise LinuxRuntimeMonitoringErrorV1("linux_runtime_data_root_invalid")
    database_path = data_root / "agentmonitor.db"
    if not database_path.is_file():
        raise LinuxRuntimeMonitoringErrorV1("linux_runtime_database_missing")
    reference = DatabaseRefV1(database_path, data_root)

    # Crash recovery is strictly database-to-database reconciliation. It runs
    # before a new run ID exists, before durable admission, and before procfs.
    recover_pending_linux_runtime_commits(reference, as_of=datetime.now(UTC))

    registered_id, registered_version, registry_revision = (
        _registered_claude_installation(reference)
    )
    discovered = discover_default_installation()
    if (
        discovered.platform_id != "linux-x86_64"
        or discovered.provider_version != registered_version
    ):
        raise LinuxRuntimeMonitoringErrorV1(
            "linux_runtime_installation_version_mismatch"
        )
    selector = ApprovedLinuxExecutableSelectorV1.from_executable(
        selector_id=_SELECTOR_ID,
        executable_identity="claude",
        provider_key="claude",
        installation_id=registered_id.value,
        provider_version=registered_version,
        executable=discovered.executable_for_adapter,
    )
    inspector = InspectLinuxProcessesV1(approved_executable_selectors=(selector,))

    requested_at = datetime.now(UTC)
    run_id = _operation_id("claude-runtime-run")
    request_id = _operation_id("claude-runtime-request")
    correlation_id = _operation_id("claude-runtime-correlation")
    admission = _build_admission(
        installation_id=registered_id,
        provider_version=registered_version,
        registry_revision=registry_revision,
        requested_at=requested_at,
        run_id=run_id,
        request_id=request_id,
        correlation_id=correlation_id,
    )
    inspection_request = PlatformInspectionRequestV1(
        operation_id=run_id,
        correlation_id=correlation_id,
        provider_key="claude",
        installation_id=registered_id.value,
        provider_version=registered_version,
        source_id=_SOURCE_ID,
        selector_id=_SELECTOR_ID,
        executable_identity="claude",
        requested_fields=_REQUESTED_FIELDS,
        maximum_candidates=16_384,
        maximum_results=512,
        deadline_at=admission.deadline_at,
    )

    collection_repository = SqliteCollectionRepositoryV1(reference)
    runtime_repository = SqliteRuntimeObservationRepositoryV1(reference)
    sink = CommitRuntimeCollectionOutcomeV1(runtime_repository)
    executor = ExecuteCollectionRunV1[
        RuntimeObservationBatchV1, RuntimeObservationBatchV1
    ](
        collection_repository,
        sink,
    )
    queued = RequestManualCollectionV1(collection_repository)(admission)
    started_at = datetime.now(UTC)
    result = RunOneCollectionV1(executor)(
        admission,
        lambda: _inspection_outcome(
            inspector=inspector,
            request=inspection_request,
            provider_version=registered_version,
        ),
        _prepare_commit,
        started_at=started_at,
        completed_at=lambda: datetime.now(UTC),
    )
    if isinstance(result, CollectionFailedV1):
        raise LinuxRuntimeMonitoringErrorV1(
            f"linux_runtime_collection_{result.error_code}"
        )
    if not isinstance(result, RuntimeCommitReceiptV1):
        raise LinuxRuntimeMonitoringErrorV1("linux_runtime_receipt_invalid")
    completed = collection_repository.get_run(admission.run_id)
    processes = ListAgentProcessesV1(runtime_repository)(
        provider_key="claude", as_of=datetime.now(UTC), page_size=500
    )
    current_ids = set(result.observation_ids)
    current_processes = tuple(
        process for process in processes if process.current_snapshot_id in current_ids
    )
    if not current_processes:
        raise LinuxRuntimeMonitoringErrorV1("linux_runtime_projection_missing")
    return LinuxRuntimeMonitoringResultV1(
        inspected_process_count=len(current_processes),
        queued_run=queued,
        completed_run=completed,
        receipt=result,
        processes=current_processes,
    )


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 2 or arguments[0] != "--data-root":
        print("invalid_operator_arguments")
        return 2
    try:
        result = run_linux_runtime_collection(Path(arguments[1]))
    except (OSError, RuntimeError, ValueError):
        print("linux_runtime_collection_failed")
        return 1
    print("linux_runtime_collection_completed")
    print(f"collection_run_id={result.completed_run.run_id.value}")
    print(f"process_count={result.inspected_process_count}")
    print("account_correlation=unresolved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

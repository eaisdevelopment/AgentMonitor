"""Real SQLite recovery for interrupted Linux runtime collection commits."""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    CollectionRepositoryErrorV1,
    SqliteCollectionRepositoryV1,
)
from agentmonitor.composition.linux_runtime_monitoring import (
    LinuxRuntimeMonitoringErrorV1,
    recover_pending_linux_runtime_commits,
    run_linux_runtime_collection,
)
from agentmonitor.contracts.collection_control_v1 import (
    CollectionFailedV1,
    CollectionRunAdmissionV1,
    CollectionRunViewV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.collection_control.application.executor import (
    CollectionExecutionErrorV1,
)

NOW = datetime(2026, 9, 23, 12, 0, tzinfo=UTC)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _runtime_admission(
    suffix: str = "one", *, requested_at: datetime = NOW
) -> CollectionRunAdmissionV1:
    return CollectionRunAdmissionV1(
        run_id=OpaqueIdV1(f"runtime-crash-run-{suffix}"),
        schedule_id=OpaqueIdV1(f"claude-linux-runtime-schedule-{suffix}"),
        request_id=OpaqueIdV1(f"runtime-crash-request-{suffix}"),
        trigger="manual",
        operation_family="collect.local.process.observation",
        requested_capability_ids=("local.process.observation",),
        capability_set_version="1.0.0",
        request_auth_method="owner_local_operator",
        request_principal_id=OpaqueIdV1("agentmonitor-owner"),
        correlation_id=OpaqueIdV1(f"runtime-crash-correlation-{suffix}"),
        causation_id=None,
        target_key_digest=_sha256(f"target-{suffix}"),
        provider_key="claude",
        installation_id=OpaqueIdV1("claude-installation-one"),
        account_id=None,
        profile_id=None,
        resource_id=None,
        capability_id="local.process.observation",
        source_id="linux.proc.process.v1",
        adapter_version="1.1.0",
        provider_version="2.1.278",
        adapter_protocol_version="1.0.0",
        manifest_fingerprint="2" * 64,
        collection_policy_version="1.0.0",
        registry_revision=1,
        retry_chain_id=OpaqueIdV1(f"runtime-crash-retry-chain-{suffix}"),
        attempt_ordinal=1,
        target_generation=1,
        scheduler_instance_id=OpaqueIdV1(f"runtime-crash-scheduler-{suffix}"),
        lease_policy_version="1.0.0",
        budget_policy_id="local-process-inspection-v1",
        budget_policy_version="1.0.0",
        budget_scope_digest=_sha256(f"budget-{suffix}"),
        budget_dimension="local_process_inspections",
        budget_unit="inspection",
        budget_units=1,
        budget_limit_units=1,
        budget_window_start=requested_at,
        budget_window_end=requested_at + timedelta(minutes=1),
        payload_schema="runtime-observation-batch.v1",
        idempotency_key_digest=_sha256(f"idempotency-{suffix}"),
        request_digest=_sha256(f"request-{suffix}"),
        requested_at=requested_at,
        deadline_at=requested_at + timedelta(seconds=10),
    )


def test_runtime_startup_recovers_committing_run_without_new_dispatch(
    tmp_path: Path,
) -> None:
    """M04-DB-019: restart resolves M06 absence and releases M04 admission."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    repository = SqliteCollectionRepositoryV1(reference)
    admission = _runtime_admission()
    run = repository.admit_run(admission)
    repository.mark_running(run.run_id, NOW, fencing_token=run.fencing_token)
    repository.mark_committing(
        run.run_id,
        fencing_token=run.fencing_token,
        payload_digest="5" * 64,
        committing_at=NOW,
        terminal_state="succeeded",
    )

    recovered = recover_pending_linux_runtime_commits(
        reference,
        as_of=NOW + timedelta(seconds=41),
        maximum_runs=8,
    )

    assert tuple(result.run_id for result in recovered) == (run.run_id,)
    recovered_run = recovered[0]
    assert isinstance(recovered_run, CollectionFailedV1)
    assert recovered_run.terminal_state == "failed"
    assert recovered_run.error_code == "collection_commit_interrupted"
    resolved = repository.get_run(run.run_id)
    assert resolved.state == "failed"
    assert resolved.fencing_token > run.fencing_token
    assert repository.get_admission_state(run.run_id) == (
        "released",
        "expired_conservative",
    )
    runs = repository.list_runs("claude", None, NOW + timedelta(seconds=41), 10)
    assert len(runs) == 1


def test_unexpired_active_runtime_commit_is_not_recovered(tmp_path: Path) -> None:
    """M04-DB-026: a live owner's unexpired fencing lease remains authoritative."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    repository = SqliteCollectionRepositoryV1(reference)
    admission = _runtime_admission()
    run = repository.admit_run(admission)
    repository.mark_running(run.run_id, NOW, fencing_token=run.fencing_token)
    repository.mark_committing(
        run.run_id,
        fencing_token=run.fencing_token,
        payload_digest="5" * 64,
        committing_at=NOW,
        terminal_state="succeeded",
    )

    recovered = recover_pending_linux_runtime_commits(
        reference,
        as_of=NOW + timedelta(seconds=1),
        maximum_runs=8,
    )

    assert recovered == ()
    untouched = repository.get_run(run.run_id)
    assert untouched.state == "committing"
    assert untouched.fencing_token == run.fencing_token
    assert repository.get_admission_state(run.run_id) == (
        "active",
        "dispatched",
    )


def test_expired_runtime_lease_with_recent_owner_is_not_recovered(
    tmp_path: Path,
) -> None:
    """M04-DB-026: expiry alone cannot fence a recently live owner."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    repository = SqliteCollectionRepositoryV1(reference)
    admission = _runtime_admission()
    run = repository.admit_run(admission)
    repository.mark_running(run.run_id, NOW, fencing_token=run.fencing_token)
    repository.mark_committing(
        run.run_id,
        fencing_token=run.fencing_token,
        payload_digest="5" * 64,
        committing_at=NOW,
        terminal_state="succeeded",
    )

    recovered = recover_pending_linux_runtime_commits(
        reference,
        as_of=NOW + timedelta(seconds=11),
        maximum_runs=8,
    )

    assert recovered == ()
    untouched = repository.get_run(run.run_id)
    assert untouched.state == "committing"
    assert untouched.fencing_token == run.fencing_token


def test_expired_stale_runtime_commit_is_atomically_refenced_once(
    tmp_path: Path,
) -> None:
    """M04-DB-012/026: one recovery owner wins and the old fence is rejected."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    repository = SqliteCollectionRepositoryV1(reference)
    admission = _runtime_admission()
    run = repository.admit_run(admission)
    repository.mark_running(run.run_id, NOW, fencing_token=run.fencing_token)
    repository.mark_committing(
        run.run_id,
        fencing_token=run.fencing_token,
        payload_digest="5" * 64,
        committing_at=NOW,
        terminal_state="succeeded",
    )
    barrier = Barrier(2)
    recovery_at = NOW + timedelta(seconds=41)

    def claim(index: int) -> tuple[CollectionRunViewV1, ...]:
        claimant = SqliteCollectionRepositoryV1(reference)
        barrier.wait()
        return claimant.claim_expired_committing_runs(
            provider_key="claude",
            capability_id="local.process.observation",
            source_id="linux.proc.process.v1",
            as_of=recovery_at,
            owner_stale_before=recovery_at - timedelta(seconds=30),
            recovery_instance_id=OpaqueIdV1(f"recovery-scheduler-{index}"),
            recovery_lease_expires_at=recovery_at + timedelta(seconds=30),
            limit=1,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = tuple(pool.map(claim, range(2)))

    assert sorted(len(claimed) for claimed in claims) == [0, 1]
    claimed_run = next(claimed[0] for claimed in claims if claimed)
    assert claimed_run.fencing_token > run.fencing_token

    interruption = CollectionFailedV1(
        run_id=run.run_id,
        terminal_state="failed",
        error_code="collection_commit_interrupted",
        completed_at=recovery_at,
    )
    with pytest.raises(
        CollectionRepositoryErrorV1,
        match="collection_fencing_conflict",
    ):
        repository.finalize_interrupted(
            interruption,
            fencing_token=run.fencing_token,
        )

    repository.finalize_interrupted(
        interruption,
        fencing_token=claimed_run.fencing_token,
    )
    assert repository.get_run(run.run_id).state == "failed"


def test_runtime_recovery_is_bounded(
    tmp_path: Path,
) -> None:
    """M04-DB-019: each invocation resolves at most its approved batch."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    repository = SqliteCollectionRepositoryV1(reference)
    admissions = (
        _runtime_admission("one"),
        _runtime_admission("two", requested_at=NOW + timedelta(seconds=1)),
    )
    runs = tuple(repository.admit_run(admission) for admission in admissions)
    for run, admission in zip(runs, admissions, strict=True):
        repository.mark_running(
            run.run_id,
            admission.requested_at,
            fencing_token=run.fencing_token,
        )
        repository.mark_committing(
            run.run_id,
            fencing_token=run.fencing_token,
            payload_digest="5" * 64,
            committing_at=admission.requested_at,
            terminal_state="succeeded",
        )

    with pytest.raises(
        CollectionExecutionErrorV1,
        match="collection_commit_recovery_batch_incomplete",
    ):
        recover_pending_linux_runtime_commits(
            reference,
            as_of=NOW + timedelta(seconds=42),
            maximum_runs=1,
        )

    assert repository.get_run(runs[0].run_id).state == "failed"
    assert repository.get_run(runs[1].run_id).state == "committing"

    with pytest.raises(
        CollectionExecutionErrorV1,
        match="collection_commit_recovery_batch_incomplete",
    ):
        recover_pending_linux_runtime_commits(
            reference,
            as_of=NOW + timedelta(seconds=42),
            maximum_runs=1,
        )

    assert repository.get_run(runs[1].run_id).state == "failed"
    assert (
        recover_pending_linux_runtime_commits(
            reference,
            as_of=NOW + timedelta(seconds=42),
            maximum_runs=1,
        )
        == ()
    )


def test_normal_runtime_invocation_recovers_before_new_admission(
    tmp_path: Path,
) -> None:
    """AC-OPS-005: production startup recovery precedes all new runtime work."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    repository = SqliteCollectionRepositoryV1(reference)
    started_at = datetime.now(UTC) - timedelta(seconds=60)
    admission = _runtime_admission(requested_at=started_at)
    run = repository.admit_run(admission)
    repository.mark_running(
        run.run_id,
        started_at,
        fencing_token=run.fencing_token,
    )
    repository.mark_committing(
        run.run_id,
        fencing_token=run.fencing_token,
        payload_digest="5" * 64,
        committing_at=started_at,
        terminal_state="succeeded",
    )

    with pytest.raises(
        LinuxRuntimeMonitoringErrorV1,
        match="linux_runtime_registered_installation_unresolved",
    ):
        run_linux_runtime_collection(tmp_path)

    assert repository.get_run(run.run_id).state == "failed"
    assert repository.get_admission_state(run.run_id) == (
        "released",
        "expired_conservative",
    )
    runs = repository.list_runs("claude", None, datetime.now(UTC), 10)
    assert tuple(item.run_id for item in runs) == (run.run_id,)

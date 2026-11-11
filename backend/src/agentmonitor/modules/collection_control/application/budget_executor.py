"""M04 billing orchestration using existing run leases and receipt reconciliation."""

from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from agentmonitor.contracts.capacity_v1 import (
    BudgetCollectionInputV1,
    BudgetReportInputV1,
)
from agentmonitor.contracts.collection_control_v1 import (
    BudgetCollectionCommitPortV1,
    BudgetCollectionCommitStatusV1,
    BudgetCollectionReceiptV1,
    BudgetCollectionRunAdmissionV1,
    BudgetCollectionRunViewV1,
    CollectionFailedV1,
    CollectionFailurePolicyV1,
    CollectionRunViewV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import CollectionOutcomeV1
from agentmonitor.modules.collection_control.application.executor import (
    CollectionExecutionErrorV1,
    CollectionRunRepositoryV1,
)


class BudgetRunRepositoryV1(CollectionRunRepositoryV1, Protocol):
    """Additive internal M04 owner-fenced variants; quota consumers stay intact."""

    def assert_claimed_budget_run(
        self,
        admission: BudgetCollectionRunAdmissionV1,
        as_of: datetime,
    ) -> BudgetCollectionRunViewV1: ...

    def mark_running(
        self,
        run_id: OpaqueIdV1,
        started_at: datetime,
        *,
        fencing_token: int,
        scheduler_instance_id: OpaqueIdV1 | None = None,
    ) -> None: ...

    def mark_committing(
        self,
        run_id: OpaqueIdV1,
        *,
        fencing_token: int,
        payload_digest: str,
        committing_at: datetime,
        terminal_state: str,
        scheduler_instance_id: OpaqueIdV1 | None = None,
    ) -> None: ...

    def finalize_failed(
        self,
        failure: CollectionFailedV1,
        *,
        fencing_token: int,
        provider_policy: CollectionFailurePolicyV1 | None = None,
        scheduler_instance_id: OpaqueIdV1 | None = None,
    ) -> None: ...

    def finalize_before_dispatch(
        self,
        failure: CollectionFailedV1,
        *,
        fencing_token: int,
        scheduler_instance_id: OpaqueIdV1 | None = None,
    ) -> None: ...

    def finalize_interrupted(
        self,
        failure: CollectionFailedV1,
        *,
        fencing_token: int,
        scheduler_instance_id: OpaqueIdV1 | None = None,
    ) -> None: ...

    def finalize_budget_committed(
        self,
        receipt: BudgetCollectionReceiptV1,
        *,
        terminal_state: str,
        completed_at: datetime,
        fencing_token: int,
        scheduler_instance_id: OpaqueIdV1,
    ) -> None: ...

    def claim_expired_budget_runs(
        self,
        *,
        provider_key: str,
        capability_id: str,
        source_id: str,
        as_of: datetime,
        owner_stale_before: datetime,
        recovery_instance_id: OpaqueIdV1,
        recovery_lease_expires_at: datetime,
        limit: int,
    ) -> tuple[BudgetCollectionRunViewV1, ...]: ...

    def claim_expired_committing_runs(
        self,
        *,
        provider_key: str,
        capability_id: str,
        source_id: str,
        as_of: datetime,
        owner_stale_before: datetime,
        recovery_instance_id: OpaqueIdV1,
        recovery_lease_expires_at: datetime,
        limit: int,
        budget_only: bool = False,
    ) -> tuple[CollectionRunViewV1, ...]: ...


def _budget_view(run: CollectionRunViewV1) -> BudgetCollectionRunViewV1:
    if not isinstance(run, BudgetCollectionRunViewV1):
        raise CollectionExecutionErrorV1("budget_run_view_required")
    return run


def reconcile_budget_receipt(
    run: BudgetCollectionRunViewV1,
    status: BudgetCollectionCommitStatusV1,
    completed_at: datetime,
    *,
    interruption_claimed: bool = False,
) -> BudgetCollectionReceiptV1 | CollectionFailedV1:
    """Pure receipt decision; never collect again or synthesize an observation."""
    if run.state != "committing" or run.outcome_code not in {"succeeded", "partial"}:
        raise CollectionExecutionErrorV1("collection_commit_recovery_invalid")
    if status.state == "not_committed":
        if interruption_claimed is not True:
            raise CollectionExecutionErrorV1("collection_commit_recovery_pending")
        return CollectionFailedV1(
            run.run_id, "failed", "collection_commit_interrupted", completed_at
        )
    if status.state == "unavailable":
        raise CollectionExecutionErrorV1("collection_commit_recovery_pending")
    receipt = status.receipt
    if (
        status.state != "committed"
        or receipt is None
        or receipt.run_id != run.run_id
        or receipt.target_generation != run.target_generation
        or receipt.capability_id != run.capability_id
        or receipt.payload_schema != "budget.report.v1"
        or receipt.payload_digest != run.payload_digest
        or receipt.stored_at > completed_at
    ):
        raise CollectionExecutionErrorV1("collection_commit_recovery_invalid")
    return receipt


class ExecuteBudgetCollectionRunV1:
    """One bounded report per run; provider I/O stays outside repository calls.

    Composition adapts the real provider result into the existing typed M03
    outcome, and supplies its real M05 sink. No alternate job engine is created.
    """

    def __init__(
        self,
        repository: BudgetRunRepositoryV1,
        sink: BudgetCollectionCommitPortV1[BudgetCollectionInputV1],
    ) -> None:
        self._repository = repository
        self._sink = sink

    def execute(
        self,
        admission: BudgetCollectionRunAdmissionV1,
        collect: Callable[[], CollectionOutcomeV1[BudgetReportInputV1]],
        normalize: Callable[
            [
                BudgetCollectionRunAdmissionV1,
                CollectionOutcomeV1[BudgetReportInputV1],
                datetime,
            ],
            BudgetCollectionInputV1 | CollectionFailedV1,
        ],
        *,
        started_at: datetime,
        completed_at: datetime | Callable[[], datetime],
    ) -> BudgetCollectionReceiptV1 | CollectionFailedV1:
        admitted = _budget_view(self._repository.admit_run(admission))
        if admitted.state == "committing":
            completion = completed_at() if callable(completed_at) else completed_at
            return self._recover_committing(
                admitted, completion, admission.scheduler_instance_id
            )
        if admitted.state != "queued" or admitted.run_id != admission.run_id:
            raise CollectionExecutionErrorV1("collection_run_not_dispatchable")
        self._repository.mark_running(
            admitted.run_id,
            started_at,
            fencing_token=admitted.fencing_token,
            scheduler_instance_id=admission.scheduler_instance_id,
        )
        return self._collect_and_commit(
            admission, admitted, collect, normalize, completed_at
        )

    def execute_claimed(
        self,
        admission: BudgetCollectionRunAdmissionV1,
        collect: Callable[[], CollectionOutcomeV1[BudgetReportInputV1]],
        normalize: Callable[
            [
                BudgetCollectionRunAdmissionV1,
                CollectionOutcomeV1[BudgetReportInputV1],
                datetime,
            ],
            BudgetCollectionInputV1 | CollectionFailedV1,
        ],
        *,
        as_of: datetime,
        completed_at: datetime | Callable[[], datetime],
    ) -> BudgetCollectionReceiptV1 | CollectionFailedV1:
        """Use an atomically running claim; never admit or dispatch it a second time."""
        admitted = self._repository.assert_claimed_budget_run(admission, as_of)
        if admitted.state != "running" or admitted.run_id != admission.run_id:
            raise CollectionExecutionErrorV1("collection_run_not_dispatchable")
        return self._collect_and_commit(
            admission, admitted, collect, normalize, completed_at
        )

    def _collect_and_commit(
        self,
        admission: BudgetCollectionRunAdmissionV1,
        admitted: BudgetCollectionRunViewV1,
        collect: Callable[[], CollectionOutcomeV1[BudgetReportInputV1]],
        normalize: Callable[
            [
                BudgetCollectionRunAdmissionV1,
                CollectionOutcomeV1[BudgetReportInputV1],
                datetime,
            ],
            BudgetCollectionInputV1 | CollectionFailedV1,
        ],
        completed_at: datetime | Callable[[], datetime],
    ) -> BudgetCollectionReceiptV1 | CollectionFailedV1:
        collected = collect()
        completion = completed_at() if callable(completed_at) else completed_at
        outcome = normalize(admission, collected, completion)
        if isinstance(outcome, CollectionFailedV1):
            if outcome.run_id != admitted.run_id:
                raise CollectionExecutionErrorV1("collection_outcome_run_mismatch")
            self._repository.finalize_failed(
                outcome,
                fencing_token=admitted.fencing_token,
                scheduler_instance_id=admission.scheduler_instance_id,
                provider_policy=(
                    CollectionFailurePolicyV1(collected.state, collected.error.retry)
                    if collected.error is not None
                    and collected.state not in {"success", "partial"}
                    else None
                ),
            )
            return outcome
        if (
            not isinstance(outcome, BudgetCollectionInputV1)
            or outcome.run_id != admitted.run_id
            or outcome.target_generation != admission.target_generation
            or outcome.capability_id != admission.capability_id
            or outcome.payload_schema != admission.payload_schema
        ):
            raise CollectionExecutionErrorV1("collection_outcome_identity_mismatch")
        self._repository.mark_committing(
            admitted.run_id,
            fencing_token=admitted.fencing_token,
            scheduler_instance_id=admission.scheduler_instance_id,
            payload_digest=outcome.payload_digest,
            committing_at=completion,
            terminal_state=outcome.terminal_state,
        )
        receipt = self._sink.commit(outcome)
        final_time = completed_at() if callable(completed_at) else completed_at
        self._repository.finalize_budget_committed(
            receipt,
            terminal_state=outcome.terminal_state,
            completed_at=max(final_time, receipt.stored_at),
            fencing_token=admitted.fencing_token,
            scheduler_instance_id=admission.scheduler_instance_id,
        )
        return receipt

    def recover_commit(
        self, admission: BudgetCollectionRunAdmissionV1, *, completed_at: datetime
    ) -> BudgetCollectionReceiptV1 | CollectionFailedV1:
        admitted = _budget_view(self._repository.admit_run(admission))
        return self._recover_committing(
            admitted, completed_at, admission.scheduler_instance_id
        )

    def recover_expired_runs(
        self,
        *,
        provider_key: str,
        capability_id: str,
        source_id: str,
        as_of: datetime,
        owner_stale_before: datetime,
        recovery_instance_id: OpaqueIdV1,
        recovery_lease_expires_at: datetime,
        maximum_runs: int,
    ) -> tuple[CollectionFailedV1, ...]:
        """Finish interrupted pre-commit work; never assert a provider outcome."""
        if type(maximum_runs) is not int or not 1 <= maximum_runs <= 64:
            raise CollectionExecutionErrorV1("collection_commit_recovery_limit_invalid")
        pending = self._repository.claim_expired_budget_runs(
            provider_key=provider_key,
            capability_id=capability_id,
            source_id=source_id,
            as_of=as_of,
            owner_stale_before=owner_stale_before,
            recovery_instance_id=recovery_instance_id,
            recovery_lease_expires_at=recovery_lease_expires_at,
            limit=maximum_runs,
        )
        results: list[CollectionFailedV1] = []
        for run in pending:
            if run.state not in {"queued", "running"}:
                raise CollectionExecutionErrorV1("collection_run_not_recoverable")
            failure = CollectionFailedV1(
                run.run_id,
                "failed",
                "collection_queued_expired"
                if run.state == "queued"
                else "collection_worker_interrupted",
                as_of,
            )
            if run.state == "queued":
                self._repository.finalize_before_dispatch(
                    failure,
                    fencing_token=run.fencing_token,
                    scheduler_instance_id=recovery_instance_id,
                )
            else:
                self._repository.finalize_failed(
                    failure,
                    fencing_token=run.fencing_token,
                    scheduler_instance_id=recovery_instance_id,
                )
            results.append(failure)
        if len(pending) == maximum_runs:
            raise CollectionExecutionErrorV1(
                "collection_commit_recovery_batch_incomplete"
            )
        return tuple(results)

    def recover_pending_commits(
        self,
        *,
        provider_key: str,
        capability_id: str,
        source_id: str,
        as_of: datetime,
        owner_stale_before: datetime,
        recovery_instance_id: OpaqueIdV1,
        recovery_lease_expires_at: datetime,
        maximum_runs: int,
    ) -> tuple[BudgetCollectionReceiptV1 | CollectionFailedV1, ...]:
        if type(maximum_runs) is not int or not 1 <= maximum_runs <= 64:
            raise CollectionExecutionErrorV1("collection_commit_recovery_limit_invalid")
        pending = self._repository.claim_expired_committing_runs(
            provider_key=provider_key,
            capability_id=capability_id,
            source_id=source_id,
            as_of=as_of,
            owner_stale_before=owner_stale_before,
            recovery_instance_id=recovery_instance_id,
            recovery_lease_expires_at=recovery_lease_expires_at,
            limit=maximum_runs,
            budget_only=True,
        )
        recovered = tuple(
            self._recover_committing(
                _budget_view(run),
                as_of,
                recovery_instance_id,
                interruption_claimed=True,
            )
            for run in pending
        )
        if len(pending) == maximum_runs:
            raise CollectionExecutionErrorV1(
                "collection_commit_recovery_batch_incomplete"
            )
        return recovered

    def _recover_committing(
        self,
        run: BudgetCollectionRunViewV1,
        completed_at: datetime,
        scheduler_instance_id: OpaqueIdV1,
        *,
        interruption_claimed: bool = False,
    ) -> BudgetCollectionReceiptV1 | CollectionFailedV1:
        status = self._sink.get_commit_status(run.run_id, run.capability_id)
        result = reconcile_budget_receipt(
            run, status, completed_at, interruption_claimed=interruption_claimed
        )
        if isinstance(result, CollectionFailedV1):
            self._repository.finalize_interrupted(
                result,
                fencing_token=run.fencing_token,
                scheduler_instance_id=scheduler_instance_id,
            )
        else:
            assert run.outcome_code is not None
            self._repository.finalize_budget_committed(
                result,
                terminal_state=run.outcome_code,
                completed_at=completed_at,
                fencing_token=run.fencing_token,
                scheduler_instance_id=scheduler_instance_id,
            )
        return result

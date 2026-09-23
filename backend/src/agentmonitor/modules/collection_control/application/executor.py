"""M04 orchestration that keeps provider I/O outside persistence transactions."""

from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from agentmonitor.contracts.collection_control_v1 import (
    CollectionCommitReceiptV1,
    CollectionFailedV1,
    CollectionOutcomeCommitPortV1,
    CollectionOutcomeCommitV1,
    CollectionRunAdmissionV1,
    CollectionRunViewV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1, TechnicalValueV1
from agentmonitor.contracts.provider_system_v1 import CollectionOutcomeV1


class CollectionRunRepositoryV1(Protocol):
    def admit_run(self, admission: CollectionRunAdmissionV1) -> CollectionRunViewV1: ...

    def mark_running(
        self, run_id: OpaqueIdV1, started_at: datetime, *, fencing_token: int
    ) -> None: ...

    def mark_committing(
        self,
        run_id: OpaqueIdV1,
        *,
        fencing_token: int,
        payload_digest: str,
        committing_at: datetime,
        terminal_state: str,
    ) -> None: ...

    def finalize_committed(
        self,
        receipt: CollectionCommitReceiptV1,
        *,
        terminal_state: str,
        completed_at: datetime,
        fencing_token: int,
    ) -> None: ...

    def finalize_failed(
        self, failure: CollectionFailedV1, *, fencing_token: int
    ) -> None: ...

    def finalize_interrupted(
        self, failure: CollectionFailedV1, *, fencing_token: int
    ) -> None: ...


class CollectionExecutionErrorV1(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ExecuteCollectionRunV1[SourceT: TechnicalValueV1, PayloadT: TechnicalValueV1]:
    """Admit, collect, commit once, then and only then finalize the M04 run."""

    def __init__(
        self,
        repository: CollectionRunRepositoryV1,
        sink: CollectionOutcomeCommitPortV1[PayloadT],
    ) -> None:
        self._repository = repository
        self._sink = sink

    def execute(
        self,
        admission: CollectionRunAdmissionV1,
        collect: Callable[[], CollectionOutcomeV1[SourceT]],
        normalize: Callable[
            [CollectionRunAdmissionV1, CollectionOutcomeV1[SourceT], datetime],
            CollectionOutcomeCommitV1[PayloadT] | CollectionFailedV1,
        ],
        *,
        started_at: datetime,
        completed_at: datetime,
    ) -> CollectionCommitReceiptV1 | CollectionFailedV1:
        """Run the injected real collector after durable admission.

        ``collect`` is invoked between repository calls, never from within a
        repository transaction. Composition must inject one approved real
        provider adapter, not a fallback chain or test double.
        """
        admitted = self._repository.admit_run(admission)
        if admitted.state == "committing":
            return self._recover_committing(admitted, completed_at)
        if admitted.state != "queued":
            raise CollectionExecutionErrorV1("collection_run_not_dispatchable")
        self._repository.mark_running(
            admission.run_id,
            started_at,
            fencing_token=admitted.fencing_token,
        )
        outcome = normalize(admission, collect(), completed_at)
        if isinstance(outcome, CollectionFailedV1):
            if outcome.run_id != admission.run_id:
                raise CollectionExecutionErrorV1("collection_outcome_run_mismatch")
            self._repository.finalize_failed(
                outcome, fencing_token=admitted.fencing_token
            )
            return outcome
        if (
            outcome.run_id != admission.run_id
            or outcome.target_generation != admission.target_generation
            or outcome.capability_id != admission.capability_id
            or outcome.payload_schema != admission.payload_schema
        ):
            raise CollectionExecutionErrorV1("collection_outcome_identity_mismatch")
        self._repository.mark_committing(
            admission.run_id,
            fencing_token=admitted.fencing_token,
            payload_digest=outcome.payload_digest,
            committing_at=completed_at,
            terminal_state=outcome.terminal_state,
        )
        receipt = self._sink.commit(outcome)
        self._repository.finalize_committed(
            receipt,
            terminal_state=outcome.terminal_state,
            completed_at=completed_at,
            fencing_token=admitted.fencing_token,
        )
        return receipt

    def recover_commit(
        self,
        admission: CollectionRunAdmissionV1,
        *,
        completed_at: datetime,
    ) -> CollectionCommitReceiptV1 | CollectionFailedV1:
        """Resolve a durable committing run without invoking a provider."""
        admitted = self._repository.admit_run(admission)
        if admitted.state != "committing":
            raise CollectionExecutionErrorV1("collection_run_not_recoverable")
        return self._recover_committing(admitted, completed_at)

    def _recover_committing(
        self, admitted: CollectionRunViewV1, completed_at: datetime
    ) -> CollectionCommitReceiptV1 | CollectionFailedV1:
        status = self._sink.get_commit_status(admitted.run_id, admitted.capability_id)
        if status.state == "not_committed":
            interrupted = CollectionFailedV1(
                run_id=admitted.run_id,
                terminal_state="failed",
                error_code="collection_commit_interrupted",
                completed_at=completed_at,
            )
            self._repository.finalize_interrupted(
                interrupted,
                fencing_token=admitted.fencing_token,
            )
            return interrupted
        if status.state == "unavailable":
            raise CollectionExecutionErrorV1("collection_commit_recovery_pending")
        if status.state == "conflict" or status.receipt is None:
            raise CollectionExecutionErrorV1("collection_commit_recovery_invalid")
        if admitted.outcome_code not in {"succeeded", "partial"}:
            raise CollectionExecutionErrorV1("collection_commit_recovery_invalid")
        self._repository.finalize_committed(
            status.receipt,
            terminal_state=admitted.outcome_code,
            completed_at=completed_at,
            fencing_token=admitted.fencing_token,
        )
        return status.receipt

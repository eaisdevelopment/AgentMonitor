"""Reconcile abandoned observation workers without asserting provider outcomes."""

from datetime import datetime, timedelta
from typing import Protocol

from agentmonitor.contracts.collection_control_v1 import (
    CollectionFailedV1,
    CollectionRunViewV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


class ExpiredSourceRunRepositoryV1(Protocol):
    def claim_expired_running_runs(
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
    ) -> tuple[CollectionRunViewV1, ...]: ...

    def finalize_failed(
        self,
        failure: CollectionFailedV1,
        *,
        fencing_token: int,
        scheduler_instance_id: OpaqueIdV1,
    ) -> None: ...


class RecoverExpiredSourceRunsV1:
    """Only an expired deadline, lease and stale owner permit a new fence."""

    def __init__(self, repository: ExpiredSourceRunRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self,
        *,
        provider_key: str,
        capability_id: str,
        source_id: str,
        as_of: datetime,
        owner_stale_before: datetime,
        recovery_instance_id: OpaqueIdV1,
    ) -> tuple[CollectionFailedV1, ...]:
        pending = self._repository.claim_expired_running_runs(
            provider_key=provider_key,
            capability_id=capability_id,
            source_id=source_id,
            as_of=as_of,
            owner_stale_before=owner_stale_before,
            recovery_instance_id=recovery_instance_id,
            recovery_lease_expires_at=as_of + timedelta(seconds=30),
            limit=16,
        )
        failures = []
        for run in pending:
            if run.state != "running":
                raise ValueError("collection_run_not_recoverable")
            failure = CollectionFailedV1(
                run.run_id, "failed", "collection_worker_interrupted", as_of
            )
            self._repository.finalize_failed(
                failure,
                fencing_token=run.fencing_token,
                scheduler_instance_id=recovery_instance_id,
            )
            failures.append(failure)
        if len(pending) == 16:
            raise ValueError("collection_recovery_batch_incomplete")
        return tuple(failures)

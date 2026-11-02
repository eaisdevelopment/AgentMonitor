"""M04 single-run boundary for composition-owned scheduling."""

from collections.abc import Callable
from datetime import datetime

from agentmonitor.contracts.collection_control_v1 import (
    CollectionCommitReceiptV1,
    CollectionFailedV1,
    CollectionOutcomeCommitV1,
    CollectionRunAdmissionV1OrV2,
    CollectionRunViewV1,
)
from agentmonitor.contracts.common_v1 import TechnicalValueV1
from agentmonitor.contracts.provider_system_v1 import CollectionOutcomeV1
from agentmonitor.modules.collection_control.application.executor import (
    CollectionRunRepositoryV1,
    ExecuteCollectionRunV1,
)


class RequestManualCollectionV1:
    """Persist a complete owner-authorized manual admission before dispatch."""

    def __init__(self, repository: CollectionRunRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self, admission: CollectionRunAdmissionV1OrV2
    ) -> CollectionRunViewV1:
        if admission.trigger != "manual":
            raise ValueError("manual_collection_trigger_required")
        if admission.request_principal_id is None:
            raise ValueError("manual_collection_principal_required")
        return self._repository.admit_run(admission)


class AdmitScheduledCollectionV1:
    """Persist a scheduler-authorized admission before provider execution."""

    def __init__(self, repository: CollectionRunRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self, admission: CollectionRunAdmissionV1OrV2
    ) -> CollectionRunViewV1:
        if admission.trigger != "scheduled":
            raise ValueError("scheduled_collection_trigger_required")
        return self._repository.admit_run(admission)


class RunOneCollectionV1[SourceT: TechnicalValueV1, PayloadT: TechnicalValueV1]:
    """No loop or clock is hidden here; runtime owns lifecycle and timing."""

    def __init__(self, executor: ExecuteCollectionRunV1[SourceT, PayloadT]) -> None:
        self._executor = executor

    def __call__(
        self,
        admission: CollectionRunAdmissionV1OrV2,
        collect: Callable[[], CollectionOutcomeV1[SourceT]],
        normalize: Callable[
            [CollectionRunAdmissionV1OrV2, CollectionOutcomeV1[SourceT], datetime],
            CollectionOutcomeCommitV1[PayloadT] | CollectionFailedV1,
        ],
        *,
        started_at: datetime,
        completed_at: datetime | Callable[[], datetime],
    ) -> CollectionCommitReceiptV1 | CollectionFailedV1:
        return self._executor.execute(
            admission,
            collect,
            normalize,
            started_at=started_at,
            completed_at=completed_at,
        )

"""M06 runtime ingestion entry point."""

from agentmonitor.contracts.runtime_observation_v1 import (
    RuntimeCommitReceiptV1,
    RuntimeCommitRequestV1,
)
from agentmonitor.modules.runtime_observation.application.commit import (
    CommitRuntimeCollectionOutcomeV1,
)


class IngestRuntimeObservationBatchV1:
    def __init__(self, commit: CommitRuntimeCollectionOutcomeV1) -> None:
        self._commit = commit

    def __call__(self, request: RuntimeCommitRequestV1) -> RuntimeCommitReceiptV1:
        return self._commit(request)

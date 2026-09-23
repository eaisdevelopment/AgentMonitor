"""M06 implementation of the M04 collection outcome commit port."""

from typing import Protocol

from agentmonitor.contracts.collection_control_v1 import (
    CollectionCommitReceiptV1,
    CollectionCommitStatusV1,
    CollectionOutcomeCommitV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.runtime_observation_v1 import (
    RuntimeCommitReceiptV1,
    RuntimeCommitRequestV1,
    RuntimeCommitStatusV1,
    RuntimeObservationBatchV1,
)
from agentmonitor.modules.runtime_observation.application.payload_digest import (
    runtime_payload_digest,
)


class RuntimeCommitValidationErrorV1(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class RuntimeCommitRepositoryV1(Protocol):
    def commit(self, request: RuntimeCommitRequestV1) -> RuntimeCommitReceiptV1: ...

    def get_commit_status(
        self, run_id: OpaqueIdV1, capability_id: str
    ) -> RuntimeCommitStatusV1: ...


class CommitRuntimeCollectionOutcomeV1:
    """Validate the canonical digest and delegate one atomic durable commit."""

    def __init__(self, repository: RuntimeCommitRepositoryV1) -> None:
        self._repository = repository

    def __call__(self, request: RuntimeCommitRequestV1) -> RuntimeCommitReceiptV1:
        if runtime_payload_digest(request.payload) != request.payload_digest:
            raise RuntimeCommitValidationErrorV1("runtime_payload_digest_mismatch")
        return self._repository.commit(request)

    def commit(
        self, request: CollectionOutcomeCommitV1[RuntimeObservationBatchV1]
    ) -> CollectionCommitReceiptV1:
        if not isinstance(request, RuntimeCommitRequestV1):
            raise RuntimeCommitValidationErrorV1("runtime_commit_request_type_invalid")
        return self(request)

    def get_commit_status(
        self, run_id: OpaqueIdV1, capability_id: str
    ) -> CollectionCommitStatusV1:
        return self._repository.get_commit_status(run_id, capability_id)

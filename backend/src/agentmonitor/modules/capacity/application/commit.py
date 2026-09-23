"""M05 typed capacity commit application boundary."""

from typing import Protocol

from agentmonitor.contracts.capacity_v1 import (
    CapacityCommitReceiptV1,
    CapacityCommitRequestV1,
    ProviderQuotaInputV1,
)
from agentmonitor.contracts.collection_control_v1 import (
    CollectionCommitReceiptV1,
    CollectionOutcomeCommitV1,
)
from agentmonitor.modules.capacity.domain.payload_digest import capacity_payload_digest


class CapacityCommitValidationErrorV1(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def validate_capacity_payload_digest(
    payload: ProviderQuotaInputV1, claimed_digest: str
) -> None:
    """Reject any caller digest that does not cover the canonical payload."""
    if capacity_payload_digest(payload) != claimed_digest:
        raise CapacityCommitValidationErrorV1("capacity_payload_digest_mismatch")


class CapacityCommitRepositoryV1(Protocol):
    def commit(self, request: CapacityCommitRequestV1) -> CapacityCommitReceiptV1: ...


class CommitCapacityCollectionOutcomeV1:
    """Route one validated quota batch to exactly one durable M05 sink."""

    def __init__(self, repository: CapacityCommitRepositoryV1) -> None:
        self._repository = repository

    def __call__(self, request: CapacityCommitRequestV1) -> CapacityCommitReceiptV1:
        validate_capacity_payload_digest(request.payload, request.payload_digest)
        return self._repository.commit(request)

    def commit(
        self, request: CollectionOutcomeCommitV1[ProviderQuotaInputV1]
    ) -> CollectionCommitReceiptV1:
        """Implement the M04 sink verb without weakening the M05 request type."""
        if not isinstance(request, CapacityCommitRequestV1):
            raise CapacityCommitValidationErrorV1(
                "capacity_commit_request_type_invalid"
            )
        return self(request)

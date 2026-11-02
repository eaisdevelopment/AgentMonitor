"""M04 application boundary for global Ollama cloud request admission."""

from datetime import datetime
from typing import Protocol

from agentmonitor.contracts.collection_control_v1 import (
    OllamaCloudAdmissionDecisionV1,
    OllamaCloudRateGateViewV1,
    OllamaCloudRequestAcquireV1,
    OllamaCloudRequestCompletionV1,
    OllamaCloudVerificationAcquireV1,
    OllamaCloudVerificationClaimRequestV1,
    OllamaCloudVerificationClaimTerminalV1,
    OllamaCloudVerificationEnqueueV1,
    OllamaCloudVerificationInterruptionProofV1,
    OllamaCloudVerificationJobClaimV1,
    OllamaCloudVerificationJobViewV1,
    OllamaCloudVerificationStatusV1,
    OllamaCloudVerificationTargetV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    CredentialBindingVerificationReceiptV1,
)


class OllamaCloudAdmissionRepositoryV1(Protocol):
    """Durable port; implementations must serialize one provider-global gate."""

    def acquire(
        self, request: OllamaCloudRequestAcquireV1
    ) -> OllamaCloudAdmissionDecisionV1: ...

    def register_verification_target(
        self, target: OllamaCloudVerificationTargetV1
    ) -> None: ...

    def acquire_verification(
        self, request: OllamaCloudVerificationAcquireV1
    ) -> OllamaCloudAdmissionDecisionV1: ...

    def enqueue_verification(
        self, request: OllamaCloudVerificationEnqueueV1
    ) -> OllamaCloudVerificationJobViewV1: ...

    def claim_verification(
        self, request: OllamaCloudVerificationClaimRequestV1
    ) -> OllamaCloudVerificationJobClaimV1 | None: ...

    def acquire_claimed_verification(
        self,
        claim: OllamaCloudVerificationJobClaimV1,
        request: OllamaCloudVerificationAcquireV1,
    ) -> OllamaCloudAdmissionDecisionV1: ...

    def finish_verification_claim(
        self, terminal: OllamaCloudVerificationClaimTerminalV1
    ) -> OllamaCloudVerificationJobViewV1: ...

    def read_verification_status(
        self,
        account_id: OpaqueIdV1,
        binding_generation: int,
        queried_at: datetime,
    ) -> OllamaCloudVerificationStatusV1: ...

    def pending_verification_finalizations(
        self,
        limit: int = 32,
        *,
        after_job_id: OpaqueIdV1 | None = None,
    ) -> tuple[OllamaCloudVerificationJobViewV1, ...]: ...

    def finalize_verification_success(
        self, receipt: CredentialBindingVerificationReceiptV1
    ) -> OllamaCloudVerificationJobViewV1: ...

    def finalize_verification_interrupted(
        self, proof: OllamaCloudVerificationInterruptionProofV1
    ) -> OllamaCloudVerificationJobViewV1: ...

    def complete(
        self, completion: OllamaCloudRequestCompletionV1
    ) -> OllamaCloudRateGateViewV1: ...


class AcquireOllamaCloudRequestV1:
    """Admit one exact request start; all other decisions prohibit dispatch."""

    def __init__(self, repository: OllamaCloudAdmissionRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self, request: OllamaCloudRequestAcquireV1
    ) -> OllamaCloudAdmissionDecisionV1:
        return self._repository.acquire(request)


class AcquireOllamaCloudVerificationV1:
    """Register and admit one explicit verification target; no source I/O."""

    def __init__(self, repository: OllamaCloudAdmissionRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self,
        target: OllamaCloudVerificationTargetV1,
        request: OllamaCloudVerificationAcquireV1,
    ) -> OllamaCloudAdmissionDecisionV1:
        if (
            target.schedule_id != request.schedule_id
            or target.account_id != request.account_id
            or target.target_generation != request.target_generation
        ):
            raise ValueError("ollama_cloud_verification_target_mismatch")
        self._repository.register_verification_target(target)
        return self._repository.acquire_verification(request)


class EnqueueOllamaCloudVerificationV1:
    """Persist an owner request without doing keyring or provider I/O."""

    def __init__(self, repository: OllamaCloudAdmissionRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self, request: OllamaCloudVerificationEnqueueV1
    ) -> OllamaCloudVerificationJobViewV1:
        return self._repository.enqueue_verification(request)


class ClaimOllamaCloudVerificationV1:
    """Claim one due job with a short pre-admission fence."""

    def __init__(self, repository: OllamaCloudAdmissionRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self, request: OllamaCloudVerificationClaimRequestV1
    ) -> OllamaCloudVerificationJobClaimV1 | None:
        return self._repository.claim_verification(request)


class AcknowledgeOllamaCloudVerificationClaimV1:
    """Atomically associate a live job claim with CTR-COL-008 admission."""

    def __init__(self, repository: OllamaCloudAdmissionRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self,
        claim: OllamaCloudVerificationJobClaimV1,
        request: OllamaCloudVerificationAcquireV1,
    ) -> OllamaCloudAdmissionDecisionV1:
        return self._repository.acquire_claimed_verification(claim, request)


class FinishUnadmittedOllamaCloudVerificationV1:
    """Persist a fenced no-request terminal before any rate admission exists."""

    def __init__(self, repository: OllamaCloudAdmissionRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self, terminal: OllamaCloudVerificationClaimTerminalV1
    ) -> OllamaCloudVerificationJobViewV1:
        return self._repository.finish_verification_claim(terminal)


class ReadOllamaCloudVerificationStatusV1:
    """Return one binding's job and authoritative provider-global gate state."""

    def __init__(self, repository: OllamaCloudAdmissionRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self,
        account_id: OpaqueIdV1,
        binding_generation: int,
        queried_at: datetime,
    ) -> OllamaCloudVerificationStatusV1:
        return self._repository.read_verification_status(
            account_id, binding_generation, queried_at
        )


class CompleteOllamaCloudRequestV1:
    """Persist sanitized terminal timing before another start is admitted."""

    def __init__(self, repository: OllamaCloudAdmissionRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self, completion: OllamaCloudRequestCompletionV1
    ) -> OllamaCloudRateGateViewV1:
        return self._repository.complete(completion)


class ListPendingOllamaCloudVerificationFinalizationsV1:
    """Read a bounded receipt-reconciliation batch without provider access."""

    def __init__(self, repository: OllamaCloudAdmissionRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self,
        limit: int = 32,
        *,
        after_job_id: OpaqueIdV1 | None = None,
    ) -> tuple[OllamaCloudVerificationJobViewV1, ...]:
        return self._repository.pending_verification_finalizations(
            limit, after_job_id=after_job_id
        )


class FinalizeOllamaCloudVerificationSuccessV1:
    """Accept one genuine M02 receipt after its exact M04 run committed."""

    def __init__(self, repository: OllamaCloudAdmissionRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self, receipt: CredentialBindingVerificationReceiptV1
    ) -> OllamaCloudVerificationJobViewV1:
        return self._repository.finalize_verification_success(receipt)


class FinalizeInterruptedOllamaCloudVerificationV1:
    """Accept trusted no-commit/no-receipt proof for one failed M04 run."""

    def __init__(self, repository: OllamaCloudAdmissionRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self, proof: OllamaCloudVerificationInterruptionProofV1
    ) -> OllamaCloudVerificationJobViewV1:
        return self._repository.finalize_verification_interrupted(proof)

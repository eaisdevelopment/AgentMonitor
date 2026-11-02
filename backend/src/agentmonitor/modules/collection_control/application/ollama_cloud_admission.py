"""M04 application boundary for global Ollama cloud request admission."""

from typing import Protocol

from agentmonitor.contracts.collection_control_v1 import (
    OllamaCloudAdmissionDecisionV1,
    OllamaCloudRateGateViewV1,
    OllamaCloudRequestAcquireV1,
    OllamaCloudRequestCompletionV1,
    OllamaCloudVerificationAcquireV1,
    OllamaCloudVerificationTargetV1,
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


class CompleteOllamaCloudRequestV1:
    """Persist sanitized terminal timing before another start is admitted."""

    def __init__(self, repository: OllamaCloudAdmissionRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self, completion: OllamaCloudRequestCompletionV1
    ) -> OllamaCloudRateGateViewV1:
        return self._repository.complete(completion)

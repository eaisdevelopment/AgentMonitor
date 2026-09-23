"""Fail-closed Claude local-session ports pending an approved M0 source join."""

from agentmonitor.contracts.provider_system_v1 import (
    CollectionOutcomeV1,
    ProviderOperationRequestHeaderV1,
    RetryAdviceV1,
)
from agentmonitor.contracts.runtime_observation_v1 import RuntimeObservationBatchV1


def _not_approved(code: str) -> CollectionOutcomeV1[RuntimeObservationBatchV1]:
    return CollectionOutcomeV1.failure(
        state="unsupported",
        code=code,
        retry=RetryAdviceV1("never"),
    )


def _invalid_scope() -> CollectionOutcomeV1[RuntimeObservationBatchV1]:
    return CollectionOutcomeV1.failure(
        state="unsupported",
        code="claude_runtime_request_scope_invalid",
        retry=RetryAdviceV1("never"),
    )


class ClaudeLocalSessionDiscoveryV1:
    """M03 local-session discovery seam; performs no I/O until M0 approves it."""

    def __call__(
        self, request: ProviderOperationRequestHeaderV1
    ) -> CollectionOutcomeV1[RuntimeObservationBatchV1]:
        if (
            request.provider_key != "claude"
            or request.capability_id != "local.session.discovery"
        ):
            return _invalid_scope()
        return _not_approved("claude_local_session_discovery_capability_not_approved")


class ClaudeLocalSessionMetricsV1:
    """M03 local-session metric seam; performs no I/O until M0 approves it."""

    def __call__(
        self, request: ProviderOperationRequestHeaderV1
    ) -> CollectionOutcomeV1[RuntimeObservationBatchV1]:
        if (
            request.provider_key != "claude"
            or request.capability_id != "local.session.metrics"
        ):
            return _invalid_scope()
        return _not_approved("claude_local_session_metrics_capability_not_approved")

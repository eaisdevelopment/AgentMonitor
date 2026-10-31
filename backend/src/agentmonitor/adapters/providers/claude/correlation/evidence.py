"""Fail-closed Claude process-correlation port for the current M0 handoff."""

from agentmonitor.contracts.provider_system_v1 import (
    CollectionOutcomeV1,
    ProviderOperationRequestHeaderV1,
    RetryAdviceV1,
)
from agentmonitor.contracts.runtime_observation_v1 import RuntimeObservationBatchV1


class ClaudeLocalProcessCorrelationV1:
    """Keep account correlation unresolved; no targeted-profile evidence exists."""

    def __call__(
        self, request: ProviderOperationRequestHeaderV1
    ) -> CollectionOutcomeV1[RuntimeObservationBatchV1]:
        if (
            request.provider_key != "claude"
            or request.capability_id != "local.process.correlation"
        ):
            return CollectionOutcomeV1.failure(
                state="unsupported",
                code="claude_runtime_request_scope_invalid",
                retry=RetryAdviceV1("never"),
            )
        return CollectionOutcomeV1.failure(
            state="unsupported",
            code="claude_process_correlation_capability_deferred",
            retry=RetryAdviceV1("never"),
        )

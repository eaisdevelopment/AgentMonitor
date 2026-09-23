"""Claude local-session ports and official OTLP session-count mapping."""

import hashlib

from agentmonitor.adapters.providers.claude.telemetry.otlp_http_json import (
    CLAUDE_OTLP_PARSER_VERSION,
    CLAUDE_OTLP_SOURCE_ID,
    CLAUDE_OTLP_SOURCE_VERSION,
    ClaudeOtlpSessionCountV1,
)
from agentmonitor.contracts.provider_system_v1 import (
    CollectionOutcomeV1,
    ProviderOperationRequestHeaderV1,
    RetryAdviceV1,
)
from agentmonitor.contracts.runtime_observation_v1 import (
    AgentProcessRecordV1,
    CorrelationEvidenceInputV1,
    LocalSessionObservationInputV1,
    ProcessSnapshotInputV1,
    RuntimeObservationBatchV1,
    SessionIdentityV1,
    SessionProcessLinkInputV1,
)

CLAUDE_OTLP_ACCOUNT_RULE_ID = "claude.otel.authenticated-account.v1"


def _id(*values: str) -> str:
    return hashlib.sha256("\x1f".join(values).encode()).hexdigest()


def map_otel_session_count(
    metric: ClaudeOtlpSessionCountV1,
    process: ProcessSnapshotInputV1 | AgentProcessRecordV1,
    *,
    provider_version: str,
    bound_account_id: str | None = None,
    bound_account_fingerprint: str | None = None,
) -> RuntimeObservationBatchV1:
    """Map one authenticated official metric; unbound account stays unresolved."""
    if (
        process.identity != metric.process_identity
        or process.provider_key != "claude"
        or process.installation_id != metric.installation_id
        or metric.provider_version != provider_version
    ):
        raise ValueError("claude_otel_process_identity_mismatch")
    if (bound_account_id is None) != (bound_account_fingerprint is None):
        raise ValueError("claude_otel_account_binding_incomplete")
    if (
        bound_account_fingerprint is not None
        and metric.observed_account_fingerprint != bound_account_fingerprint
    ):
        raise ValueError("claude_otel_account_binding_mismatch")
    session = SessionIdentityV1(
        provider_key="claude",
        installation_id=metric.installation_id,
        identity_kind="otel.session.sha256",
        identity_value=metric.session_fingerprint,
    )
    common = (
        metric.launch_id,
        metric.session_fingerprint,
        str(metric.process_identity.pid),
    )
    session_observation = LocalSessionObservationInputV1(
        observation_id=_id("claude-otel-session", *common),
        session_identity=session,
        observed_at=metric.observed_at,
        source_id=CLAUDE_OTLP_SOURCE_ID,
        source_version=CLAUDE_OTLP_SOURCE_VERSION,
        parser_version=CLAUDE_OTLP_PARSER_VERSION,
        provider_version=provider_version,
        activity_state="present",
        activity_code="session_started",
        activity_reason_code=None,
    )
    evidence = CorrelationEvidenceInputV1(
        evidence_id=_id("claude-otel-account", *common),
        session_identity=session,
        evidence_class="strong" if bound_account_id is not None else "corroborated",
        rule_id=CLAUDE_OTLP_ACCOUNT_RULE_ID,
        account_id=bound_account_id,
        observed_at=metric.observed_at,
        source_id=CLAUDE_OTLP_SOURCE_ID,
        source_version=CLAUDE_OTLP_SOURCE_VERSION,
        reason_code=(
            "exact_bound_authenticated_account"
            if bound_account_id is not None
            else "authenticated_account_binding_required"
        ),
    )
    link = SessionProcessLinkInputV1(
        link_id=_id("claude-otel-process-link", *common),
        session_identity=session,
        process_identity=metric.process_identity,
        relationship_kind="primary",
        evidence_class="strong",
        certainty="definitive",
        source_id=CLAUDE_OTLP_SOURCE_ID,
        source_version=CLAUDE_OTLP_SOURCE_VERSION,
        observed_at=metric.observed_at,
    )
    return RuntimeObservationBatchV1(
        # The independently verified A04 process snapshot is committed under
        # its own source provenance before this A01 batch.  The M06 link then
        # resolves the exact ProcessIdentityV1 against that durable instance.
        process_snapshots=(),
        session_observations=(session_observation,),
        correlation_evidence=(evidence,),
        session_process_links=(link,),
        completeness="complete_scope",
    )


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

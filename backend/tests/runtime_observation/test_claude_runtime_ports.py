"""Fail-closed A01 runtime port conformance for the current M0 handoff."""

from datetime import UTC, datetime

import pytest
from agentmonitor.adapters.providers.claude.correlation.evidence import (
    ClaudeLocalProcessCorrelationV1,
)
from agentmonitor.adapters.providers.claude.local_sessions.source import (
    ClaudeLocalSessionDiscoveryV1,
    ClaudeLocalSessionMetricsV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    CapabilitySchemaVersionV1,
    LocalProcessCorrelationPortV1,
    LocalSessionDiscoveryPortV1,
    LocalSessionMetricsPortV1,
    ProviderOperationRequestHeaderV1,
    ProviderTargetV1,
    SourcePolicyV1,
)


def _request(provider_key: str, capability_id: str) -> ProviderOperationRequestHeaderV1:
    return ProviderOperationRequestHeaderV1(
        operation_id=OpaqueIdV1("runtime-port-operation"),
        correlation_id=OpaqueIdV1("runtime-port-correlation"),
        provider_key=provider_key,
        capability_id=capability_id,
        capability_schema_version=CapabilitySchemaVersionV1(1, 0),
        target=ProviderTargetV1(
            provider_key=provider_key,
            installation_ref=OpaqueIdV1("installation-opaque"),
            account_ref=None,
            profile_ref=None,
            resource_ref=None,
            profile_protection="unknown",
        ),
        requested_at=datetime(2026, 9, 22, 12, tzinfo=UTC),
        deadline_ms=5_000,
        source_policy=SourcePolicyV1(
            policy_ref=OpaqueIdV1("runtime-policy"),
            source_ids=("linux.proc.process.v1",),
            approved_fallbacks=(),
            experimental_grant_ref=None,
        ),
        access_grant_refs=(OpaqueIdV1("runtime-read-grant"),),
    )


@pytest.mark.parametrize(
    ("port", "protocol_type", "capability_id"),
    [
        (
            ClaudeLocalSessionDiscoveryV1(),
            LocalSessionDiscoveryPortV1,
            "local.session.discovery",
        ),
        (
            ClaudeLocalSessionMetricsV1(),
            LocalSessionMetricsPortV1,
            "local.session.metrics",
        ),
        (
            ClaudeLocalProcessCorrelationV1(),
            LocalProcessCorrelationPortV1,
            "local.process.correlation",
        ),
    ],
)
def test_claude_runtime_ports_reject_another_provider_before_io(
    port: object, protocol_type: type[object], capability_id: str
) -> None:
    assert isinstance(port, protocol_type)
    outcome = port(_request("codex", capability_id))  # type: ignore[operator]

    assert outcome.state == "unsupported"
    assert outcome.error is not None
    assert outcome.error.code == "claude_runtime_request_scope_invalid"


@pytest.mark.parametrize(
    ("port", "capability_id", "error_code"),
    [
        (
            ClaudeLocalSessionDiscoveryV1(),
            "local.session.discovery",
            "claude_local_session_discovery_capability_not_approved",
        ),
        (
            ClaudeLocalSessionMetricsV1(),
            "local.session.metrics",
            "claude_local_session_metrics_capability_not_approved",
        ),
        (
            ClaudeLocalProcessCorrelationV1(),
            "local.process.correlation",
            "claude_process_correlation_capability_deferred",
        ),
    ],
)
def test_current_claude_runtime_ports_are_not_invokable_without_m0_approval(
    port: object, capability_id: str, error_code: str
) -> None:
    outcome = port(_request("claude", capability_id))  # type: ignore[operator]

    assert outcome.state == "unsupported"
    assert outcome.value is None
    assert outcome.provenance is None
    assert outcome.error is not None
    assert outcome.error.code == error_code
    assert outcome.error.retry.disposition == "never"

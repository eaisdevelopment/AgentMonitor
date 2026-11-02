"""Pure classification for exact M04 Ollama cloud source signals."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from agentmonitor.contracts.collection_control_v1 import (
    InvalidCollectionControlV1,
    OllamaCloudLatestSourceSignalQueryV1,
    OllamaCloudLatestSourceSignalV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.collection_control.domain.ollama_verification import (
    classify_latest_ollama_cloud_source_signal_v1,
)

NOW = datetime(2026, 11, 2, 22, 0, tzinfo=UTC)


def query() -> OllamaCloudLatestSourceSignalQueryV1:
    return OllamaCloudLatestSourceSignalQueryV1(
        account_id=OpaqueIdV1("account"),
        binding_generation=3,
        access_target_id=OpaqueIdV1("amat_" + "1" * 32),
        capability_id="subscription.quota",
        source_id="ollama.cloud.balance.v1",
        adapter_version="1.1.0",
        source_fingerprint="a" * 64,
        payload_schema="ProviderQuotaInputV2@2",
        queried_at=NOW,
    )


@pytest.mark.parametrize(
    ("certainty", "outcome", "failure", "expected"),
    (
        ("response_received", "succeeded", None, "verified_success"),
        ("response_received", "failed", "unauthorized", "credential_unauthorized"),
        ("response_received", "failed", "access_denied", "credential_unauthorized"),
        (
            "response_received",
            "failed",
            "invalid_provider_data",
            "provider_schema_incompatible",
        ),
        (
            "response_received",
            "failed",
            "unexpected_response",
            "outcome_unresolved",
        ),
        ("response_received", "rate_limited", "rate_limited", "rate_limited"),
        (
            "response_received",
            "failed",
            "provider_unavailable",
            "transient_failure",
        ),
        ("not_started", None, "deadline_exceeded", "transient_failure"),
        (
            "not_started",
            None,
            "authorization_unavailable",
            "authorization_unavailable",
        ),
    ),
)
def test_terminal_exact_source_state_maps_to_closed_signal(
    certainty: str,
    outcome: str | None,
    failure: str | None,
    expected: str,
) -> None:
    assert (
        classify_latest_ollama_cloud_source_signal_v1(
            run_state="partial" if outcome == "succeeded" else "failed",
            dispatch_certainty=certainty,
            outcome=outcome,
            failure_code=failure,
        )
        == expected
    )


@pytest.mark.parametrize(
    ("state", "certainty", "outcome", "failure"),
    (
        ("running", "may_have_started", None, None),
        ("failed", "response_received", "failed", "internal_adapter_error"),
        ("failed", "not_started", None, "source_not_admitted"),
        ("failed", "response_received", "failed", None),
    ),
)
def test_ambiguous_or_unclassified_state_fails_closed(
    state: str,
    certainty: str,
    outcome: str | None,
    failure: str | None,
) -> None:
    assert (
        classify_latest_ollama_cloud_source_signal_v1(
            run_state=state,
            dispatch_certainty=certainty,
            outcome=outcome,
            failure_code=failure,
        )
        == "outcome_unresolved"
    )


def test_projection_binds_exact_query_and_signal_lineage() -> None:
    request = query()
    signal = OllamaCloudLatestSourceSignalV1(
        account_id=request.account_id,
        binding_generation=request.binding_generation,
        access_target_id=request.access_target_id,
        capability_id=request.capability_id,
        source_id=request.source_id,
        adapter_version=request.adapter_version,
        source_fingerprint=request.source_fingerprint,
        payload_schema=request.payload_schema,
        signal="verified_success",
        run_id=OpaqueIdV1("run"),
        admission_id=OpaqueIdV1("admission"),
        run_state="partial",
        dispatch_certainty="response_received",
        run_requested_at=NOW - timedelta(seconds=2),
        signal_observed_at=NOW - timedelta(seconds=1),
        gate_state="ready",
        retry_at=None,
        queried_at=NOW,
    )

    assert signal.account_id == request.account_id
    assert signal.signal == "verified_success"
    assert signal.signal_observed_at == NOW - timedelta(seconds=1)


def test_transient_projection_requires_a_failed_run() -> None:
    request = query()
    signal = OllamaCloudLatestSourceSignalV1(
        account_id=request.account_id,
        binding_generation=request.binding_generation,
        access_target_id=request.access_target_id,
        capability_id=request.capability_id,
        source_id=request.source_id,
        adapter_version=request.adapter_version,
        source_fingerprint=request.source_fingerprint,
        payload_schema=request.payload_schema,
        signal="verified_success",
        run_id=OpaqueIdV1("run"),
        admission_id=OpaqueIdV1("admission"),
        run_state="partial",
        dispatch_certainty="response_received",
        run_requested_at=NOW - timedelta(seconds=2),
        signal_observed_at=NOW - timedelta(seconds=1),
        gate_state="ready",
        retry_at=None,
        queried_at=NOW,
    )

    with pytest.raises(
        InvalidCollectionControlV1, match="ollama_cloud_source_signal_invalid"
    ):
        replace(signal, signal="transient_failure")

"""Pure M03 admission for generation-bound scheduled cloud reads."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    InvalidProviderContract,
    ScheduledSourceAdmissionPolicyV1,
    ScheduledSourceLineageV1,
)
from agentmonitor.modules.provider_system.domain.protocol import (
    derive_scheduled_source_admission_v1,
    scheduled_source_policy_digest_v1,
)

NOW = datetime(2026, 11, 2, 20, 0, tzinfo=UTC)
SOURCE_FINGERPRINT = "a" * 64
PAYLOAD_DIGEST = "b" * 64


def policy() -> ScheduledSourceAdmissionPolicyV1:
    return ScheduledSourceAdmissionPolicyV1(
        policy_ref=OpaqueIdV1("ollama-cloud-scheduled-v1"),
        provider_key="ollama",
        authority_id="ollama.com",
        capability_id="subscription.quota",
        source_id="ollama.cloud.balance.v1",
        adapter_version="1.1.0",
        source_fingerprint=SOURCE_FINGERPRINT,
        payload_schema="ProviderQuotaInputV2@2",
        minimum_interval_seconds=60,
        maximum_concurrency=1,
        automatic_retry_count=0,
        provider_request_count=1,
        collection_policy_id="ollama-cloud-scheduled-v1",
        collection_policy_version="1.0.0",
        rate_policy_id="ollama-cloud-global-v1",
        rate_policy_version="1.0.0",
        fairness_policy_id="ollama-cloud-round-robin-v1",
        fairness_policy_version="1.0.0",
        invalidation_policy_id="ollama-cloud-binding-v1",
        invalidation_policy_version="1.0.0",
    )


def lineage() -> ScheduledSourceLineageV1:
    return ScheduledSourceLineageV1(
        verification_id=OpaqueIdV1("amvr_" + "1" * 32),
        account_id=OpaqueIdV1("account"),
        binding_id=OpaqueIdV1("amcb_" + "2" * 32),
        binding_generation=3,
        current_account_id=OpaqueIdV1("account"),
        current_binding_id=OpaqueIdV1("amcb_" + "2" * 32),
        current_binding_generation=3,
        access_target_id=OpaqueIdV1("amat_" + "3" * 32),
        current_access_target_id=OpaqueIdV1("amat_" + "3" * 32),
        target_kind="cloud_service",
        provider_key="ollama",
        authority_id="ollama.com",
        capability_id="subscription.quota",
        source_id="ollama.cloud.balance.v1",
        adapter_version="1.1.0",
        source_fingerprint=SOURCE_FINGERPRINT,
        payload_schema="ProviderQuotaInputV2@2",
        probe_run_id=OpaqueIdV1("probe-run"),
        probe_admission_id=OpaqueIdV1("probe-admission"),
        dispatch_certainty="response_received",
        run_state="succeeded",
        run_account_id=OpaqueIdV1("account"),
        run_target_generation=3,
        run_source_id="ollama.cloud.balance.v1",
        run_adapter_version="1.1.0",
        run_payload_digest=PAYLOAD_DIGEST,
        payload_digest=PAYLOAD_DIGEST,
        commit_state="committed",
        commit_run_id=OpaqueIdV1("probe-run"),
        commit_target_generation=3,
        commit_payload_schema="ProviderQuotaInputV2@2",
        commit_payload_digest=PAYLOAD_DIGEST,
        verified_at=NOW,
        commit_stored_at=NOW + timedelta(seconds=1),
        identity_provenance="owner_asserted",
        authorization_signal="verified_success",
        authorization_signal_run_id=OpaqueIdV1("probe-run"),
        authorization_signal_admission_id=OpaqueIdV1("probe-admission"),
        authorization_signal_account_id=OpaqueIdV1("account"),
        authorization_signal_binding_generation=3,
        authorization_signal_access_target_id=OpaqueIdV1("amat_" + "3" * 32),
        authorization_signal_source_id="ollama.cloud.balance.v1",
        authorization_signal_adapter_version="1.1.0",
        authorization_signal_source_fingerprint=SOURCE_FINGERPRINT,
        authorization_signal_payload_schema="ProviderQuotaInputV2@2",
        authorization_signal_run_state="partial",
        authorization_signal_dispatch_certainty="response_received",
        authorization_signal_run_requested_at=NOW - timedelta(seconds=1),
        authorization_signal_observed_at=NOW,
    )


def test_exact_probe_lineage_derives_ephemeral_scheduled_admission() -> None:
    current_policy = policy()
    proof = derive_scheduled_source_admission_v1(
        current_policy,
        lineage(),
        evaluated_at=NOW + timedelta(seconds=2),
    )

    assert proof.policy_digest == scheduled_source_policy_digest_v1(current_policy)
    assert proof.binding_generation == 3
    assert proof.probe_run_id == OpaqueIdV1("probe-run")
    assert proof.source_fingerprint == SOURCE_FINGERPRINT
    assert proof.identity_provenance == "owner_asserted"
    assert proof.authorization_signal_run_id == OpaqueIdV1("probe-run")


@pytest.mark.parametrize(
    "change",
    (
        {"current_binding_generation": 4},
        {"current_access_target_id": OpaqueIdV1("amat_" + "4" * 32)},
        {"source_fingerprint": "c" * 64},
        {"run_account_id": OpaqueIdV1("other-account")},
        {"run_target_generation": 4},
        {"run_source_id": "other.source.v1"},
        {"run_adapter_version": "2.0.0"},
        {"run_payload_digest": "d" * 64},
        {"commit_run_id": OpaqueIdV1("other-run")},
        {"commit_target_generation": 4},
        {"commit_payload_schema": "OtherPayloadV1@1"},
        {"commit_payload_digest": "d" * 64},
        {"authorization_signal_account_id": OpaqueIdV1("other-account")},
        {"authorization_signal_binding_generation": 4},
        {"authorization_signal_access_target_id": OpaqueIdV1("amat_" + "4" * 32)},
        {"authorization_signal_source_id": "other.source.v1"},
        {"authorization_signal_adapter_version": "2.0.0"},
        {"authorization_signal_source_fingerprint": "d" * 64},
        {"authorization_signal_payload_schema": "OtherPayloadV1@1"},
    ),
)
def test_mismatched_current_or_commit_lineage_is_not_admitted(
    change: dict[str, object],
) -> None:
    with pytest.raises(InvalidProviderContract, match="scheduled_source_not_admitted"):
        derive_scheduled_source_admission_v1(
            policy(),
            replace(lineage(), **change),
            evaluated_at=NOW + timedelta(seconds=2),
        )


def test_policy_binds_safe_scheduled_request_limits() -> None:
    with pytest.raises(
        InvalidProviderContract, match="scheduled_source_policy_invalid"
    ):
        replace(policy(), minimum_interval_seconds=59)


def test_policy_digest_changes_with_bound_invalidation_policy() -> None:
    current = policy()

    assert scheduled_source_policy_digest_v1(current) != (
        scheduled_source_policy_digest_v1(
            replace(current, invalidation_policy_version="1.0.1")
        )
    )


def test_proof_cannot_claim_provider_verified_identity() -> None:
    proof = derive_scheduled_source_admission_v1(
        policy(), lineage(), evaluated_at=NOW + timedelta(seconds=2)
    )
    assert proof.identity_provenance == "owner_asserted"
    assert not hasattr(proof, "provider_identity")


@pytest.mark.parametrize(
    "signal",
    (
        "credential_unauthorized",
        "provider_schema_incompatible",
        "outcome_unresolved",
    ),
)
def test_authoritative_auth_or_schema_failure_revokes_scheduled_admission(
    signal: str,
) -> None:
    with pytest.raises(InvalidProviderContract, match="scheduled_source_not_admitted"):
        derive_scheduled_source_admission_v1(
            policy(),
            replace(lineage(), authorization_signal=signal),  # type: ignore[arg-type]
            evaluated_at=NOW + timedelta(seconds=2),
        )


@pytest.mark.parametrize(
    "signal", ("rate_limited", "transient_failure", "authorization_unavailable")
)
def test_temporary_failure_preserves_generation_bound_admission(signal: str) -> None:
    certainty = (
        "not_started" if signal == "authorization_unavailable" else "response_received"
    )
    proof = derive_scheduled_source_admission_v1(
        policy(),
        replace(
            lineage(),
            authorization_signal=signal,  # type: ignore[arg-type]
            authorization_signal_run_state="failed",
            authorization_signal_dispatch_certainty=certainty,  # type: ignore[arg-type]
        ),
        evaluated_at=NOW + timedelta(seconds=2),
    )
    assert proof.authorization_signal == signal


def test_transient_signal_cannot_preserve_admission_from_a_successful_run() -> None:
    with pytest.raises(
        InvalidProviderContract, match="scheduled_source_lineage_invalid"
    ):
        replace(lineage(), authorization_signal="transient_failure")

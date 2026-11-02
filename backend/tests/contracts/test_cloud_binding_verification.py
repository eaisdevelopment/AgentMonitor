"""Pure M02/M04 cloud verification values; no I/O or provider data."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.contracts.collection_control_v1 import (
    CollectionRunAdmissionV2,
    InvalidCollectionControlV1,
    OllamaCloudVerificationAcquireV1,
    OllamaCloudVerificationTargetV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    ActiveCredentialBindingRefV1,
    AssertCredentialAccountOwnershipCommandV1,
    CredentialBindingVerificationReceiptV1,
    CredentialConnectionStatusV1,
    InitiateOllamaCloudVerificationCommandV1,
    ProviderAccessTargetV1,
    ProviderTargetRefV1,
)


def _binding() -> ActiveCredentialBindingRefV1:
    return ActiveCredentialBindingRefV1(
        account_id=OpaqueIdV1("account-1"),
        binding_id=OpaqueIdV1("amcb_" + "a" * 32),
        generation=3,
    )


def test_owner_assertion_is_exact_account_binding_installation_and_version() -> None:
    now = datetime(2026, 11, 2, 12, tzinfo=UTC)
    command = AssertCredentialAccountOwnershipCommandV1(
        command_id=OpaqueIdV1("command-1"),
        principal_id=OpaqueIdV1("principal-1"),
        account_id=OpaqueIdV1("account-1"),
        access_target_id=OpaqueIdV1("amat_" + "e" * 32),
        expected_account_record_version=2,
        binding=_binding(),
        requested_at=now,
    )

    assert command.binding.account_id == command.account_id
    with pytest.raises(ValueError, match="registry_credential_owner_assertion_invalid"):
        replace(command, account_id=OpaqueIdV1("account-2"))
    with pytest.raises(ValueError, match="registry_credential_owner_assertion_invalid"):
        replace(command, expected_account_record_version=0)

    initiation = InitiateOllamaCloudVerificationCommandV1(
        idempotency_key=OpaqueIdV1("request-1"),
        principal_id=command.principal_id,
        account_id=command.account_id,
        expected_account_record_version=command.expected_account_record_version,
        requested_at=now,
    )
    assert initiation.account_id == command.account_id

    status = CredentialConnectionStatusV1(
        account_id=command.account_id,
        state="pending",
        can_verify=True,
        binding_generation=command.binding.generation,
        observed_at=None,
        reason_code="verification_required",
    )
    assert status.can_verify
    with pytest.raises(
        ValueError, match="registry_credential_connection_status_invalid"
    ):
        replace(status, state="unavailable", can_verify=True)


def test_cloud_access_target_is_distinct_from_a_local_installation() -> None:
    target = ProviderAccessTargetV1(
        access_target_id=OpaqueIdV1("amat_" + "e" * 32),
        provider_key="ollama",
        target_kind="cloud_service",
        authority_id="ollama.cloud.official.v1",
        manifest_fingerprint="f" * 64,
        lifecycle="active",
        record_version=1,
    )

    assert target.target_kind == "cloud_service"
    with pytest.raises(ValueError, match="registry_provider_access_target_invalid"):
        replace(target, access_target_id=OpaqueIdV1("installation-1"))
    with pytest.raises(ValueError, match="unsupported-field-state"):
        replace(target, target_kind="local_installation")  # type: ignore[arg-type]


def test_provider_target_reference_requires_an_opaque_identifier() -> None:
    with pytest.raises(ValueError, match="registry_provider_target_invalid"):
        ProviderTargetRefV1(
            target_kind="provider_installation",
            target_id="installation-1",  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="registry_provider_target_invalid"):
        ProviderTargetRefV1(
            target_kind="cloud_service",
            target_id="amat_" + "e" * 32,  # type: ignore[arg-type]
        )


def test_generation_verification_receipt_is_closed_and_non_secret() -> None:
    now = datetime(2026, 11, 2, 12, tzinfo=UTC)
    receipt = CredentialBindingVerificationReceiptV1(
        verification_id=OpaqueIdV1("amvr_" + "b" * 32),
        binding=_binding(),
        access_target_id=OpaqueIdV1("amat_" + "e" * 32),
        run_id=OpaqueIdV1("run-1"),
        admission_id=OpaqueIdV1("admission-1"),
        source_id="ollama.cloud.balance.v1",
        adapter_version="1.0.0",
        manifest_fingerprint="c" * 64,
        payload_digest="d" * 64,
        verified_at=now,
        record_version=1,
    )

    assert receipt.binding.generation == 3
    assert receipt.access_target_id == OpaqueIdV1("amat_" + "e" * 32)
    with pytest.raises(ValueError, match="registry_credential_verification_invalid"):
        replace(receipt, verification_id=OpaqueIdV1("owner-supplied"))
    with pytest.raises(ValueError, match="unsupported-field-state"):
        replace(receipt, source_id="other.source")
    with pytest.raises(ValueError, match="registry_credential_verification_invalid"):
        replace(receipt, payload_digest="d" * 63)


def test_targeted_verification_acquire_is_exact_and_short_lived() -> None:
    now = datetime(2026, 11, 2, 12, tzinfo=UTC)
    request = OllamaCloudVerificationAcquireV1(
        admission_id=OpaqueIdV1("admission-1"),
        scheduler_instance_id=OpaqueIdV1("scheduler-1"),
        schedule_id=OpaqueIdV1("schedule-1"),
        account_id=OpaqueIdV1("account-1"),
        target_generation=4,
        requested_at=now,
        lease_expires_at=now + timedelta(seconds=30),
        jitter_seconds=2,
    )

    assert request.target_generation == 4
    with pytest.raises(
        InvalidCollectionControlV1, match="ollama_cloud_verification_acquire_invalid"
    ):
        replace(request, target_generation=0)
    with pytest.raises(
        InvalidCollectionControlV1, match="ollama_cloud_verification_acquire_invalid"
    ):
        replace(request, lease_expires_at=now + timedelta(seconds=61))

    target = OllamaCloudVerificationTargetV1(
        schedule_id=request.schedule_id,
        account_id=request.account_id,
        profile_id=OpaqueIdV1("profile-1"),
        resource_id=OpaqueIdV1("resource-1"),
        provider_target=ProviderTargetRefV1(
            target_kind="cloud_service",
            target_id=OpaqueIdV1("amat_" + "e" * 32),
        ),
        target_key_digest="a" * 64,
        target_generation=request.target_generation,
        requested_at=now,
    )
    assert target.provider_target.target_kind == "cloud_service"


def test_cloud_run_admission_requires_the_complete_cloud_graph() -> None:
    now = datetime(2026, 11, 2, 12, tzinfo=UTC)
    admission = CollectionRunAdmissionV2(
        run_id=OpaqueIdV1("run-1"),
        schedule_id=OpaqueIdV1("schedule-1"),
        request_id=OpaqueIdV1("request-1"),
        trigger="reauth_verification",
        operation_family="ollama_cloud_verification",
        requested_capability_ids=("subscription.quota",),
        capability_set_version="1.0.0",
        request_auth_method="dashboard_session",
        request_principal_id=OpaqueIdV1("principal-1"),
        correlation_id=OpaqueIdV1("correlation-1"),
        causation_id=None,
        target_key_digest="1" * 64,
        provider_key="ollama",
        provider_target=ProviderTargetRefV1(
            target_kind="cloud_service",
            target_id=OpaqueIdV1("amat_" + "2" * 32),
        ),
        account_id=OpaqueIdV1("account-1"),
        profile_id=OpaqueIdV1("profile-1"),
        resource_id=OpaqueIdV1("resource-1"),
        capability_id="subscription.quota",
        source_id="ollama.cloud.balance.v1",
        adapter_version="1.0.0",
        provider_version=None,
        adapter_protocol_version="1.0.0",
        manifest_fingerprint="3" * 64,
        collection_policy_version="1.0.0",
        registry_revision=1,
        retry_chain_id=OpaqueIdV1("retry-1"),
        attempt_ordinal=1,
        target_generation=1,
        scheduler_instance_id=OpaqueIdV1("scheduler-1"),
        lease_policy_version="1.0.0",
        budget_policy_id="ollama-cloud-global",
        budget_policy_version="1.0.0",
        budget_scope_digest="4" * 64,
        budget_dimension="request",
        budget_unit="count",
        budget_units=1,
        budget_limit_units=1,
        budget_window_start=now,
        budget_window_end=now + timedelta(minutes=1),
        payload_schema="ProviderQuotaInputV2@2",
        idempotency_key_digest=None,
        request_digest="5" * 64,
        requested_at=now,
        deadline_at=now + timedelta(seconds=30),
    )

    assert admission.provider_target.target_kind == "cloud_service"
    with pytest.raises(
        InvalidCollectionControlV1, match="collection_admission_invalid"
    ):
        replace(admission, resource_id=None)
    with pytest.raises(
        InvalidCollectionControlV1, match="collection_admission_invalid"
    ):
        replace(admission, provider_target="cloud_service")  # type: ignore[arg-type]

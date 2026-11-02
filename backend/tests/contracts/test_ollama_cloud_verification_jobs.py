"""Pure M04 contract checks for durable owner-verification work."""

from datetime import UTC, datetime, timedelta

import pytest

from agentmonitor.contracts.collection_control_v1 import (
    InvalidCollectionControlV1,
    OllamaCloudVerificationClaimRequestV1,
    OllamaCloudVerificationClaimTerminalV1,
    OllamaCloudVerificationEnqueueV2,
    OllamaCloudVerificationInterruptionProofV1,
    OllamaCloudVerificationJobClaimV1,
    OllamaCloudVerificationJobViewV1,
    OllamaCloudVerificationReplayQueryV1,
    OllamaCloudVerificationStatusV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1

NOW = datetime(2026, 11, 2, 18, 0, tzinfo=UTC)


def oid(value: str) -> OpaqueIdV1:
    return OpaqueIdV1(value)


def claim() -> OllamaCloudVerificationJobClaimV1:
    return OllamaCloudVerificationJobClaimV1(
        job_id=oid("amvj_" + "1" * 32),
        worker_instance_id=oid("worker-1"),
        request_principal_id=oid("principal-1"),
        idempotency_key_digest="a" * 64,
        schedule_id=oid("schedule-1"),
        account_id=oid("account-1"),
        access_target_id=oid("amat_" + "2" * 32),
        binding_generation=3,
        fencing_token=4,
        claimed_at=NOW,
        claim_expires_at=NOW + timedelta(seconds=45),
        record_version=2,
    )


def test_verification_enqueue_and_claim_are_exact_bounded_values() -> None:
    enqueue = OllamaCloudVerificationEnqueueV2(
        idempotency_key=oid("request-1"),
        principal_id=oid("principal-1"),
        schedule_id=oid("schedule-1"),
        account_id=oid("account-1"),
        access_target_id=oid("amat_" + "2" * 32),
        binding_generation=3,
        expected_account_record_version=4,
        requested_at=NOW,
    )
    replay = OllamaCloudVerificationReplayQueryV1(
        idempotency_key=enqueue.idempotency_key,
        principal_id=enqueue.principal_id,
        account_id=enqueue.account_id,
        expected_account_record_version=enqueue.expected_account_record_version,
    )
    request = OllamaCloudVerificationClaimRequestV1(
        worker_instance_id=oid("worker-1"),
        claimed_at=NOW,
        claim_expires_at=NOW + timedelta(seconds=45),
    )

    assert enqueue.binding_generation == 3
    assert replay.expected_account_record_version == 4
    assert request.claim_expires_at - request.claimed_at == timedelta(seconds=45)
    claimed = claim()
    assert claimed.fencing_token == 4
    assert claimed.request_principal_id == enqueue.principal_id
    assert claimed.idempotency_key_digest == "a" * 64


def test_verification_claim_cannot_outlive_the_bounded_worker_lease() -> None:
    with pytest.raises(
        InvalidCollectionControlV1,
        match="ollama_cloud_verification_claim_invalid",
    ):
        OllamaCloudVerificationClaimRequestV1(
            worker_instance_id=oid("worker-1"),
            claimed_at=NOW,
            claim_expires_at=NOW + timedelta(seconds=61),
        )


def test_only_an_exact_live_claim_can_record_a_pre_admission_terminal() -> None:
    current = claim()
    terminal = OllamaCloudVerificationClaimTerminalV1(
        job_id=current.job_id,
        worker_instance_id=current.worker_instance_id,
        fencing_token=current.fencing_token,
        claimed_at=current.claimed_at,
        claim_expires_at=current.claim_expires_at,
        terminal_at=NOW + timedelta(seconds=10),
        reason_code="worker_unavailable",
    )
    assert terminal.terminal_at < terminal.claim_expires_at

    with pytest.raises(
        InvalidCollectionControlV1,
        match="ollama_cloud_verification_terminal_invalid",
    ):
        OllamaCloudVerificationClaimTerminalV1(
            job_id=current.job_id,
            worker_instance_id=current.worker_instance_id,
            fencing_token=current.fencing_token,
            claimed_at=current.claimed_at,
            claim_expires_at=current.claim_expires_at,
            terminal_at=current.claim_expires_at + timedelta(microseconds=1),
            reason_code="worker_unavailable",
        )


def test_status_keeps_ambiguous_dispatch_non_retryable() -> None:
    job = OllamaCloudVerificationJobViewV1(
        job_id=oid("amvj_" + "1" * 32),
        account_id=oid("account-1"),
        access_target_id=oid("amat_" + "2" * 32),
        schedule_id=oid("schedule-1"),
        binding_generation=3,
        state="admitted",
        requested_at=NOW,
        not_before_at=NOW,
        admission_id=oid("admission-1"),
        run_id=oid("run-1"),
        dispatch_certainty="may_have_started",
        terminal_at=None,
        outcome=None,
        reason_code="request_outcome_unknown",
        retry_after_seconds=None,
        record_version=4,
    )
    status = OllamaCloudVerificationStatusV1(
        account_id=job.account_id,
        binding_generation=3,
        job=job,
        gate_state="unresolved",
        retry_at=None,
        queried_at=NOW + timedelta(minutes=1),
    )

    assert status.gate_state == "unresolved"
    assert status.retry_at is None


def test_busy_or_not_due_status_requires_an_exact_retry_time() -> None:
    with pytest.raises(
        InvalidCollectionControlV1,
        match="ollama_cloud_verification_status_invalid",
    ):
        OllamaCloudVerificationStatusV1(
            account_id=oid("account-1"),
            binding_generation=3,
            job=None,
            gate_state="busy",
            retry_at=None,
            queried_at=NOW,
        )


def test_ambiguous_dispatch_cannot_be_presented_as_terminal() -> None:
    with pytest.raises(
        InvalidCollectionControlV1,
        match="ollama_cloud_verification_job_invalid",
    ):
        OllamaCloudVerificationJobViewV1(
            job_id=oid("amvj_" + "1" * 32),
            account_id=oid("account-1"),
            access_target_id=oid("amat_" + "2" * 32),
            schedule_id=oid("schedule-1"),
            binding_generation=3,
            state="terminal",
            requested_at=NOW,
            not_before_at=NOW,
            admission_id=oid("admission-1"),
            run_id=oid("run-1"),
            dispatch_certainty="may_have_started",
            terminal_at=NOW + timedelta(seconds=10),
            outcome=None,
            reason_code="request_outcome_unknown",
            retry_after_seconds=None,
            record_version=4,
        )


def test_interruption_proof_is_closed_and_time_bound() -> None:
    proof = OllamaCloudVerificationInterruptionProofV1(
        job_id=oid("amvj_" + "1" * 32),
        run_id=oid("run-1"),
        admission_id=oid("admission-1"),
        commit_status="not_committed",
        verification_receipt_state="absent",
        checked_at=NOW,
    )
    assert proof.commit_status == "not_committed"

    with pytest.raises(ValueError, match="unsupported-field-state"):
        OllamaCloudVerificationInterruptionProofV1(
            job_id=proof.job_id,
            run_id=proof.run_id,
            admission_id=proof.admission_id,
            commit_status="committed",  # type: ignore[arg-type]
            verification_receipt_state="absent",
            checked_at=NOW,
        )

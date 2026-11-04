"""Pure terminal sequencing for Ollama cloud owner verification."""

from typing import Literal

from agentmonitor.contracts.collection_control_v1 import (
    CollectionRunStateV1,
    OllamaCloudAdmissionOutcomeV1,
    OllamaCloudSourceAuthorizationSignalV1,
)

OllamaVerificationCompletionDecisionV1 = Literal[
    "pending", "verification_succeeded", "verification_commit_interrupted"
]
VERIFICATION_RESPONSE_OUTCOME_V1: Literal["succeeded"] = "succeeded"

_NONTERMINAL_RUNS = frozenset({"requested", "queued", "running", "committing"})
_COMMITTED_RUNS = frozenset({"succeeded", "partial"})
_FAILED_RUNS = frozenset({"failed", "blocked", "cancelled", "unsupported"})
RECONCILABLE_VERIFICATION_RUN_STATES_V1: tuple[CollectionRunStateV1, ...] = (
    "succeeded",
    "partial",
    "failed",
    "blocked",
    "cancelled",
    "unsupported",
)


def decide_cloud_verification_replay(
    *,
    existing_account_id: str,
    existing_expected_account_record_version: int | None,
    request_account_id: str,
    request_expected_account_record_version: int,
) -> Literal["replay"]:
    """Permit replay only for the original external initiation request."""
    if (
        not existing_account_id
        or not request_account_id
        or type(request_expected_account_record_version) is not int
        or request_expected_account_record_version < 1
        or type(existing_expected_account_record_version) is not int
        or existing_expected_account_record_version < 1
        or existing_account_id != request_account_id
        or existing_expected_account_record_version
        != request_expected_account_record_version
    ):
        raise ValueError("ollama_cloud_verification_idempotency_conflict")
    return "replay"


def classify_latest_ollama_cloud_source_signal_v1(
    *,
    run_state: str,
    dispatch_certainty: str | None,
    outcome: str | None,
    failure_code: str | None,
) -> OllamaCloudSourceAuthorizationSignalV1:
    """Classify only M04's closed sanitized journal facts, never reason text."""
    if (
        run_state
        not in {
            "requested",
            "queued",
            "running",
            "committing",
            "succeeded",
            "partial",
            "failed",
            "blocked",
            "cancelled",
            "unsupported",
        }
        or dispatch_certainty
        not in {None, "not_started", "may_have_started", "response_received"}
        or outcome not in {None, "succeeded", "rate_limited", "failed"}
        or failure_code
        not in {
            None,
            "authorization_unavailable",
            "credential_update_in_progress",
            "unauthorized",
            "access_denied",
            "rate_limited",
            "provider_unavailable",
            "unexpected_response",
            "invalid_provider_data",
            "deadline_exceeded",
            "internal_adapter_error",
            "source_not_admitted",
            "pre_dispatch_failed",
        }
    ):
        raise ValueError("ollama_cloud_source_signal_invalid")
    if run_state in _NONTERMINAL_RUNS:
        return "outcome_unresolved"
    if dispatch_certainty == "response_received":
        if (
            run_state in _COMMITTED_RUNS
            and outcome == "succeeded"
            and failure_code is None
        ):
            return "verified_success"
        if run_state != "failed":
            return "outcome_unresolved"
        if outcome == "rate_limited" and failure_code == "rate_limited":
            return "rate_limited"
        if outcome != "failed":
            return "outcome_unresolved"
        if failure_code in {"unauthorized", "access_denied"}:
            return "credential_unauthorized"
        if failure_code == "invalid_provider_data":
            return "provider_schema_incompatible"
        if failure_code in {"provider_unavailable", "deadline_exceeded"}:
            return "transient_failure"
        return "outcome_unresolved"
    if dispatch_certainty == "not_started" and run_state == "failed":
        if (
            failure_code in {"pre_dispatch_failed", "internal_adapter_error"}
            and outcome is None
        ):
            return "transient_failure"
        if failure_code == "credential_update_in_progress":
            return "credential_update_in_progress"
        if failure_code == "authorization_unavailable":
            return "authorization_unavailable"
        if failure_code in {"provider_unavailable", "deadline_exceeded"}:
            return "transient_failure"
    return "outcome_unresolved"


def verification_lineage_matches(
    *,
    expected_run_id: str,
    job_run_id: str,
    journal_run_id: str,
    job_account_id: str,
    admission_account_id: str,
    run_account_id: str,
    job_schedule_id: str,
    admission_schedule_id: str,
    run_schedule_id: str,
) -> bool:
    """Match the exact cross-table lineage used by a verification finalizer."""
    values = (
        expected_run_id,
        job_run_id,
        journal_run_id,
        job_account_id,
        admission_account_id,
        run_account_id,
        job_schedule_id,
        admission_schedule_id,
        run_schedule_id,
    )
    return all(type(value) is str and bool(value) for value in values) and (
        expected_run_id == job_run_id == journal_run_id
        and job_account_id == admission_account_id == run_account_id
        and job_schedule_id == admission_schedule_id == run_schedule_id
    )


def verification_completion_decision(
    rate_outcome: OllamaCloudAdmissionOutcomeV1,
    run_state: CollectionRunStateV1,
    receipt_present: bool,
) -> OllamaVerificationCompletionDecisionV1:
    """Require the committed receipt and terminal M04 run before verification."""
    if rate_outcome != "succeeded" or type(receipt_present) is not bool:
        raise ValueError("ollama_cloud_verification_proof_invalid")
    if run_state in _NONTERMINAL_RUNS:
        if receipt_present:
            raise ValueError("ollama_cloud_verification_proof_invalid")
        return "pending"
    if run_state in _COMMITTED_RUNS:
        if not receipt_present:
            raise ValueError("ollama_cloud_verification_proof_invalid")
        return "verification_succeeded"
    if run_state in _FAILED_RUNS:
        if receipt_present:
            raise ValueError("ollama_cloud_verification_proof_invalid")
        return "verification_commit_interrupted"
    raise ValueError("ollama_cloud_verification_proof_invalid")

"""Pure terminal sequencing for Ollama cloud owner verification."""

from typing import Literal

from agentmonitor.contracts.collection_control_v1 import (
    CollectionRunStateV1,
    OllamaCloudAdmissionOutcomeV1,
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

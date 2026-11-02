"""Pure sequencing policy for owner-requested Ollama verification."""

from typing import Literal

import pytest
from agentmonitor.modules.collection_control.domain.ollama_verification import (
    RECONCILABLE_VERIFICATION_RUN_STATES_V1,
    VERIFICATION_RESPONSE_OUTCOME_V1,
    decide_cloud_verification_replay,
    verification_completion_decision,
    verification_lineage_matches,
)


def test_exact_verification_request_replays_after_account_version_moves() -> None:
    assert (
        decide_cloud_verification_replay(
            existing_account_id="account-1",
            existing_expected_account_record_version=4,
            request_account_id="account-1",
            request_expected_account_record_version=4,
        )
        == "replay"
    )


@pytest.mark.parametrize(
    "existing_account_id,existing_version,request_account_id,request_version",
    (
        ("account-1", 4, "account-1", 5),
        ("account-1", 4, "account-2", 4),
        ("account-1", None, "account-1", 4),
    ),
)
def test_changed_or_legacy_verification_request_cannot_replay(
    existing_account_id: str,
    existing_version: int | None,
    request_account_id: str,
    request_version: int,
) -> None:
    with pytest.raises(
        ValueError, match="ollama_cloud_verification_idempotency_conflict"
    ):
        decide_cloud_verification_replay(
            existing_account_id=existing_account_id,
            existing_expected_account_record_version=existing_version,
            request_account_id=request_account_id,
            request_expected_account_record_version=request_version,
        )


def test_successful_response_waits_for_terminal_run_and_receipt() -> None:
    assert verification_completion_decision("succeeded", "running", False) == "pending"
    assert (
        verification_completion_decision("succeeded", "partial", True)
        == "verification_succeeded"
    )


def test_interrupted_commit_never_becomes_verified() -> None:
    assert (
        verification_completion_decision("succeeded", "failed", False)
        == "verification_commit_interrupted"
    )
    assert VERIFICATION_RESPONSE_OUTCOME_V1 == "succeeded"


def test_recovery_query_only_selects_terminal_reconcilable_runs() -> None:
    assert RECONCILABLE_VERIFICATION_RUN_STATES_V1 == (
        "succeeded",
        "partial",
        "failed",
        "blocked",
        "cancelled",
        "unsupported",
    )


def test_finalization_requires_exact_cross_table_lineage() -> None:
    assert verification_lineage_matches(
        expected_run_id="run",
        job_run_id="run",
        journal_run_id="run",
        job_account_id="account",
        admission_account_id="account",
        run_account_id="account",
        job_schedule_id="schedule",
        admission_schedule_id="schedule",
        run_schedule_id="schedule",
    )
    assert not verification_lineage_matches(
        expected_run_id="run",
        job_run_id="run",
        journal_run_id="other-run",
        job_account_id="account",
        admission_account_id="account",
        run_account_id="account",
        job_schedule_id="schedule",
        admission_schedule_id="schedule",
        run_schedule_id="schedule",
    )


@pytest.mark.parametrize(
    ("run_state", "receipt_present"),
    (("partial", False), ("failed", True), ("running", True)),
)
def test_receipt_and_run_mismatch_fails_closed(
    run_state: Literal["partial", "failed", "running"], receipt_present: bool
) -> None:
    with pytest.raises(ValueError, match="ollama_cloud_verification_proof_invalid"):
        verification_completion_decision("succeeded", run_state, receipt_present)

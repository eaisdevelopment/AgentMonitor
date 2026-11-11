"""Pure safe diagnostics never reveal an exception payload or filesystem path."""

import pytest

from tools.automation.implementations.m6_cutover import CutoverError
from tools.automation.implementations.m6_cutover_diagnostics import (
    cutover_failure_message,
    cutover_failure_reason,
    parse_cutover_failure_message,
)


def test_closed_diagnostic_keeps_phase_and_known_reason() -> None:
    error = CutoverError(
        "cutover_incomplete_review_journal",
        phase="write_barrier",
        reason="persistence_busy",
    )
    message = cutover_failure_message(error)
    assert parse_cutover_failure_message(message.encode()) == (
        "write_barrier",
        "persistence_busy",
    )
    assert str(error) == "cutover_incomplete_review_journal"


@pytest.mark.parametrize(
    "payload", ["unrecognized detail", "/private/location", "header-value"]
)
def test_arbitrary_failure_text_is_not_exposed(payload: str) -> None:
    error = RuntimeError(payload)
    assert cutover_failure_reason(error) == "unexpected_failure"
    assert payload not in cutover_failure_message(error)
    assert parse_cutover_failure_message(payload.encode()) is None


def test_diagnostic_rejects_extra_output_and_unapproved_fields() -> None:
    message = cutover_failure_message(CutoverError("target_unit_changed"))
    assert parse_cutover_failure_message(message.encode()) == (
        "preflight",
        "target_unit_changed",
    )
    assert parse_cutover_failure_message((message + "\nextra").encode()) is None
    assert (
        parse_cutover_failure_message(
            message.replace("preflight", "unreviewed").encode()
        )
        is None
    )
    assert (
        parse_cutover_failure_message(
            message.replace("target_unit_changed", "unreviewed").encode()
        )
        is None
    )


def test_m7_retains_closed_phase_reason() -> None:
    from tools.automation.implementations.auto_m7 import closed_setup_command_reason

    error = CutoverError(
        "cutover_incomplete_review_journal",
        phase="write_barrier",
        reason="persistence_busy",
    )
    assert (
        closed_setup_command_reason(cutover_failure_message(error).encode())
        == "m7_cutover_write_barrier_persistence_busy"
    )


@pytest.mark.parametrize(
    "reason",
    [
        "unit_not_quiescent_ready",
        "unit_identity_changed",
        "unit_identity_unavailable",
        "unit_has_children_or_not_stopped",
        "unit_changed",
        "unit_invocation_changed",
        "unit_stop_unconfirmed",
        "unit_signal_unavailable",
        "unit_unavailable",
        "unit_uid_mismatch",
        "unit_cgroup_mismatch",
    ],
)
def test_quiescent_stop_retains_closed_reason_without_process_details(
    reason: str,
) -> None:
    from tools.automation.implementations.m6_quiescent_stop import QuiescentStopError

    error = QuiescentStopError(reason)
    safe_reason = cutover_failure_reason(error)
    assert safe_reason == reason
    transition = CutoverError(
        "cutover_incomplete_review_journal", phase="stop", reason=safe_reason
    )
    assert parse_cutover_failure_message(
        cutover_failure_message(transition).encode()
    ) == ("stop", reason)

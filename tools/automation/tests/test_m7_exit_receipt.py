"""Pure receipt policy; constructed outcomes never cross an I/O boundary."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from tools.automation.implementations.auto_m7 import REQUIRED_CHECKS
from tools.automation.implementations.m7_exit_receipt import (
    ExitContext,
    TimedCheck,
    build_receipt,
)

START = datetime(2026, 11, 12, tzinfo=UTC)
CONTEXT = ExitContext("a" * 40, "a" * 40, "v1_0736", "b" * 64)


def observations() -> tuple[TimedCheck, ...]:
    return tuple(
        TimedCheck(lane, name, "passed", None, START, START + timedelta(seconds=1))
        for lane in (*REQUIRED_CHECKS["exit"], "exit")
        for name in REQUIRED_CHECKS[lane]
    )


def receipt(checks: tuple[TimedCheck, ...]) -> dict[str, object]:
    return build_receipt(CONTEXT, CONTEXT, checks, REQUIRED_CHECKS)


def test_complete_receipt_binds_all_required_checks_without_owner_acceptance() -> None:
    value = receipt(observations())
    assert value["status"] == "passed"
    assert value["source_revision"] == CONTEXT.source_revision
    assert value["installed_revision"] == CONTEXT.installed_revision
    assert value["schema_revision"] == CONTEXT.schema_revision
    assert value["owner_acceptance"] == "not_recorded"
    assert value["publication"] == "not_verified"
    checks = value["checks"]
    assert isinstance(checks, list) and len(checks) == 26


@pytest.mark.parametrize("status", ["not_run", "blocked", "failed"])
def test_nonpass_required_check_cannot_be_hidden_by_passed_parent(status: str) -> None:
    checks = observations()
    value = receipt((replace(checks[0], status=status), *checks[1:]))
    assert value["status"] != "passed"


def test_missing_duplicate_or_foreign_required_checks_are_rejected() -> None:
    checks = observations()
    for invalid in (
        checks[1:],
        (*checks, checks[0]),
        (replace(checks[0], name="other"), *checks[1:]),
    ):
        with pytest.raises(ValueError, match="m7_receipt_checks_invalid"):
            receipt(invalid)


@pytest.mark.parametrize(
    "field",
    ["source_revision", "installed_revision", "schema_revision", "service_identity"],
)
def test_context_change_is_rejected(field: str) -> None:
    changed = replace(CONTEXT, **{field: "changed"})
    with pytest.raises(ValueError, match="m7_receipt_context_invalid"):
        build_receipt(CONTEXT, changed, observations(), REQUIRED_CHECKS)


@pytest.mark.parametrize("invalid", ["credential=secret", "unexpected", "", "PASSED"])
def test_unrecognized_status_cannot_enter_receipt(invalid: str) -> None:
    checks = observations()
    with pytest.raises(ValueError, match="m7_receipt_check_invalid"):
        receipt((replace(checks[0], status=invalid), *checks[1:]))


def test_invalid_time_or_unbounded_diagnostic_cannot_enter_receipt() -> None:
    checks = observations()
    for first in (
        replace(checks[0], finished_at=START - timedelta(seconds=1)),
        replace(checks[0], started_at=START.replace(tzinfo=None)),
        replace(checks[0], reason_code="https://private.example?key=secret"),
    ):
        with pytest.raises(ValueError, match="m7_receipt_check_invalid"):
            receipt((first, *checks[1:]))

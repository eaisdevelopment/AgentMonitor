"""Pure closed-result admission; no subprocess or credential boundary is simulated."""

import pytest

from tools.automation.implementations import auto_m7
from tools.automation.implementations.auto_m7 import (
    CREDENTIAL_LIFECYCLE_CHECKS as CHECKS,
)


def _proof() -> dict[str, object]:
    return {
        "record_type": "agentmonitor.m7_credential_lifecycle.v1",
        "evidence_scope": "one_real_billing_rotation_and_local_removal",
        "source_revision": "a" * 40,
        "status": "passed",
        "reason_code": None,
        "provider": "claude",
        "proof_digest": "b" * 64,
        "checks": dict.fromkeys(
            (
                "retired_binding_used",
                "replacement_binding_used",
                "same_scope",
                "history_retained",
                "retired_entry_absent",
                "replacement_entry_present",
                "service_unchanged",
                "account_unchanged",
                "env_selection_unchanged",
            ),
            True,
        ),
        "provider_key_revocation_claimed": False,
        "distinct_key_content_claimed": False,
        "command_provenance_claimed": False,
    }


def test_complete_genuine_lifecycle_can_replace_constant_not_run() -> None:
    assert auto_m7.credential_lifecycle_result(0, _proof(), "a" * 40).status == "passed"


@pytest.mark.parametrize("field", CHECKS)
def test_missing_physical_or_lineage_evidence_cannot_pass(field: str) -> None:
    payload = _proof()
    checks = payload["checks"]
    assert isinstance(checks, dict)
    payload["checks"] = checks | {field: False}
    assert auto_m7.credential_lifecycle_result(0, payload, "a" * 40).status == "failed"


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_revision", "c" * 40),
        ("provider", "ollama"),
        ("proof_digest", "not-a-digest"),
        ("provider_key_revocation_claimed", True),
        ("distinct_key_content_claimed", True),
        ("status", "not_run"),
    ],
)
def test_scope_revision_and_claims_are_not_interchangeable(
    field: str, value: object
) -> None:
    assert (
        auto_m7.credential_lifecycle_result(
            0, _proof() | {field: value}, "a" * 40
        ).status
        == "failed"
    )


def test_missing_real_rotation_remains_specific_not_run() -> None:
    payload = _proof() | {
        "status": "not_run",
        "reason_code": "m7_billing_rotation_history_absent",
        "provider": None,
        "proof_digest": None,
        "checks": {},
    }
    result = auto_m7.credential_lifecycle_result(3, payload, "a" * 40)
    assert result.status == "not_run"
    assert result.reason_code == "m7_billing_rotation_history_absent"


def test_unknown_runtime_text_cannot_escape_closed_result() -> None:
    payload = _proof() | {"status": "not_run", "reason_code": "arbitrary private text"}
    assert (
        auto_m7.credential_lifecycle_result(3, payload, "a" * 40).reason_code
        == "m7_credential_lifecycle_proof_invalid"
    )

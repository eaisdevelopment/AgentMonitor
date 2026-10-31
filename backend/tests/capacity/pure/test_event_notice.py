"""M4-CAP-E01: closed owned notice values, no I/O or provider telemetry."""

import hashlib
from typing import Any

import pytest
from agentmonitor.contracts import capacity_v1 as contracts
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.capacity.application import queries


def _notice(**changes: Any) -> Any:
    notice_type = getattr(contracts, "CapacityCommittedNoticeV1", None)
    assert notice_type is not None, (
        "existing commit notice has no closed payload contract"
    )
    values = {
        "capability_id": "domain-capability",
        "projection_count": 2,
        "state": "succeeded",
    }
    values.update(changes)
    return notice_type(**values)


def test_commit_notice_digest_is_exact_canonical_three_field_payload() -> None:
    digest = getattr(queries, "capacity_event_payload_digest_v1", None)
    assert callable(digest), "owned commit notice canonical digest is absent"
    expected = hashlib.sha256(
        b'{"capability_id":"domain-capability","projection_count":2,"state":"succeeded"}'
    ).hexdigest()
    assert digest(_notice()) == expected


@pytest.mark.parametrize("value", [0, 33, True])
def test_notice_cannot_claim_outside_committed_window_bound(value: int | bool) -> None:
    with pytest.raises(ValueError, match="capacity_commit_notice_invalid"):
        _notice(projection_count=value)


def test_notice_cannot_reinterpret_commit_as_capacity_health() -> None:
    with pytest.raises(ValueError, match="capacity_commit_notice_invalid"):
        _notice(state="exhausted")


def _ack(**changes: Any) -> Any:
    decide = getattr(queries, "capacity_event_acknowledgement_v1", None)
    assert callable(decide), "exact idempotent acknowledgement proof policy is absent"
    values = {
        "actual_digest": "a" * 64,
        "provided_digest": "a" * 64,
        "receipt_id": OpaqueIdV1("domain_receipt"),
        "previous_receipt_id": None,
        "previous_digest": None,
        "previously_acknowledged": False,
    }
    values.update(changes)
    return decide(**values)


def test_new_exact_receipt_is_applied_and_identical_ack_is_duplicate() -> None:
    assert _ack() == "apply"
    assert (
        _ack(
            previous_receipt_id=OpaqueIdV1("domain_receipt"),
            previous_digest="a" * 64,
            previously_acknowledged=True,
        )
        == "duplicate"
    )


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"provided_digest": "b" * 64}, "capacity_event_digest_mismatch"),
        (
            {"previously_acknowledged": True},
            "capacity_event_acknowledgement_proof_unknown",
        ),
        (
            {
                "previous_receipt_id": OpaqueIdV1("different_receipt"),
                "previous_digest": "a" * 64,
            },
            "capacity_event_acknowledgement_conflict",
        ),
        (
            {
                "previous_receipt_id": OpaqueIdV1("domain_receipt"),
                "previous_digest": "b" * 64,
            },
            "capacity_event_acknowledgement_conflict",
        ),
    ],
)
def test_wrong_or_unknown_receipt_proof_cannot_modify_first_ack(
    changes: dict[str, Any], code: str
) -> None:
    with pytest.raises(ValueError, match=code):
        _ack(**changes)

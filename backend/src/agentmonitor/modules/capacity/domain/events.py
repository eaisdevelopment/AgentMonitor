"""Pure canonical meaning of owned commit notices and acknowledgement proof."""

import hashlib
import json
from typing import Literal

from agentmonitor.contracts.capacity_v1 import (
    CapacityCommittedNoticeV1,
    InvalidCapacityContractV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def capacity_event_payload_digest_v1(notice: CapacityCommittedNoticeV1) -> str:
    payload = json.dumps(
        {
            "capability_id": notice.capability_id,
            "projection_count": notice.projection_count,
            "state": notice.state,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def capacity_event_acknowledgement_v1(
    *,
    actual_digest: str,
    provided_digest: str,
    receipt_id: OpaqueIdV1,
    previous_receipt_id: OpaqueIdV1 | None,
    previous_digest: str | None,
    previously_acknowledged: bool,
) -> Literal["apply", "duplicate"]:
    if actual_digest != provided_digest:
        raise InvalidCapacityContractV1("capacity_event_digest_mismatch")
    if previously_acknowledged and previous_receipt_id is None:
        raise InvalidCapacityContractV1("capacity_event_acknowledgement_proof_unknown")
    if previous_receipt_id is not None or previous_digest is not None:
        if previous_receipt_id != receipt_id or previous_digest != provided_digest:
            raise InvalidCapacityContractV1("capacity_event_acknowledgement_conflict")
        if previously_acknowledged:
            return "duplicate"
    return "apply"

"""Published M05 projection-policy entry point used by its persistence adapter."""

import json
from typing import Literal

from agentmonitor.contracts.capacity_v1 import (
    CapacityCommittedNoticeV1,
    CapacityHealthPolicyV1,
    CapacityHealthViewV1,
    QuotaWindowViewV1OrV2,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.capacity.domain.current_projection import (
    current_window_candidate_wins_v1 as current_window_candidate_wins_v1,
)
from agentmonitor.modules.capacity.domain.current_projection import (
    current_window_lifecycle_semantic_v1 as current_window_lifecycle_semantic_v1,
)
from agentmonitor.modules.capacity.domain.current_projection import (
    omitted_current_window_keys_v1 as omitted_current_window_keys_v1,
)
from agentmonitor.modules.capacity.domain.events import (
    capacity_event_acknowledgement_v1,
    capacity_event_payload_digest_v1,
)
from agentmonitor.modules.capacity.domain.health import (
    classify_capacity_windows_v1,
    default_capacity_health_policy_v1,
)


class ClassifyCapacityProjectionV1:
    """Pure policy facade; no persistence, provider or clock dependency."""

    @property
    def policy(self) -> CapacityHealthPolicyV1:
        return default_capacity_health_policy_v1()

    def __call__(
        self, windows: tuple[QuotaWindowViewV1OrV2, ...]
    ) -> CapacityHealthViewV1:
        return classify_capacity_windows_v1(
            windows,
            policy=self.policy,
        )


class CapacityCommittedPayloadPolicyV1:
    """Decode the owned persisted V1 notice without raw dictionaries escaping."""

    def decode(self, payload_json: str) -> CapacityCommittedNoticeV1:
        if len(payload_json) > 4096:
            raise ValueError("capacity_event_payload_invalid")
        try:
            value = json.loads(payload_json)
            if not isinstance(value, dict) or set(value) != {
                "capability_id",
                "projection_count",
                "state",
            }:
                raise ValueError("capacity_event_payload_invalid")
            return CapacityCommittedNoticeV1(
                value["capability_id"], value["projection_count"], value["state"]
            )
        except (ValueError, TypeError, KeyError):
            raise ValueError("capacity_event_payload_invalid") from None

    def digest(self, notice: CapacityCommittedNoticeV1) -> str:
        return capacity_event_payload_digest_v1(notice)

    def acknowledge(
        self,
        *,
        actual_digest: str,
        provided_digest: str,
        receipt_id: OpaqueIdV1,
        previous_receipt_id: OpaqueIdV1 | None,
        previous_digest: str | None,
        previously_acknowledged: bool,
    ) -> Literal["apply", "duplicate"]:
        return capacity_event_acknowledgement_v1(
            actual_digest=actual_digest,
            provided_digest=provided_digest,
            receipt_id=receipt_id,
            previous_receipt_id=previous_receipt_id,
            previous_digest=previous_digest,
            previously_acknowledged=previously_acknowledged,
        )

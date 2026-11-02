"""Read-only M04 scheduled-lane facts for operational presentation."""

from dataclasses import dataclass
from typing import ClassVar

from agentmonitor.contracts.common_v1 import TechnicalValueV1


@dataclass(frozen=True, slots=True)
class CloudScheduleStatusV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-COL-011"
    OWNER: ClassVar[str] = "PLAN-M04"
    schedule_id: str
    target_key_digest: str
    account_id: str
    profile_id: str
    resource_id: str
    access_target_id: str
    target_generation: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            any(
                not isinstance(value, str) or not value.strip() or len(value) > 256
                for value in (
                    self.schedule_id,
                    self.account_id,
                    self.profile_id,
                    self.resource_id,
                    self.access_target_id,
                )
            )
            or len(self.target_key_digest) != 64
            or any(value not in "0123456789abcdef" for value in self.target_key_digest)
            or type(self.target_generation) is not int
            or self.target_generation < 1
        ):
            raise ValueError("cloud_schedule_status_invalid")

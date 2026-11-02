"""Read-only M04 scheduled-lane facts for operational presentation."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CloudScheduleStatusV1:
    schedule_id: str
    target_key_digest: str
    account_id: str
    profile_id: str
    resource_id: str
    access_target_id: str
    target_generation: int

"""Closed cloud usage intents; no secrets or owner preference changes."""

from datetime import datetime
from typing import Literal

from agentmonitor.api.v1.schemas.billing_actions import BillingCheckRunV1
from pydantic import BaseModel, ConfigDict, Field


class CloudUsageContextV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    scope: Literal["self", "team"]
    range_key: Literal["7d", "30d"]
    interval_start: datetime
    interval_end: datetime


class CloudUsageCollectInputV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    expected_target_version: int = Field(strict=True, ge=1)
    report_context: CloudUsageContextV1


class CloudUsageEligibilityWireV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    account_id: str
    resource_id: str
    account_record_version: int
    target_record_version: int
    binding_generation: int | None
    report_context: CloudUsageContextV1
    can_collect: bool
    reason_code: str
    next_allowed_at: datetime | None
    checked_at: datetime


class CloudUsageRunStatusV1(BillingCheckRunV1):
    account_id: str
    resource_id: str
    report_id: str | None
    report_context: CloudUsageContextV1

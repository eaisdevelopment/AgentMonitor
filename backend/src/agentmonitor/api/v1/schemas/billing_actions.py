"""Closed billing-check wire models; no credential or connection claims."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BillingCheckInputV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    expected_connection_version: int = Field(strict=True, ge=1)


class BillingCheckRunV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    state: Literal[
        "requested",
        "queued",
        "running",
        "committing",
        "succeeded",
        "partial",
        "failed",
        "blocked",
        "cancelled",
        "unsupported",
    ]
    outcome_code: str | None
    error_code: str | None
    requested_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    deadline_at: datetime


class BudgetRunStatusV1(BillingCheckRunV1):
    """Durable billing run and optional committed report; no credential state."""

    account_id: str
    resource_id: str
    report_id: str | None

"""Closed billing-check wire models; no credential or connection claims."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BillingCheckInputV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    expected_connection_version: int = Field(strict=True, ge=1)


class BillingReportContextV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    range_key: Literal["7d", "30d"]
    interval_start: datetime
    interval_end: datetime
    source_category: Literal["cost"]
    grouping: tuple[str, ...] = Field(default=(), max_length=0)


class BillingCollectInputV1(BillingCheckInputV1):
    report_context: BillingReportContextV1


class BillingReportContextV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    range_key: Literal["7d", "30d"]
    interval_start: datetime
    interval_end: datetime
    source_category: str = Field(
        min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$"
    )
    grouping: tuple[
        Literal["workspace", "project", "api_key_id", "model", "token_category"], ...
    ] = Field(default=(), max_length=1)


class BillingCollectInputV2(BillingCheckInputV1):
    report_context: BillingReportContextV2


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
    report_context: BillingReportContextV1 | None = None


class BudgetRunStatusV2(BillingCheckRunV1):
    """Durable billing run and optional committed report; no credential state."""

    account_id: str
    resource_id: str
    report_id: str | None
    report_context: BillingReportContextV2 | None = None


class SetBillingMonitoringInputV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    expected_connection_version: int = Field(strict=True, ge=1)
    expected_scope_generation: int = Field(strict=True, ge=1)
    expected_binding_generation: int | None = Field(strict=True, ge=1)
    monitoring_preference: Literal["enabled", "disabled"]
    verified_run_id: str | None = Field(
        min_length=1, max_length=256, pattern=r"^[A-Za-z0-9._:-]+$"
    )


class BillingMonitoringStatusV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    account_id: str
    resource_id: str
    account_record_version: int
    connection_record_version: int
    scope_generation: int
    binding_generation: int | None
    monitoring_preference: Literal["enabled", "disabled"]
    lifecycle: Literal["pending", "active", "disconnected"]
    can_enable: bool
    can_disable: bool
    reason_code: str
    verified_run_id: str | None
    verified_at: datetime | None


class BillingMonitoringResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    account_id: str
    resource_id: str
    connection_record_version: int
    scope_generation: int
    monitoring_preference: Literal["enabled", "disabled"]
    lifecycle: Literal["pending", "active", "disconnected"]
    registry_revision: int
    updated_at: datetime


class BillingReportOptionWireV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_id: str
    source_category: str
    grouping: tuple[str, ...] = Field(max_length=1)
    label: str


class BillingCollectionEligibilityWireV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    account_id: str
    resource_id: str
    account_record_version: int
    connection_record_version: int
    scope_generation: int
    binding_generation: int | None
    report_context: BillingReportContextV1
    can_collect: bool
    reason_code: str
    next_allowed_at: datetime | None
    checked_at: datetime
    collection_options: tuple[BillingReportOptionWireV1, ...] = Field(
        default=(), max_length=64
    )


class BillingCollectionEligibilityWireV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    account_id: str
    resource_id: str
    account_record_version: int
    connection_record_version: int
    scope_generation: int
    binding_generation: int | None
    report_context: BillingReportContextV2
    can_collect: bool
    reason_code: str
    next_allowed_at: datetime | None
    checked_at: datetime
    collection_options: tuple[BillingReportOptionWireV1, ...] = Field(
        default=(), max_length=64
    )

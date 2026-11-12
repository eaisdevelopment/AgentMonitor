"""Compact analysis of one pinned financial report; no bucket bodies."""

from datetime import datetime

from agentmonitor.api.v1.schemas.budgets import (
    BudgetPeriodWireV1,
    BudgetReportSummaryWireV1,
    ExactMoneyWireV1,
)
from pydantic import BaseModel, ConfigDict, Field


class BudgetObservedRateWireV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    cost: ExactMoneyWireV1
    covered_seconds: int = Field(gt=0)
    period: BudgetPeriodWireV1
    input_report_ids: list[str] = Field(max_length=1)
    input_bucket_keys: list[str] = Field(max_length=200)
    day_count: int = Field(ge=3, le=7)
    display_text: str | None
    display_rounding: str | None
    display_decimal_places: int | None


class BudgetForecastWireV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    report: BudgetReportSummaryWireV1
    as_of: datetime
    rate: BudgetObservedRateWireV1 | None
    rate_reason: str
    exhaustion_reason: str
    exhaustion_at: datetime | None
    funds_observed_at: datetime | None
    input_observation_ids: list[str]
    time_left_numerator: str | None
    time_left_denominator: str | None
    method_id: str
    method_version: str
    time_rounding: str
    source_policy_id: str | None
    source_policy_version: str | None

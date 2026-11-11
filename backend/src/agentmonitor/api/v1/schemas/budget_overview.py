"""Compact financial Overview; no report bodies or credential identifiers."""

from datetime import datetime
from typing import Literal

from agentmonitor.api.v1.schemas.budgets import (
    BudgetPeriodWireV1,
    BudgetReportedSpendWireV1,
    BudgetReportWireV1,
    ExactMoneyFieldWireV1,
    ExactMoneyWireV1,
)
from agentmonitor.api.v1.schemas.registry import (
    AccountViewV1,
    AvailabilityV1,
    PageMetaV1,
)
from pydantic import BaseModel, ConfigDict


class _ClosedV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BudgetOverviewContextWireV1(_ClosedV1):
    report_id: str
    scope_generation: int
    scope_id: str | None
    scope_evidence: Literal["provider_verified", "owner_asserted", "unresolved"]
    source_id: str
    source_category: str
    cost_basis: str
    currency: str | None
    spend: ExactMoneyWireV1 | None
    spend_reason: str
    source_data_through: datetime | None
    collected_at: datetime
    completeness: Literal["complete", "partial", "unknown"]


class BudgetOverviewFundWireV1(_ClosedV1):
    component_id: str
    kind: Literal[
        "balance", "included_credits", "purchased_credits", "soft_limit", "hard_limit"
    ]
    remaining: ExactMoneyFieldWireV1
    limit: ExactMoneyFieldWireV1
    percentage_text: str | None
    is_low: bool | None
    percentage_reason: str
    is_constraining: bool | None
    collected_at: datetime
    observed_at: datetime | None
    freshness: str
    observation_id: str
    percentage_method: str | None
    percentage_decimal_places: int | None
    percentage_rounding: str | None


class BudgetOverviewRowWireV1(_ClosedV1):
    row_id: str
    account: AccountViewV1
    resource_id: str | None
    resource_kind: Literal["billing", "cloud", "unconfigured"]
    monitoring_enabled: bool
    state_code: str
    state_rank: int
    contexts: list[BudgetOverviewContextWireV1]
    funds: list[BudgetOverviewFundWireV1]
    collection_state: str | None
    collection_error: str | None
    funds_reason_code: str | None


class BudgetOverviewSummaryWireV1(_ClosedV1):
    scope_kind: Literal["global", "organization"]
    organization_id: str | None
    currency: str
    cost_basis: str
    source_category: str
    total: ExactMoneyWireV1
    included_pool_count: int
    excluded_resource_count: int


class BudgetOverviewExclusionWireV1(_ClosedV1):
    reason_code: str
    count: int


class BudgetOverviewWireV1(_ClosedV1):
    period: BudgetPeriodWireV1
    as_of: datetime
    items: list[BudgetOverviewRowWireV1]
    page: PageMetaV1
    availability: AvailabilityV1
    summaries: list[BudgetOverviewSummaryWireV1]
    exclusions: list[BudgetOverviewExclusionWireV1]
    summary_reason: str | None
    inventory_count: int
    registry_revision: int
    subscription_account_ids: list[str]


class BudgetSelectedReportWireV1(_ClosedV1):
    report: BudgetReportWireV1
    reported_spend: BudgetReportedSpendWireV1
    as_of: datetime

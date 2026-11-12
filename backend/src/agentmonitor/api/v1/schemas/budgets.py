"""Closed financial wire projections; exact amounts never become JSON numbers."""

from datetime import datetime
from typing import Literal

from agentmonitor.api.v1.schemas.capacity import (
    CapacityObservationProvenanceWireV1,
    CapacitySubjectWireV2,
    ExactQuantityWireV1,
)
from agentmonitor.api.v1.schemas.registry import (
    AvailabilityV1,
    BillingConnectionViewV1,
    PageMetaV1,
)
from agentmonitor.contracts.capacity_v1 import (
    BudgetDimensionKindV1,
    CompletenessV1,
    ConfidenceV1,
    ValueKindV1,
)
from agentmonitor.contracts.collection_control_v1 import CollectionRunStateV1
from agentmonitor.contracts.common_provenance_v1 import PrecisionV1
from agentmonitor.contracts.common_v1 import AvailabilityStateV1
from pydantic import BaseModel, ConfigDict, Field


class _ClosedV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BudgetPeriodWireV1(_ClosedV1):
    """UTC half-open reporting interval; not an inferred billing renewal."""

    start: datetime
    end: datetime


class ExactMoneyWireV1(_ClosedV1):
    """Currency units equal coefficient × 10**(-scale); signed costs preserved."""

    coefficient: str = Field(pattern=r"^-?(0|[1-9][0-9]{0,77})$")
    scale: int = Field(ge=0, le=18, strict=True)
    currency: str = Field(pattern=r"^[A-Z]{3}$")


class BudgetDimensionWireV1(_ClosedV1):
    kind: BudgetDimensionKindV1
    value: str | None


class BudgetCostBucketWireV1(_ClosedV1):
    bucket_key: str
    period: BudgetPeriodWireV1
    amount: ExactMoneyWireV1
    dimensions: list[BudgetDimensionWireV1]
    kind: Literal["charge", "adjustment"]


class BudgetUsageBucketWireV1(_ClosedV1):
    bucket_key: str
    period: BudgetPeriodWireV1
    quantity: ExactQuantityWireV1
    dimensions: list[BudgetDimensionWireV1]


class BudgetReportWireV1(_ClosedV1):
    """Immutable safe report facts; credential binding details are excluded."""

    report_id: str
    account_id: str
    resource_id: str
    provider_key: str
    scope_generation: int
    scope_id: str | None
    scope_evidence: Literal["provider_verified", "owner_asserted", "unresolved"]
    source_id: str
    source_category: str
    cost_basis: str
    grouping: list[BudgetDimensionKindV1]
    requested_period: BudgetPeriodWireV1
    covered_period: BudgetPeriodWireV1 | None
    source_data_through: datetime | None
    collected_at: datetime
    stored_at: datetime
    completeness: Literal["complete", "partial", "unknown"]
    omission_codes: list[str]
    currency: str | None
    empty_means_zero: bool
    cost_buckets: list[BudgetCostBucketWireV1]
    usage_buckets: list[BudgetUsageBucketWireV1]


class BudgetReportSelectionWireV1(_ClosedV1):
    current: BudgetReportWireV1 | None
    latest_attempt: BudgetReportWireV1 | None


class BudgetReportedSpendWireV1(_ClosedV1):
    """Application-calculated total for one report; null is never zero."""

    report_id: str
    total: ExactMoneyWireV1 | None
    reason_code: str


class BudgetCollectionStateWireV1(_ClosedV1):
    """Latest collection can fail without producing a report."""

    run_id: str
    state: CollectionRunStateV1
    source_id: str
    requested_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    outcome_code: str | None
    error_code: str | None
    report_id: str | None


class BudgetResourceCurrentWireV1(_ClosedV1):
    connection: BillingConnectionViewV1
    reports: list[BudgetReportSelectionWireV1]
    report_availability: AvailabilityV1
    reported_spend: list[BudgetReportedSpendWireV1]
    latest_collection: BudgetCollectionStateWireV1 | None
    collection_availability: AvailabilityV1


class BudgetCloudResourceCurrentWireV1(_ClosedV1):
    """Safe existing-resource projection; no credential binding identifiers."""

    account_id: str
    resource_id: str
    lifecycle: str
    reports: list[BudgetReportSelectionWireV1]
    report_availability: AvailabilityV1
    reported_spend: list[BudgetReportedSpendWireV1]
    latest_collection: BudgetCollectionStateWireV1 | None
    collection_availability: AvailabilityV1


class ExactMoneyFieldWireV1(_ClosedV1):
    availability: AvailabilityStateV1
    value: ExactMoneyWireV1 | None
    precision: PrecisionV1
    confidence: ConfidenceV1
    value_kind: ValueKindV1
    reason_code: str | None


class BudgetFundComponentWireV1(_ClosedV1):
    subject: CapacitySubjectWireV2
    component_id: str
    kind: Literal[
        "balance", "included_credits", "purchased_credits", "soft_limit", "hard_limit"
    ]
    remaining: ExactMoneyFieldWireV1
    limit: ExactMoneyFieldWireV1
    period: BudgetPeriodWireV1 | None
    renewal_at: datetime | None
    expires_at: datetime | None
    is_constraining: bool | None
    scope_evidence: Literal["provider_verified", "owner_asserted", "unresolved"]
    observation_id: str
    collection_run_id: str
    observed_at: datetime | None
    collected_at: datetime
    stored_at: datetime
    freshness: Literal[
        "fresh", "stale", "freshness_unknown", "conflicted", "no_observation"
    ]
    completeness: CompletenessV1
    provenance: CapacityObservationProvenanceWireV1


class AccountBudgetFundsWireV1(_ClosedV1):
    account_id: str
    as_of: datetime
    availability: AvailabilityV1
    components: list[BudgetFundComponentWireV1]
    registry_revision: int


class AccountBudgetCurrentWireV1(_ClosedV1):
    account_id: str
    period: BudgetPeriodWireV1
    as_of: datetime
    availability: AvailabilityV1
    resources: list[BudgetResourceCurrentWireV1]
    funds: AccountBudgetFundsWireV1 | None = None
    cloud_resources: list[BudgetCloudResourceCurrentWireV1] = Field(
        default_factory=list
    )


class BudgetReportSummaryWireV1(_ClosedV1):
    """Immutable report metadata and counts; facts are paged separately."""

    report_id: str
    account_id: str
    resource_id: str
    provider_key: str
    scope_generation: int
    scope_id: str | None
    scope_evidence: Literal["provider_verified", "owner_asserted", "unresolved"]
    source_id: str
    source_category: str
    cost_basis: str
    grouping: list[BudgetDimensionKindV1]
    requested_period: BudgetPeriodWireV1
    covered_period: BudgetPeriodWireV1 | None
    source_data_through: datetime | None
    collected_at: datetime
    stored_at: datetime
    completeness: Literal["complete", "partial", "unknown"]
    omission_codes: list[str]
    currency: str | None
    empty_means_zero: bool
    cost_bucket_count: int = Field(ge=0)
    usage_bucket_count: int = Field(ge=0)


class BudgetReportSummarySelectionWireV1(_ClosedV1):
    current: BudgetReportSummaryWireV1 | None
    latest_attempt: BudgetReportSummaryWireV1 | None


class BudgetResourceSummaryWireV1(_ClosedV1):
    connection: BillingConnectionViewV1
    reports: list[BudgetReportSummarySelectionWireV1]
    report_availability: AvailabilityV1
    reported_spend: list[BudgetReportedSpendWireV1]
    latest_collection: BudgetCollectionStateWireV1 | None
    collection_availability: AvailabilityV1


class BudgetCloudResourceSummaryWireV1(_ClosedV1):
    account_id: str
    resource_id: str
    lifecycle: str
    reports: list[BudgetReportSummarySelectionWireV1]
    report_availability: AvailabilityV1
    reported_spend: list[BudgetReportedSpendWireV1]
    latest_collection: BudgetCollectionStateWireV1 | None
    collection_availability: AvailabilityV1


class AccountBudgetSummaryWireV1(_ClosedV1):
    account_id: str
    period: BudgetPeriodWireV1
    as_of: datetime
    availability: AvailabilityV1
    resources: list[BudgetResourceSummaryWireV1]
    funds: AccountBudgetFundsWireV1 | None = None
    cloud_resources: list[BudgetCloudResourceSummaryWireV1] = Field(
        default_factory=list
    )


class BudgetHistoryChartPointWireV1(_ClosedV1):
    series_key: str
    label: str
    magnitude_basis_points: int = Field(ge=0, le=10000)
    direction: Literal["positive", "negative", "zero"]


class BudgetHistoryRowWireV1(_ClosedV1):
    kind: Literal["cost", "usage"]
    cost: BudgetCostBucketWireV1 | None
    usage: BudgetUsageBucketWireV1 | None
    chart: BudgetHistoryChartPointWireV1 | None = None
    chart_unavailable_reason: Literal["source_interval_not_daily"] | None = None


class BudgetHistoryWireV1(_ClosedV1):
    report: BudgetReportSummaryWireV1
    reported_spend: BudgetReportedSpendWireV1
    as_of: datetime
    items: list[BudgetHistoryRowWireV1]
    page: PageMetaV1
    availability: AvailabilityV1


class BudgetReportListWireV1(_ClosedV1):
    account_id: str
    resource_id: str
    period: BudgetPeriodWireV1
    as_of: datetime
    items: list[BudgetReportSummaryWireV1]
    page: PageMetaV1
    availability: AvailabilityV1

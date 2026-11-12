"""Additive CTR-CAP-006 account financial read; no transport or I/O behavior."""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import ClassVar, Literal, Protocol

from agentmonitor.contracts.capacity_v1 import (
    BudgetCostBucketV1,
    BudgetPeriodV1,
    BudgetReportHistoryQueryV1,
    BudgetReportSelectionV1,
    BudgetReportViewV1,
    BudgetUsageBucketV1,
    CapacityObservationProvenanceViewV1,
    CapacitySubjectV2,
    CompletenessV1,
    ExactMoneyFieldV1,
)
from agentmonitor.contracts.collection_control_v1 import (
    BillingBudgetReportContextV1,
    BudgetCollectionRunViewV1,
    CloudBudgetReportContextV1,
)
from agentmonitor.contracts.common_quantity_v1 import ExactMoneyV1
from agentmonitor.contracts.common_v1 import (
    OpaqueIdV1,
    QueryAvailabilityV1,
    QueryPageV1,
    TechnicalValueV1,
)
from agentmonitor.contracts.registry_billing_v1 import BillingConnectionViewV1
from agentmonitor.contracts.registry_v1 import AccountViewV1, CloudMonitoringTargetV1


@dataclass(frozen=True, slots=True)
class BudgetFundComponentV1(TechnicalValueV1):
    """One observed fund component; it does not establish account exhaustion."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-006"
    CONTRACT_VERSION: ClassVar[str] = "2.3.0"
    OWNER: ClassVar[str] = "PLAN-M05"
    subject: CapacitySubjectV2
    component_id: OpaqueIdV1
    kind: Literal[
        "balance", "included_credits", "purchased_credits", "soft_limit", "hard_limit"
    ]
    remaining: ExactMoneyFieldV1
    limit: ExactMoneyFieldV1
    period: BudgetPeriodV1 | None
    renewal_at: datetime | None
    expires_at: datetime | None
    is_constraining: bool | None
    scope_evidence: Literal["provider_verified", "owner_asserted", "unresolved"]
    observation_id: OpaqueIdV1
    collection_run_id: OpaqueIdV1
    observed_at: datetime | None
    collected_at: datetime
    stored_at: datetime
    freshness: Literal[
        "fresh", "stale", "freshness_unknown", "conflicted", "no_observation"
    ]
    completeness: CompletenessV1
    provenance: CapacityObservationProvenanceViewV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            self.collected_at > self.stored_at
            or self.observed_at is not None
            and self.observed_at > self.collected_at
            or self.is_constraining is not None
            and type(self.is_constraining) is not bool
            or self.remaining.value is not None
            and self.limit.value is not None
            and self.remaining.value.currency != self.limit.value.currency
        ):
            raise ValueError("budget_fund_component_invalid")


@dataclass(frozen=True, slots=True)
class AccountBudgetFundsV1(TechnicalValueV1):
    """Independent stored funds read, including accounts without spend reports."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-006"
    CONTRACT_VERSION: ClassVar[str] = "2.3.0"
    OWNER: ClassVar[str] = "PLAN-M05"
    account_id: OpaqueIdV1
    as_of: datetime
    availability: QueryAvailabilityV1
    components: tuple[BudgetFundComponentV1, ...]
    registry_revision: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            self.availability.as_of != self.as_of
            or type(self.registry_revision) is not int
            or self.registry_revision < 0
            or any(
                c.subject.account_id != self.account_id or c.stored_at > self.as_of
                for c in self.components
            )
            or len({(c.subject.resource_id, c.component_id) for c in self.components})
            != len(self.components)
        ):
            raise ValueError("budget_funds_query_invalid")


class AccountBudgetFundsPortV1(Protocol):
    def __call__(
        self, account_id: OpaqueIdV1, *, as_of: datetime
    ) -> AccountBudgetFundsV1: ...


@dataclass(frozen=True, slots=True)
class BudgetReportedSpendV1(TechnicalValueV1):
    """One selected report's calculated spend; never a mixed-context total."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-006"
    CONTRACT_VERSION: ClassVar[str] = "2.2.0"
    OWNER: ClassVar[str] = "PLAN-M05"
    report_id: OpaqueIdV1
    total: ExactMoneyV1 | None
    reason_code: str


@dataclass(frozen=True, slots=True)
class BudgetResourceCurrentV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-006"
    CONTRACT_VERSION: ClassVar[str] = "2.2.0"
    OWNER: ClassVar[str] = "PLAN-M05"
    connection: BillingConnectionViewV1
    reports: tuple[BudgetReportSelectionV1, ...]
    report_availability: QueryAvailabilityV1
    reported_spend: tuple[BudgetReportedSpendV1, ...]
    latest_collection: BudgetCollectionRunViewV1 | None
    collection_availability: QueryAvailabilityV1


@dataclass(frozen=True, slots=True)
class BudgetCloudResourceCurrentV1(TechnicalValueV1):
    """Existing cloud resource, without inventing an independent billing enrollment."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-006"
    CONTRACT_VERSION: ClassVar[str] = "2.4.0"
    OWNER: ClassVar[str] = "PLAN-M05"
    target: CloudMonitoringTargetV1
    reports: tuple[BudgetReportSelectionV1, ...]
    report_availability: QueryAvailabilityV1
    reported_spend: tuple[BudgetReportedSpendV1, ...]
    latest_collection: BudgetCollectionRunViewV1 | None
    collection_availability: QueryAvailabilityV1


@dataclass(frozen=True, slots=True)
class AccountBudgetCurrentV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-006"
    CONTRACT_VERSION: ClassVar[str] = "2.4.0"
    OWNER: ClassVar[str] = "PLAN-M05"
    account_id: OpaqueIdV1
    period: BudgetPeriodV1
    as_of: datetime
    availability: QueryAvailabilityV1
    resources: tuple[BudgetResourceCurrentV1, ...]
    funds: AccountBudgetFundsV1 | None = None
    cloud_resources: tuple[BudgetCloudResourceCurrentV1, ...] = ()

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            self.period.end > self.as_of
            or self.availability.as_of != self.as_of
            or any(
                item.connection.account_id != self.account_id for item in self.resources
            )
            or len({item.connection.resource_id for item in self.resources})
            != len(self.resources)
            or any(
                item.target.account_id != self.account_id
                for item in self.cloud_resources
            )
            or len({item.target.resource_id for item in self.cloud_resources})
            != len(self.cloud_resources)
            or {item.connection.resource_id for item in self.resources}
            & {item.target.resource_id for item in self.cloud_resources}
            or self.funds is not None
            and (
                self.funds.account_id != self.account_id
                or self.funds.as_of != self.as_of
            )
        ):
            raise ValueError("budget_account_query_invalid")


class AccountBudgetCurrentPortV1(Protocol):
    def __call__(
        self, account_id: OpaqueIdV1, *, period: BudgetPeriodV1, as_of: datetime
    ) -> AccountBudgetCurrentV1 | None: ...


class BudgetCollectionStatePortV1(Protocol):
    def get_latest_budget_run(
        self,
        account_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
        scope_generation: int,
        as_of: datetime,
        *,
        report_context: BillingBudgetReportContextV1
        | CloudBudgetReportContextV1
        | None = None,
    ) -> BudgetCollectionRunViewV1 | None: ...


@dataclass(frozen=True, slots=True)
class BudgetOverviewQueryV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-006"
    CONTRACT_VERSION: ClassVar[str] = "2.7.0"
    OWNER: ClassVar[str] = "PLAN-M05"
    period: BudgetPeriodV1
    as_of: datetime
    organization_ids: tuple[OpaqueIdV1, ...] | None = None
    include_ungrouped: bool = False
    provider_key: str | None = None
    limit: int = 50
    after_key: str | None = None
    sort_by: Literal["account", "organization", "state"] = "state"
    sort_direction: Literal["ascending", "descending"] = "ascending"

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            self.sort_by not in {"account", "organization", "state"}
            or self.sort_direction not in {"ascending", "descending"}
            or self.period.end > self.as_of
            or self.period.end - self.period.start
            not in {timedelta(days=7), timedelta(days=30)}
            or any(
                v.hour or v.minute or v.second or v.microsecond
                for v in (self.period.start, self.period.end)
            )
            or type(self.limit) is not int
            or not 1 <= self.limit <= 200
            or type(self.include_ungrouped) is not bool
            or self.organization_ids is not None
            and (
                not isinstance(self.organization_ids, tuple)
                or any(
                    not isinstance(value, OpaqueIdV1) for value in self.organization_ids
                )
                or len(self.organization_ids) > 100
                or len(set(self.organization_ids)) != len(self.organization_ids)
            )
            or self.provider_key is not None
            and self.provider_key not in {"claude", "codex", "ollama"}
            or self.after_key is not None
            and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", self.after_key) is None
        ):
            raise ValueError("budget_overview_query_invalid")


@dataclass(frozen=True, slots=True)
class BudgetOverviewContextV1(TechnicalValueV1):
    """Compact report selection; bucket bodies belong only on account/history reads."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-006"
    CONTRACT_VERSION: ClassVar[str] = "2.7.0"
    OWNER: ClassVar[str] = "PLAN-M05"
    report_id: OpaqueIdV1
    scope_generation: int
    scope_id: str | None
    scope_evidence: Literal["provider_verified", "owner_asserted", "unresolved"]
    source_id: str
    source_category: str
    cost_basis: str
    currency: str | None
    spend: ExactMoneyV1 | None
    spend_reason: str
    source_data_through: datetime | None
    collected_at: datetime
    completeness: Literal["complete", "partial", "unknown"]
    report_account_id: OpaqueIdV1 | None = None
    report_resource_id: OpaqueIdV1 | None = None


@dataclass(frozen=True, slots=True)
class BudgetOverviewFundV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-006"
    CONTRACT_VERSION: ClassVar[str] = "2.7.0"
    OWNER: ClassVar[str] = "PLAN-M05"
    component_id: OpaqueIdV1
    kind: Literal[
        "balance", "included_credits", "purchased_credits", "soft_limit", "hard_limit"
    ]
    remaining: ExactMoneyFieldV1
    limit: ExactMoneyFieldV1
    percentage_text: str | None
    is_low: bool | None
    percentage_reason: str
    is_constraining: bool | None
    collected_at: datetime
    observed_at: datetime | None
    freshness: str
    observation_id: OpaqueIdV1
    percentage_method: str | None = None
    percentage_decimal_places: int | None = None
    percentage_rounding: str | None = None
    source_account_id: OpaqueIdV1 | None = None
    source_resource_id: OpaqueIdV1 | None = None


@dataclass(frozen=True, slots=True)
class BudgetOverviewAccessPathV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-006"
    CONTRACT_VERSION: ClassVar[str] = "2.7.0"
    OWNER: ClassVar[str] = "PLAN-M05"
    account: AccountViewV1
    resource_id: OpaqueIdV1
    state_code: str
    monitoring_enabled: bool
    collection_error: str | None


@dataclass(frozen=True, slots=True)
class BudgetOverviewRowV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-006"
    CONTRACT_VERSION: ClassVar[str] = "2.7.0"
    OWNER: ClassVar[str] = "PLAN-M05"
    row_id: str
    account: AccountViewV1
    resource_id: OpaqueIdV1 | None
    resource_kind: Literal["billing", "cloud", "unconfigured"]
    monitoring_enabled: bool
    state_code: str
    state_rank: int
    contexts: tuple[BudgetOverviewContextV1, ...]
    funds: tuple[BudgetOverviewFundV1, ...]
    collection_state: str | None
    collection_error: str | None
    funds_reason_code: str | None = None
    pool_id: OpaqueIdV1 | None = None
    pool_name: str | None = None
    pool_selector: Literal["billing", "self", "team"] | None = None
    primary_organization_id: OpaqueIdV1 | None = None
    association_evidence: Literal["owner_asserted", "provider_verified"] | None = None
    counted_in_selection: bool = True
    access_paths: tuple[BudgetOverviewAccessPathV1, ...] = ()


@dataclass(frozen=True, slots=True)
class BudgetOverviewSummaryV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-006"
    CONTRACT_VERSION: ClassVar[str] = "2.7.0"
    OWNER: ClassVar[str] = "PLAN-M05"
    scope_kind: Literal["global", "organization"]
    organization_id: OpaqueIdV1 | None
    currency: str
    cost_basis: str
    source_category: str
    total: ExactMoneyV1
    included_pool_count: int
    excluded_resource_count: int


@dataclass(frozen=True, slots=True)
class BudgetOverviewExclusionV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-006"
    CONTRACT_VERSION: ClassVar[str] = "2.7.0"
    OWNER: ClassVar[str] = "PLAN-M05"
    reason_code: str
    count: int


@dataclass(frozen=True, slots=True)
class BudgetOverviewResultV1:
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-006"
    CONTRACT_VERSION: ClassVar[str] = "2.7.0"
    OWNER: ClassVar[str] = "PLAN-M05"
    period: BudgetPeriodV1
    as_of: datetime
    page: QueryPageV1[BudgetOverviewRowV1]
    summaries: tuple[BudgetOverviewSummaryV1, ...]
    exclusions: tuple[BudgetOverviewExclusionV1, ...]
    summary_reason: str | None
    inventory_count: int
    registry_revision: int
    subscription_account_ids: tuple[OpaqueIdV1, ...]


class BudgetAccountInventoryPortV1(Protocol):
    def page(
        self,
        provider_key: str | None,
        *,
        as_of: datetime,
        limit: int,
        after_key: str | None = None,
    ) -> QueryPageV1[AccountViewV1]: ...


class BudgetOverviewPortV1(Protocol):
    def __call__(self, query: BudgetOverviewQueryV1) -> BudgetOverviewResultV1: ...


@dataclass(frozen=True, slots=True)
class BudgetSelectedReportV1(TechnicalValueV1):
    """Explicit retained report, distinct from an account's current selection."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-006"
    CONTRACT_VERSION: ClassVar[str] = "2.5.0"
    OWNER: ClassVar[str] = "PLAN-M05"
    report: BudgetReportViewV1
    reported_spend: BudgetReportedSpendV1
    as_of: datetime


class BudgetSelectedReportPortV1(Protocol):
    def __call__(
        self,
        account_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
        report_id: OpaqueIdV1,
        *,
        period: BudgetPeriodV1,
        as_of: datetime,
    ) -> BudgetSelectedReportV1 | None: ...


@dataclass(frozen=True, slots=True)
class BudgetHistoryQueryV1(TechnicalValueV1):
    """One immutable report's facts; collection and report revisions are separate."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-006"
    CONTRACT_VERSION: ClassVar[str] = "2.8.0"
    OWNER: ClassVar[str] = "PLAN-M05"
    account_id: OpaqueIdV1
    resource_id: OpaqueIdV1
    report_id: OpaqueIdV1
    period: BudgetPeriodV1
    as_of: datetime
    limit: int = 50
    after_key: str | None = None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            self.period.end > self.as_of
            or self.period.end - self.period.start
            not in {timedelta(days=7), timedelta(days=30)}
            or any(
                value.hour or value.minute or value.second or value.microsecond
                for value in (self.period.start, self.period.end)
            )
            or type(self.limit) is not int
            or not 1 <= self.limit <= 200
        ):
            raise ValueError("budget_history_query_invalid")


@dataclass(frozen=True, slots=True)
class BudgetHistoryRowV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-006"
    CONTRACT_VERSION: ClassVar[str] = "2.8.0"
    OWNER: ClassVar[str] = "PLAN-M05"
    kind: Literal["cost", "usage"]
    cost: BudgetCostBucketV1 | None
    usage: BudgetUsageBucketV1 | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not (
            self.kind == "cost"
            and self.cost is not None
            and self.usage is None
            or self.kind == "usage"
            and self.usage is not None
            and self.cost is None
        ):
            raise ValueError("budget_history_row_invalid")


@dataclass(frozen=True, slots=True)
class BudgetHistoryResultV1:
    """API projects report metadata only; bucket bodies are bounded by page."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-006"
    CONTRACT_VERSION: ClassVar[str] = "2.8.0"
    OWNER: ClassVar[str] = "PLAN-M05"
    report: BudgetReportViewV1
    reported_spend: BudgetReportedSpendV1
    as_of: datetime
    page: QueryPageV1[BudgetHistoryRowV1]


class BudgetHistoryPortV1(Protocol):
    def __call__(self, query: BudgetHistoryQueryV1) -> BudgetHistoryResultV1 | None: ...


class BudgetReportHistoryPortV1(Protocol):
    """CTR-CAP-006 2.9.0: authorized retained revisions, never current authority."""

    def __call__(
        self, query: BudgetReportHistoryQueryV1
    ) -> QueryPageV1[BudgetReportViewV1] | None: ...

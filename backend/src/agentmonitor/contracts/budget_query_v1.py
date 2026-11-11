"""Additive CTR-CAP-006 account financial read; no transport or I/O behavior."""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Literal, Protocol

from agentmonitor.contracts.capacity_v1 import (
    BudgetPeriodV1,
    BudgetReportSelectionV1,
    CapacityObservationProvenanceViewV1,
    CapacitySubjectV2,
    CompletenessV1,
    ExactMoneyFieldV1,
)
from agentmonitor.contracts.collection_control_v1 import BudgetCollectionRunViewV1
from agentmonitor.contracts.common_quantity_v1 import ExactMoneyV1
from agentmonitor.contracts.common_v1 import (
    OpaqueIdV1,
    QueryAvailabilityV1,
    TechnicalValueV1,
)
from agentmonitor.contracts.registry_billing_v1 import BillingConnectionViewV1


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
class AccountBudgetCurrentV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-006"
    CONTRACT_VERSION: ClassVar[str] = "2.3.0"
    OWNER: ClassVar[str] = "PLAN-M05"
    account_id: OpaqueIdV1
    period: BudgetPeriodV1
    as_of: datetime
    availability: QueryAvailabilityV1
    resources: tuple[BudgetResourceCurrentV1, ...]
    funds: AccountBudgetFundsV1 | None = None

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
    ) -> BudgetCollectionRunViewV1 | None: ...

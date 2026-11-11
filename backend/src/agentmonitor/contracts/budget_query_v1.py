"""Additive CTR-CAP-006 account financial read; no transport or I/O behavior."""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Protocol

from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1, BudgetReportSelectionV1
from agentmonitor.contracts.collection_control_v1 import BudgetCollectionRunViewV1
from agentmonitor.contracts.common_quantity_v1 import ExactMoneyV1
from agentmonitor.contracts.common_v1 import (
    OpaqueIdV1,
    QueryAvailabilityV1,
    TechnicalValueV1,
)
from agentmonitor.contracts.registry_billing_v1 import BillingConnectionViewV1


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
    CONTRACT_VERSION: ClassVar[str] = "2.2.0"
    OWNER: ClassVar[str] = "PLAN-M05"
    account_id: OpaqueIdV1
    period: BudgetPeriodV1
    as_of: datetime
    availability: QueryAvailabilityV1
    resources: tuple[BudgetResourceCurrentV1, ...]

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

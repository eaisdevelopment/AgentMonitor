"""Bounded owner-initiated billing verification; contains no credential values."""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Protocol

from agentmonitor.contracts.collection_control_v1 import (
    BillingBudgetReportContextV1,
    BudgetCollectionRunViewV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1, TechnicalValueV1


@dataclass(frozen=True, slots=True)
class BillingCheckCommandV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-COL-002"
    CONTRACT_VERSION: ClassVar[str] = "2.2.0"
    OWNER: ClassVar[str] = "PLAN-M04"
    account_id: OpaqueIdV1
    resource_id: OpaqueIdV1
    expected_account_version: int
    expected_connection_version: int
    principal_id: OpaqueIdV1
    command_id: OpaqueIdV1
    requested_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if any(
            type(value) is not int or value < 1
            for value in (
                self.expected_account_version,
                self.expected_connection_version,
            )
        ):
            raise ValueError("billing_check_command_invalid")


@dataclass(frozen=True, slots=True)
class BillingCollectCommandV1(BillingCheckCommandV1):
    """One explicit read of the selected completed window; no preference change."""

    CONTRACT_VERSION: ClassVar[str] = "2.4.0"
    report_context: BillingBudgetReportContextV1

    def __post_init__(self) -> None:
        BillingCheckCommandV1.__post_init__(self)
        if (
            not isinstance(self.report_context, BillingBudgetReportContextV1)
            or self.requested_at < self.report_context.interval_end
        ):
            raise ValueError("billing_collect_command_invalid")


@dataclass(frozen=True, slots=True)
class BillingCollectionEligibilityV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-COL-002"
    CONTRACT_VERSION: ClassVar[str] = "2.4.0"
    OWNER: ClassVar[str] = "PLAN-M04"
    account_id: OpaqueIdV1
    resource_id: OpaqueIdV1
    account_record_version: int
    connection_record_version: int
    scope_generation: int
    binding_generation: int | None
    report_context: BillingBudgetReportContextV1
    can_collect: bool
    reason_code: str
    next_allowed_at: datetime | None
    checked_at: datetime


class BillingCheckPortV1(Protocol):
    def get_collect_eligibility(
        self,
        account_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
        report_context: BillingBudgetReportContextV1,
        as_of: datetime,
    ) -> BillingCollectionEligibilityV1 | None: ...

    def get_report_context(
        self, run_id: OpaqueIdV1
    ) -> BillingBudgetReportContextV1 | None: ...

    def collect(
        self, command: BillingCollectCommandV1
    ) -> BudgetCollectionRunViewV1: ...

    def check(self, command: BillingCheckCommandV1) -> BudgetCollectionRunViewV1: ...

    def get_status(self, run_id: OpaqueIdV1) -> BudgetCollectionRunViewV1 | None:
        """Read a durable billing run; absent/non-budget identifiers return None."""
        ...

"""Owner-selected cloud usage intent, without credentials or monitoring edits."""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Protocol

from agentmonitor.contracts.collection_control_v1 import (
    BudgetCollectionRunViewV1,
    CloudBudgetReportContextV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1, TechnicalValueV1


@dataclass(frozen=True, slots=True)
class CloudUsageCollectCommandV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-COL-002"
    CONTRACT_VERSION: ClassVar[str] = "2.5.0"
    OWNER: ClassVar[str] = "PLAN-M04"
    account_id: OpaqueIdV1
    resource_id: OpaqueIdV1
    expected_account_version: int
    expected_target_version: int
    principal_id: OpaqueIdV1
    command_id: OpaqueIdV1
    requested_at: datetime
    report_context: CloudBudgetReportContextV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            any(
                type(value) is not int or value < 1
                for value in (
                    self.expected_account_version,
                    self.expected_target_version,
                )
            )
            or not isinstance(self.report_context, CloudBudgetReportContextV1)
            or self.requested_at < self.report_context.interval_end
        ):
            raise ValueError("cloud_usage_command_invalid")


@dataclass(frozen=True, slots=True)
class CloudUsageEligibilityV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-COL-002"
    CONTRACT_VERSION: ClassVar[str] = "2.5.0"
    OWNER: ClassVar[str] = "PLAN-M04"
    account_id: OpaqueIdV1
    resource_id: OpaqueIdV1
    account_record_version: int
    target_record_version: int
    binding_generation: int | None
    report_context: CloudBudgetReportContextV1
    can_collect: bool
    reason_code: str
    next_allowed_at: datetime | None
    checked_at: datetime


class CloudUsageActionsPortV1(Protocol):
    def eligibility(
        self,
        account_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
        context: CloudBudgetReportContextV1,
        as_of: datetime,
    ) -> CloudUsageEligibilityV1 | None: ...

    def collect(
        self, command: CloudUsageCollectCommandV1
    ) -> BudgetCollectionRunViewV1: ...

    def get_status(
        self,
        account_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
        run_id: OpaqueIdV1,
    ) -> tuple[BudgetCollectionRunViewV1, CloudBudgetReportContextV1] | None: ...

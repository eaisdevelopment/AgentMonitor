"""Bounded owner-initiated billing verification; contains no credential values."""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Protocol

from agentmonitor.contracts.collection_control_v1 import BudgetCollectionRunViewV1
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


class BillingCheckPortV1(Protocol):
    def check(self, command: BillingCheckCommandV1) -> BudgetCollectionRunViewV1: ...

    def get_status(self, run_id: OpaqueIdV1) -> BudgetCollectionRunViewV1 | None:
        """Read a durable billing run; absent/non-budget identifiers return None."""
        ...

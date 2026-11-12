"""Additive CTR-CAP-007 2.0.0: query-time financial analysis, no stored forecast."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import ClassVar, Protocol

from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1, BudgetReportViewV1
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_quantity_v1 import ExactMoneyV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1, TechnicalValueV1


@dataclass(frozen=True, slots=True)
class BudgetSourceEvidenceV1(TechnicalValueV1):
    """Adapter-owned semantics for this exact retained report, not caller claims."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-007"
    CONTRACT_VERSION: ClassVar[str] = "2.0.0"
    OWNER: ClassVar[str] = "PLAN-M05"
    report_id: OpaqueIdV1
    policy_id: str
    policy_version: str
    disjoint_costs: bool
    corrections_resolved: bool
    zero_day_coverage: bool
    cost_freshness_deadline: datetime | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not self.policy_id
            or not self.policy_version
            or any(
                type(v) is not bool
                for v in (
                    self.disjoint_costs,
                    self.corrections_resolved,
                    self.zero_day_coverage,
                )
            )
            or self.cost_freshness_deadline is not None
            and self.cost_freshness_deadline.utcoffset() != timedelta(0)
        ):
            raise ValueError("budget_source_evidence_invalid")


class BudgetSourceEvidencePortV1(Protocol):
    def __call__(self, report: BudgetReportViewV1) -> BudgetSourceEvidenceV1 | None: ...


class BudgetReportProvenancePortV1(Protocol):
    def __call__(
        self, account_id: OpaqueIdV1, report_id: OpaqueIdV1
    ) -> ObservationProvenanceV1 | None: ...


@dataclass(frozen=True, slots=True)
class BudgetObservedRateV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-007"
    CONTRACT_VERSION: ClassVar[str] = "2.0.0"
    OWNER: ClassVar[str] = "PLAN-M05"
    cost: ExactMoneyV1
    covered_seconds: int
    period: BudgetPeriodV1
    input_report_ids: tuple[OpaqueIdV1, ...]
    input_bucket_keys: tuple[str, ...]
    day_count: int
    display_text: str | None
    display_rounding: str | None
    display_decimal_places: int | None


@dataclass(frozen=True, slots=True)
class BudgetForecastV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-007"
    CONTRACT_VERSION: ClassVar[str] = "2.0.0"
    OWNER: ClassVar[str] = "PLAN-M05"
    report: BudgetReportViewV1
    as_of: datetime
    rate: BudgetObservedRateV1 | None
    rate_reason: str
    exhaustion_reason: str
    exhaustion_at: datetime | None
    funds_observed_at: datetime | None
    input_observation_ids: tuple[OpaqueIdV1, ...]
    time_left_numerator: str | None
    time_left_denominator: str | None
    method_id: str
    method_version: str
    time_rounding: str
    source_evidence: BudgetSourceEvidenceV1 | None


class BudgetForecastPortV1(Protocol):
    def __call__(
        self,
        account_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
        report_id: OpaqueIdV1,
        *,
        period: BudgetPeriodV1,
        as_of: datetime,
    ) -> BudgetForecastV1 | None: ...

"""M05 capacity V1 contracts with explicit exactness and availability."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Literal

from agentmonitor.contracts.collection_control_v1 import (
    CollectionCommitReceiptV1,
    CollectionCommitStatusV1,
    CollectionOutcomeCommitV1,
)
from agentmonitor.contracts.common_quantity_v1 import (
    CanonicalDecimalV1,
    ExactQuantityV1,
)
from agentmonitor.contracts.common_v1 import (
    FieldAvailabilityV1,
    OpaqueIdV1,
    TechnicalValueV1,
)

PrecisionV1 = Literal["exact", "rounded", "range", "estimated", "unknown"]
ConfidenceV1 = Literal["confirmed", "high", "medium", "low", "unknown"]
ValueKindV1 = Literal[
    "authoritative", "provider_reported", "derived", "heuristic", "unknown"
]
CompletenessV1 = Literal["complete", "partial", "unknown"]
CapacityHealthStateV1 = Literal[
    "available",
    "constrained",
    "critical",
    "exhausted",
    "reauthentication_required",
    "unknown",
]

_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:@/-]{0,127}\Z")


class InvalidCapacityContractV1(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _token(value: object) -> bool:
    return type(value) is str and _TOKEN.fullmatch(value) is not None


@dataclass(frozen=True, slots=True)
class ExactMetricFieldV1(TechnicalValueV1):
    """An exact value paired with one explicit field-availability state."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-001"
    OWNER: ClassVar[str] = "PLAN-M05"

    availability: FieldAvailabilityV1
    value: ExactQuantityV1 | None
    precision: PrecisionV1
    confidence: ConfidenceV1
    value_kind: ValueKindV1
    reason_code: str | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if self.availability.state not in {
            "available",
            "unknown",
            "unsupported",
            "not_applicable",
            "withheld_or_denied",
            "stale",
        }:
            raise InvalidCapacityContractV1("capacity_field_availability_invalid")
        has_value = self.availability.state in {"available", "stale"}
        if has_value != (self.value is not None):
            raise InvalidCapacityContractV1("capacity_field_state_invalid")
        if has_value and self.reason_code is not None:
            raise InvalidCapacityContractV1("capacity_field_reason_invalid")
        if not has_value and not _token(self.reason_code):
            raise InvalidCapacityContractV1("capacity_field_reason_required")
        if not has_value and (
            self.precision != "unknown"
            or self.confidence != "unknown"
            or self.value_kind != "unknown"
        ):
            raise InvalidCapacityContractV1("capacity_unknown_metadata_invalid")


@dataclass(frozen=True, slots=True)
class CapacitySubjectV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-001"
    OWNER: ClassVar[str] = "PLAN-M05"

    provider_key: str
    installation_id: OpaqueIdV1
    account_id: OpaqueIdV1
    resource_id: OpaqueIdV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not _token(self.provider_key):
            raise InvalidCapacityContractV1("capacity_subject_invalid")


@dataclass(frozen=True, slots=True)
class ProviderQuotaWindowInputV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-001"
    OWNER: ClassVar[str] = "PLAN-M05"

    window_key: str
    safe_label: str | None
    semantic_role: str
    is_constraining: bool
    used: ExactMetricFieldV1
    remaining: ExactMetricFieldV1
    limit: ExactMetricFieldV1
    remaining_ratio: ExactMetricFieldV1
    reset_at: datetime | None
    reset_precision: PrecisionV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not _token(self.window_key) or not _token(self.semantic_role):
            raise InvalidCapacityContractV1("capacity_window_identity_invalid")
        if self.safe_label is not None and (
            self.safe_label != self.safe_label.strip()
            or not 1 <= len(self.safe_label) <= 128
            or not self.safe_label.isprintable()
        ):
            raise InvalidCapacityContractV1("capacity_window_label_invalid")
        if type(self.is_constraining) is not bool:
            raise InvalidCapacityContractV1("capacity_window_constraint_invalid")
        if (self.reset_at is None) != (self.reset_precision == "unknown"):
            raise InvalidCapacityContractV1("capacity_reset_pair_invalid")
        ratio = self.remaining_ratio.value
        if ratio is not None:
            if ratio.unit != "ratio" or not (0 <= ratio.as_decimal() <= 1):
                raise InvalidCapacityContractV1("capacity_ratio_invalid")
        quantities = tuple(
            field.value
            for field in (self.used, self.remaining, self.limit)
            if field.value is not None
        )
        if any(value.as_decimal() < 0 for value in quantities):
            raise InvalidCapacityContractV1("capacity_quantity_negative")
        if len({value.unit for value in quantities}) > 1:
            raise InvalidCapacityContractV1("capacity_quantity_unit_mismatch")


@dataclass(frozen=True, slots=True)
class ProviderQuotaInputV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-001"
    OWNER: ClassVar[str] = "PLAN-M05"

    subject: CapacitySubjectV1
    registry_revision: int
    capability_schema_version: str
    completeness: Literal["complete_scope", "partial_scope"]
    windows: tuple[ProviderQuotaWindowInputV1, ...]
    omission_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        keys = tuple(item.window_key for item in self.windows)
        if (
            not _token(self.capability_schema_version)
            or type(self.registry_revision) is not int
            or self.registry_revision < 1
            or not keys
            or len(keys) > 32
            or len(keys) != len(set(keys))
        ):
            raise InvalidCapacityContractV1("capacity_quota_batch_invalid")
        if self.omission_codes != tuple(sorted(set(self.omission_codes))) or not all(
            _token(code) for code in self.omission_codes
        ):
            raise InvalidCapacityContractV1("capacity_omission_codes_invalid")
        if (self.completeness == "partial_scope") != bool(self.omission_codes):
            raise InvalidCapacityContractV1("capacity_partial_omissions_required")


class CapacityCommitRequestV1(CollectionOutcomeCommitV1[ProviderQuotaInputV1]):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-004"
    OWNER: ClassVar[str] = "PLAN-M05"


class CapacityCommitReceiptV1(CollectionCommitReceiptV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-004"
    OWNER: ClassVar[str] = "PLAN-M05"


class CapacityCommitStatusV1(CollectionCommitStatusV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-004"
    OWNER: ClassVar[str] = "PLAN-M05"


@dataclass(frozen=True, slots=True)
class QuotaWindowViewV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-001"
    OWNER: ClassVar[str] = "PLAN-M05"

    window_id: OpaqueIdV1
    subject: CapacitySubjectV1
    window_key: str
    safe_label: str | None
    used: ExactMetricFieldV1
    remaining: ExactMetricFieldV1
    limit: ExactMetricFieldV1
    remaining_ratio: ExactMetricFieldV1
    freshness: Literal[
        "fresh", "stale", "freshness_unknown", "conflicted", "no_observation"
    ]
    current_observation_id: OpaqueIdV1
    collection_run_id: OpaqueIdV1
    observed_at: datetime | None
    collected_at: datetime
    stored_at: datetime


@dataclass(frozen=True, slots=True)
class CapacityHealthPolicyV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-003"
    OWNER: ClassVar[str] = "PLAN-M05"

    policy_id: str
    policy_version: str
    constrained_remaining_ratio: CanonicalDecimalV1
    critical_remaining_ratio: CanonicalDecimalV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        constrained = self.constrained_remaining_ratio.as_decimal()
        critical = self.critical_remaining_ratio.as_decimal()
        if (
            not _token(self.policy_id)
            or not _token(self.policy_version)
            or not 0 < critical < constrained < 1
        ):
            raise InvalidCapacityContractV1("capacity_health_policy_invalid")


@dataclass(frozen=True, slots=True)
class CapacityHealthViewV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-003"
    OWNER: ClassVar[str] = "PLAN-M05"

    state: CapacityHealthStateV1
    completeness: CompletenessV1
    freshness: Literal["fresh", "stale", "freshness_unknown", "conflicted"]
    constraining_window_id: str | None
    policy_id: str
    policy_version: str
    explanation_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AccountCapacityViewV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-001"
    OWNER: ClassVar[str] = "PLAN-M05"

    subject: CapacitySubjectV1
    windows: tuple[QuotaWindowViewV1, ...]
    health: CapacityHealthViewV1 | None


@dataclass(frozen=True, slots=True)
class BudgetViewV1(TechnicalValueV1):
    """Reserved exact budget view for the frozen V1 schema; no value is inferred."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-002"
    OWNER: ClassVar[str] = "PLAN-M05"

    budget_id: OpaqueIdV1
    subject: CapacitySubjectV1
    state: Literal["available", "unknown", "unsupported", "unavailable", "stale"]
    observed_at: datetime | None

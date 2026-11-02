"""M05 capacity V1 contracts with explicit exactness and availability."""

import re
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import ClassVar, Literal, Protocol

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
    QueryPageV1,
    TechnicalValueV1,
)
from agentmonitor.contracts.events_v1 import DurableEventBatchV1
from agentmonitor.contracts.registry_v1 import (
    AccountResourceViewV1,
    AccountViewV1,
    ProviderTargetRefV1,
    RegistryScopeKindV1,
    RegistryScopeSnapshotV1,
)

PrecisionV1 = Literal["exact", "rounded", "range", "estimated", "unknown"]
ConfidenceV1 = Literal["confirmed", "high", "medium", "low", "unknown"]
ValueKindV1 = Literal[
    "authoritative", "provider_reported", "derived", "heuristic", "unknown"
]
CompletenessV1 = Literal["complete", "partial", "unknown"]
SourceClassV1 = Literal[
    "documented_api",
    "supported_cli",
    "approved_local_metadata",
    "experimental_private_or_browser",
]
CapacityHealthStateV1 = Literal[
    "available",
    "constrained",
    "critical",
    "exhausted",
    "reauthentication_required",
    "unknown",
]
CapacityHistoryMetricV1 = Literal["used", "remaining", "limit", "remaining_ratio"]
CapacityHistorySeriesKindV1 = Literal["raw_provider", "poll_snapshot", "derived"]

_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:@/-]{0,127}\Z")
_PROVENANCE_MECHANISM_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:@/+-]{0,127}\Z")
_CURSOR_KEY = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")


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
class CapacitySubjectV2(TechnicalValueV1):
    """V2 subject with an explicit installation-or-cloud target."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-001"
    CONTRACT_VERSION: ClassVar[str] = "2.0.0"
    OWNER: ClassVar[str] = "PLAN-M05"

    provider_key: str
    provider_target: ProviderTargetRefV1
    account_id: OpaqueIdV1
    resource_id: OpaqueIdV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not _token(self.provider_key)
            or not isinstance(self.account_id, OpaqueIdV1)
            or not isinstance(self.resource_id, OpaqueIdV1)
        ):
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
    source_period_start: datetime | None = None

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
        if self.source_period_start is not None and (
            not isinstance(self.source_period_start, datetime)
            or self.source_period_start.utcoffset() != timedelta(0)
            or (
                self.reset_at is not None
                and (
                    self.reset_at.utcoffset() is None
                    or self.source_period_start >= self.reset_at
                )
            )
        ):
            raise InvalidCapacityContractV1("capacity_source_period_invalid")
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


@dataclass(frozen=True, slots=True)
class ProviderQuotaInputV2(TechnicalValueV1):
    """V2 quota batch retaining the discriminated provider target."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-001"
    CONTRACT_VERSION: ClassVar[str] = "2.0.0"
    OWNER: ClassVar[str] = "PLAN-M05"

    subject: CapacitySubjectV2
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


class CapacityCommitRequestV2(CollectionOutcomeCommitV1[ProviderQuotaInputV2]):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-004"
    CONTRACT_VERSION: ClassVar[str] = "2.0.0"
    OWNER: ClassVar[str] = "PLAN-M05"


class CapacityCommitReceiptV1(CollectionCommitReceiptV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-004"
    OWNER: ClassVar[str] = "PLAN-M05"


class CapacityCommitStatusV1(CollectionCommitStatusV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-004"
    OWNER: ClassVar[str] = "PLAN-M05"


@dataclass(frozen=True, slots=True)
class CapacityObservationProvenanceViewV1(TechnicalValueV1):
    """Persisted, safe source lineage for a capacity observation query."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-001"
    OWNER: ClassVar[str] = "PLAN-M05"

    capability_id: str
    capability_schema_version: str
    adapter_id: str
    adapter_version: str
    provider_protocol_version: str
    source_id: str
    source_class: SourceClassV1
    mechanism_version: str
    parser_version: str | None
    provider_version: str | None
    freshness_deadline: datetime | None
    freshness_policy_id: str
    precision: PrecisionV1
    confidence: ConfidenceV1
    confidence_reason_code: str
    is_experimental: bool
    decision_reference: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        required = (
            self.capability_id,
            self.capability_schema_version,
            self.adapter_id,
            self.adapter_version,
            self.provider_protocol_version,
            self.source_id,
            self.freshness_policy_id,
            self.confidence_reason_code,
            self.decision_reference,
        )
        if not all(_token(value) for value in required) or not (
            type(self.mechanism_version) is str
            and _PROVENANCE_MECHANISM_TOKEN.fullmatch(self.mechanism_version)
        ):
            raise InvalidCapacityContractV1("capacity_provenance_invalid")
        if self.parser_version is not None and not _token(self.parser_version):
            raise InvalidCapacityContractV1("capacity_provenance_parser_invalid")
        if self.provider_version is not None and not _token(self.provider_version):
            raise InvalidCapacityContractV1("capacity_provenance_provider_invalid")
        if type(self.is_experimental) is not bool:
            raise InvalidCapacityContractV1("capacity_provenance_experimental_invalid")


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
    provenance: CapacityObservationProvenanceViewV1
    freshness: Literal[
        "fresh", "stale", "freshness_unknown", "conflicted", "no_observation"
    ]
    current_observation_id: OpaqueIdV1
    collection_run_id: OpaqueIdV1
    observed_at: datetime | None
    collected_at: datetime
    stored_at: datetime
    semantic_role: str | None = None
    is_constraining: bool | None = None
    definition_version: int | None = None
    reset_at: datetime | None = None
    reset_precision: PrecisionV1 = "unknown"
    registry_revision: int | None = None
    projection_version: int | None = None
    completeness: CompletenessV1 = "unknown"


@dataclass(frozen=True, slots=True)
class QuotaWindowViewV2(TechnicalValueV1):
    """V2 quota view retaining a cloud-or-installation target."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-001"
    CONTRACT_VERSION: ClassVar[str] = "2.0.0"
    OWNER: ClassVar[str] = "PLAN-M05"

    window_id: OpaqueIdV1
    subject: CapacitySubjectV2
    window_key: str
    safe_label: str | None
    used: ExactMetricFieldV1
    remaining: ExactMetricFieldV1
    limit: ExactMetricFieldV1
    remaining_ratio: ExactMetricFieldV1
    provenance: CapacityObservationProvenanceViewV1
    freshness: Literal[
        "fresh", "stale", "freshness_unknown", "conflicted", "no_observation"
    ]
    current_observation_id: OpaqueIdV1
    collection_run_id: OpaqueIdV1
    observed_at: datetime | None
    collected_at: datetime
    stored_at: datetime
    semantic_role: str | None = None
    is_constraining: bool | None = None
    definition_version: int | None = None
    reset_at: datetime | None = None
    reset_precision: PrecisionV1 = "unknown"
    registry_revision: int | None = None
    projection_version: int | None = None
    completeness: CompletenessV1 = "unknown"


QuotaWindowViewV1OrV2 = QuotaWindowViewV1 | QuotaWindowViewV2


@dataclass(frozen=True, slots=True)
class QuotaAllowanceV1:
    """M05 display derivation with the original observation left intact."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-001"
    OWNER: ClassVar[str] = "PLAN-M05"

    remaining_percentage: ExactMetricFieldV1
    calculation: Literal["remaining_ratio_times_100", "100_minus_used_percent"]
    input_observation_id: OpaqueIdV1


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
class AccountCapacityViewV2(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-001"
    CONTRACT_VERSION: ClassVar[str] = "2.0.0"
    OWNER: ClassVar[str] = "PLAN-M05"

    subject: CapacitySubjectV2
    windows: tuple[QuotaWindowViewV2, ...]
    health: CapacityHealthViewV1 | None


AccountCapacityViewV1OrV2 = AccountCapacityViewV1 | AccountCapacityViewV2


@dataclass(frozen=True, slots=True)
class CapacityHistoryQueryV1(TechnicalValueV1):
    """One bounded, side-effect-free immutable quota-history selection."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-006"
    OWNER: ClassVar[str] = "PLAN-M05"

    subject_id: OpaqueIdV1
    resource_id: OpaqueIdV1 | None
    window_id: OpaqueIdV1 | None
    metric: CapacityHistoryMetricV1
    series_kind: CapacityHistorySeriesKindV1
    range_start: datetime
    range_before: datetime
    as_of: datetime
    limit: int
    after_key: str | None
    bucket_method: str | None
    bucket_seconds: int | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if self.range_start >= self.range_before:
            raise InvalidCapacityContractV1("capacity_history_range_invalid")
        if self.range_before - self.range_start > timedelta(days=365):
            raise InvalidCapacityContractV1("capacity_history_range_too_large")
        if type(self.limit) is not int or not 1 <= self.limit <= 200:
            raise InvalidCapacityContractV1("capacity_history_limit_invalid")
        if self.after_key is not None and _CURSOR_KEY.fullmatch(self.after_key) is None:
            raise InvalidCapacityContractV1("capacity_history_cursor_invalid")
        if self.bucket_method is not None or self.bucket_seconds is not None:
            raise InvalidCapacityContractV1("capacity_history_bucket_unsupported")

    def with_cursor(self, after_key: str | None) -> "CapacityHistoryQueryV1":
        return replace(self, after_key=after_key)


@dataclass(frozen=True, slots=True)
class CapacityHistoryPointV1(TechnicalValueV1):
    """One persisted point; no bucket, interpolation, or value is invented."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-006"
    OWNER: ClassVar[str] = "PLAN-M05"

    observation_id: OpaqueIdV1
    window_id: OpaqueIdV1
    window_definition_id: OpaqueIdV1
    subject: CapacitySubjectV1
    window_key: str
    safe_label: str | None
    semantic_role: str
    native_unit: str | None
    definition_version: int
    metric: CapacityHistoryMetricV1
    series_kind: CapacityHistorySeriesKindV1
    value: ExactMetricFieldV1
    provenance: CapacityObservationProvenanceViewV1
    freshness: Literal["fresh", "stale", "freshness_unknown"]
    completeness: CompletenessV1
    collection_run_id: OpaqueIdV1
    derivation_id: OpaqueIdV1 | None
    observed_at: datetime
    interval_start: datetime | None
    interval_end: datetime | None
    reset_at: datetime | None
    reset_precision: PrecisionV1
    collected_at: datetime
    stored_at: datetime
    source_period_start: datetime | None = None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not _token(self.window_key)
            or not _token(self.semantic_role)
            or type(self.definition_version) is not int
            or self.definition_version < 1
            or (self.interval_start is None) != (self.interval_end is None)
            or (
                self.interval_start is not None
                and self.interval_end is not None
                and self.interval_start >= self.interval_end
            )
            or (self.reset_at is None) != (self.reset_precision == "unknown")
        ):
            raise InvalidCapacityContractV1("capacity_history_point_invalid")

    @property
    def cursor_key(self) -> str:
        return self.observation_id.value


@dataclass(frozen=True, slots=True)
class CapacityHistoryPointV2(TechnicalValueV1):
    """V2 history point retaining a cloud-or-installation target."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-006"
    CONTRACT_VERSION: ClassVar[str] = "2.0.0"
    OWNER: ClassVar[str] = "PLAN-M05"

    observation_id: OpaqueIdV1
    window_id: OpaqueIdV1
    window_definition_id: OpaqueIdV1
    subject: CapacitySubjectV2
    window_key: str
    safe_label: str | None
    semantic_role: str
    native_unit: str | None
    definition_version: int
    metric: CapacityHistoryMetricV1
    series_kind: CapacityHistorySeriesKindV1
    value: ExactMetricFieldV1
    provenance: CapacityObservationProvenanceViewV1
    freshness: Literal["fresh", "stale", "freshness_unknown"]
    completeness: CompletenessV1
    collection_run_id: OpaqueIdV1
    derivation_id: OpaqueIdV1 | None
    observed_at: datetime
    interval_start: datetime | None
    interval_end: datetime | None
    reset_at: datetime | None
    reset_precision: PrecisionV1
    collected_at: datetime
    stored_at: datetime
    source_period_start: datetime | None = None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not _token(self.window_key)
            or not _token(self.semantic_role)
            or type(self.definition_version) is not int
            or self.definition_version < 1
            or (self.interval_start is None) != (self.interval_end is None)
            or (
                self.interval_start is not None
                and self.interval_end is not None
                and self.interval_start >= self.interval_end
            )
            or (self.reset_at is None) != (self.reset_precision == "unknown")
        ):
            raise InvalidCapacityContractV1("capacity_history_point_invalid")

    @property
    def cursor_key(self) -> str:
        return self.observation_id.value


CapacityHistoryPointV1OrV2 = CapacityHistoryPointV1 | CapacityHistoryPointV2


@dataclass(frozen=True, slots=True)
class BudgetViewV1(TechnicalValueV1):
    """Reserved exact budget view for the frozen V1 schema; no value is inferred."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-002"
    OWNER: ClassVar[str] = "PLAN-M05"

    budget_id: OpaqueIdV1
    subject: CapacitySubjectV1
    state: Literal["available", "unknown", "unsupported", "unavailable", "stale"]
    observed_at: datetime | None


CapacityAlertAvailabilityV1 = Literal[
    "current", "stale", "unknown", "unsupported", "unavailable"
]


@dataclass(frozen=True, slots=True)
class CapacityCommittedNoticeV1(TechnicalValueV1):
    """The existing commit notice does not assert capacity condition truth."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-004"
    OWNER: ClassVar[str] = "PLAN-M05"

    capability_id: str
    projection_count: int
    state: Literal["succeeded", "partial"]

    def __post_init__(self) -> None:
        if self.state not in {"succeeded", "partial"}:
            raise InvalidCapacityContractV1("capacity_commit_notice_invalid")
        TechnicalValueV1.__post_init__(self)
        if (
            not _token(self.capability_id)
            or type(self.projection_count) is not int
            or not 1 <= self.projection_count <= 32
            or self.state not in {"succeeded", "partial"}
        ):
            raise InvalidCapacityContractV1("capacity_commit_notice_invalid")


CapacityAlertReasonV1 = Literal[
    "capacity_ratio_current",
    "capacity_used_percent_current",
    "capacity_reading_stale",
    "capacity_reading_conflicted",
    "capacity_reading_partial",
    "capacity_freshness_unknown",
    "capacity_ratio_unsupported",
    "capacity_ratio_unavailable",
    "capacity_ratio_unknown",
    "capacity_nonconstraining",
]
CAPACITY_ALERT_REASON_CODES = frozenset(
    {
        "capacity_ratio_current",
        "capacity_used_percent_current",
        "capacity_reading_stale",
        "capacity_reading_conflicted",
        "capacity_reading_partial",
        "capacity_freshness_unknown",
        "capacity_ratio_unsupported",
        "capacity_ratio_unavailable",
        "capacity_ratio_unknown",
        "capacity_nonconstraining",
    }
)


@dataclass(frozen=True, slots=True)
class CapacityAlertConditionV1(TechnicalValueV1):
    """Current producer fact; event/run generations never stand in for its revision."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-005"
    OWNER: ClassVar[str] = "PLAN-M05"

    resource_id: OpaqueIdV1
    account_id: OpaqueIdV1
    provider_key: str
    window_id: OpaqueIdV1
    generation: int
    remaining_basis_points: CanonicalDecimalV1 | None
    denominator_kind: Literal["remaining_ratio", "used_percent_complement", "unknown"]
    availability: CapacityAlertAvailabilityV1
    exhausted: bool | None
    reset_at: datetime | None
    freshness_deadline: datetime | None
    observation_ids: tuple[OpaqueIdV1, ...]
    precision: PrecisionV1
    confidence: ConfidenceV1
    reason_code: CapacityAlertReasonV1
    observed_at: datetime | None
    recorded_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        current = self.availability == "current"
        if (
            not _token(self.provider_key)
            or type(self.generation) is not int
            or self.generation < 1
            or not 1 <= len(self.observation_ids) <= 32
            or len(set(self.observation_ids)) != len(self.observation_ids)
            or self.reason_code not in CAPACITY_ALERT_REASON_CODES
            or current != (self.remaining_basis_points is not None)
            or current != (self.exhausted is not None)
            or current
            and self.denominator_kind == "unknown"
            or self.remaining_basis_points is not None
            and not 0 <= self.remaining_basis_points.as_decimal() <= 10000
        ):
            raise InvalidCapacityContractV1("capacity_alert_condition_invalid")


@dataclass(frozen=True, slots=True)
class CapacityAlertConditionQueryV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-005"
    OWNER: ClassVar[str] = "PLAN-M05"

    account_id: OpaqueIdV1
    resource_id: OpaqueIdV1 | None
    window_id: OpaqueIdV1 | None
    as_of: datetime
    limit: int = 50
    after_key: str | None = None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.limit) is not int
            or not 1 <= self.limit <= 200
            or self.after_key is not None
            and _CURSOR_KEY.fullmatch(self.after_key) is None
        ):
            raise InvalidCapacityContractV1("capacity_alert_query_invalid")


class ListCapacityAlertConditionsV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-005"
    OWNER: ClassVar[str] = "PLAN-M05"

    def __call__(
        self, query: CapacityAlertConditionQueryV1
    ) -> QueryPageV1[CapacityAlertConditionV1]: ...


class ReadCapacityEventsV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-004"
    OWNER: ClassVar[str] = "PLAN-M05"

    def __call__(
        self,
        consumer_key: str,
        after_cursor: str | None,
        as_of: datetime,
        limit: int = 200,
    ) -> DurableEventBatchV1[CapacityCommittedNoticeV1]: ...


class AcknowledgeCapacityEventV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-004"
    OWNER: ClassVar[str] = "PLAN-M05"

    def __call__(
        self,
        consumer_key: str,
        event_id: OpaqueIdV1,
        payload_digest: str,
        receipt_id: OpaqueIdV1,
        as_of: datetime,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class CapacityAggregateQueryV1(TechnicalValueV1):
    """One revision-consistent membership, never a live registry join."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-003"
    OWNER: ClassVar[str] = "PLAN-M05"

    scope_snapshot: RegistryScopeSnapshotV1
    accounts: tuple[AccountViewV1, ...]
    resources: tuple[AccountResourceViewV1, ...]
    as_of: datetime
    policy: CapacityHealthPolicyV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        scope = self.scope_snapshot
        account_ids = tuple(a.account_id for a in self.accounts)
        resource_ids = tuple(r.resource_id for r in self.resources)
        if (
            len(account_ids) != len(set(account_ids))
            or len(resource_ids) != len(set(resource_ids))
            or set(account_ids) != set(scope.account_ids)
            or set(resource_ids) != set(scope.resource_ids)
            or any(r.account_id not in account_ids for r in self.resources)
            or len(account_ids) > 200
            or len(resource_ids) > 2000
        ):
            raise InvalidCapacityContractV1("capacity_aggregate_membership_invalid")
        if any(
            item.registry_revision != scope.registry_revision for item in self.accounts
        ) or any(
            item.registry_revision != scope.registry_revision for item in self.resources
        ):
            raise InvalidCapacityContractV1("registry_scope_changed")


@dataclass(frozen=True, slots=True)
class CapacityAccountCoverageV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-003"
    OWNER: ClassVar[str] = "PLAN-M05"

    account_id: OpaqueIdV1
    resource_ids: tuple[OpaqueIdV1, ...]
    eligibility: Literal["eligible", "excluded"]
    coverage: Literal["covered", "missing", "partial", "excluded"]
    reason_codes: tuple[str, ...]
    health: CapacityHealthViewV1 | None
    windows: tuple[QuotaWindowViewV1, ...]
    input_observation_ids: tuple[OpaqueIdV1, ...]


@dataclass(frozen=True, slots=True)
class CapacityNumericAggregateV1(TechnicalValueV1):
    """Reserved for explicit additive evidence; independent pools never use it."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-003"
    OWNER: ClassVar[str] = "PLAN-M05"

    metric: Literal["used", "remaining", "limit"]
    quantity: ExactQuantityV1
    interval_start: datetime
    interval_end: datetime
    aggregation_group_id: OpaqueIdV1
    relationship_evidence_id: OpaqueIdV1
    input_observation_ids: tuple[OpaqueIdV1, ...]
    precision: PrecisionV1
    confidence: ConfidenceV1
    value_kind: Literal["derived"] = "derived"

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            self.quantity.unit in {"ratio", "percent"}
            or self.interval_start >= self.interval_end
        ):
            raise InvalidCapacityContractV1("capacity_aggregation_incompatible")


@dataclass(frozen=True, slots=True)
class CapacityAggregateWindowGroupV1(TechnicalValueV1):
    """Inventory group, not proof that periods or resource pools can be summed."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-003"
    OWNER: ClassVar[str] = "PLAN-M05"

    provider_key: str
    native_window_key: str
    semantic_role: str | None
    unit: str | None
    resource_ids: tuple[OpaqueIdV1, ...]
    account_ids: tuple[OpaqueIdV1, ...]
    input_observation_ids: tuple[OpaqueIdV1, ...]
    relationship_state: Literal["unknown"]
    reason_codes: tuple[str, ...]
    numeric_values: tuple[CapacityNumericAggregateV1, ...] = ()


@dataclass(frozen=True, slots=True)
class CapacityAggregateViewV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-003"
    OWNER: ClassVar[str] = "PLAN-M05"

    scope_kind: RegistryScopeKindV1
    scope_id: OpaqueIdV1 | None
    registry_revision: int
    generated_at: datetime
    completeness: CompletenessV1
    availability: Literal["available", "unavailable"]
    reason_codes: tuple[str, ...]
    eligible_account_ids: tuple[OpaqueIdV1, ...]
    covered_account_ids: tuple[OpaqueIdV1, ...]
    missing_accounts: tuple[CapacityAccountCoverageV1, ...]
    excluded_accounts: tuple[CapacityAccountCoverageV1, ...]
    accounts: tuple[CapacityAccountCoverageV1, ...]
    window_groups: tuple[CapacityAggregateWindowGroupV1, ...]
    health_counts: tuple[tuple[CapacityHealthStateV1, int], ...]
    freshness_counts: tuple[tuple[str, int], ...]
    worst_health: CapacityHealthStateV1
    input_observation_ids: tuple[OpaqueIdV1, ...]
    input_set_digest: str
    policy_id: str
    policy_version: str

    @property
    def registered_account_count(self) -> int:
        return len(self.accounts)

    @property
    def eligible_account_count(self) -> int:
        return len(self.eligible_account_ids)

    @property
    def covered_account_count(self) -> int:
        return len(self.covered_account_ids)

    @property
    def excluded_account_count(self) -> int:
        return len(self.excluded_accounts)

    @property
    def missing_account_count(self) -> int:
        return len(self.missing_accounts)

    @property
    def observed_capacity_count(self) -> int:
        return sum(
            bool(item.windows)
            for item in self.accounts
            if item.eligibility == "eligible"
        )


@dataclass(frozen=True, slots=True)
class CapacityForecastPolicyV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-007"
    OWNER: ClassVar[str] = "PLAN-M05"

    method_id: str = "bounded-secant-v1"
    method_version: str = "1.0.0"
    minimum_samples: int = 3
    minimum_span_seconds: int = 900
    maximum_gap_seconds: int = 900
    maximum_samples: int = 200
    maximum_horizon_seconds: int = 604800

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            self.method_id != "bounded-secant-v1"
            or self.method_version != "1.0.0"
            or not 3 <= self.minimum_samples <= self.maximum_samples <= 200
            or not 1 <= self.minimum_span_seconds <= self.maximum_horizon_seconds
            or not 1 <= self.maximum_gap_seconds <= self.maximum_horizon_seconds
            or self.maximum_horizon_seconds > 604800
        ):
            raise InvalidCapacityContractV1("capacity_forecast_policy_invalid")


@dataclass(frozen=True, slots=True)
class CapacityForecastSampleV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-007"
    OWNER: ClassVar[str] = "PLAN-M05"

    observation_id: OpaqueIdV1
    window_definition_id: OpaqueIdV1
    definition_version: int
    subject: CapacitySubjectV1
    window_key: str
    metric: CapacityHistoryMetricV1
    observed_at: datetime
    consumed: ExactMetricFieldV1
    remaining: ExactMetricFieldV1
    source_compatibility_id: str
    reset_segment_id: OpaqueIdV1 | None
    reset_at: datetime | None
    freshness_deadline: datetime | None
    lower_consumed_bound: ExactQuantityV1 | None
    upper_consumed_bound: ExactQuantityV1 | None
    lower_remaining_bound: ExactQuantityV1 | None
    upper_remaining_bound: ExactQuantityV1 | None


@dataclass(frozen=True, slots=True)
class CapacityForecastQueryV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-007"
    OWNER: ClassVar[str] = "PLAN-M05"

    account_id: OpaqueIdV1
    resource_id: OpaqueIdV1 | None
    window_id: OpaqueIdV1 | None
    as_of: datetime
    limit: int = 50
    after_key: str | None = None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if type(self.limit) is not int or not 1 <= self.limit <= 200:
            raise InvalidCapacityContractV1("capacity_forecast_limit_invalid")
        if self.after_key is not None and _CURSOR_KEY.fullmatch(self.after_key) is None:
            raise InvalidCapacityContractV1("capacity_forecast_cursor_invalid")


@dataclass(frozen=True, slots=True)
class CapacityBurnRateV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-007"
    OWNER: ClassVar[str] = "PLAN-M05"

    estimate: ExactQuantityV1
    lower_bound: ExactQuantityV1
    upper_bound: ExactQuantityV1
    sample_count: int
    observed_span_seconds: CanonicalDecimalV1
    input_observation_ids: tuple[OpaqueIdV1, ...]
    time_basis: Literal["second"] = "second"


@dataclass(frozen=True, slots=True)
class CapacityForecastV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-007"
    OWNER: ClassVar[str] = "PLAN-M05"

    forecast_id: OpaqueIdV1
    generation: int
    subject: CapacitySubjectV1
    window_id: OpaqueIdV1
    window_definition_id: OpaqueIdV1
    metric: CapacityHistoryMetricV1
    state: Literal[
        "available", "insufficient_input", "not_applicable", "stale", "conflicted"
    ]
    burn_rate: CapacityBurnRateV1 | None
    earliest_exhaustion_at: datetime | None
    latest_exhaustion_at: datetime | None
    reset_relation: Literal["before", "after", "unknown"]
    confidence: ConfidenceV1
    precision: PrecisionV1
    uncertainty_codes: tuple[str, ...]
    reason_codes: tuple[str, ...]
    input_observation_ids: tuple[OpaqueIdV1, ...]
    input_set_digest: str
    method_id: str
    method_version: str
    generated_at: datetime
    valid_until: datetime | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if self.state == "available":
            if (
                self.burn_rate is None
                or self.earliest_exhaustion_at is None
                or self.latest_exhaustion_at is None
            ):
                raise InvalidCapacityContractV1("capacity_forecast_value_required")
            if self.earliest_exhaustion_at > self.latest_exhaustion_at:
                raise InvalidCapacityContractV1("capacity_forecast_interval_invalid")
        elif (
            self.burn_rate is not None
            or self.earliest_exhaustion_at is not None
            or self.latest_exhaustion_at is not None
        ):
            raise InvalidCapacityContractV1("capacity_forecast_no_value_required")


@dataclass(frozen=True, slots=True)
class CurrentCapacityForecastV1(TechnicalValueV1):
    """A durable M05 forecast, distinct from the query-derived explanation."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-007"
    OWNER: ClassVar[str] = "PLAN-M05"

    forecast: CapacityForecastV1
    source_window_projection_id: OpaqueIdV1
    source_window_generation: int
    source_reset_at: datetime | None
    source_observed_at: datetime | None
    recorded_at: datetime
    freshness_deadline: datetime | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.forecast.generation) is not int
            or self.forecast.generation < 1
            or type(self.source_window_generation) is not int
            or self.source_window_generation < 1
            or self.forecast.window_id != self.source_window_projection_id
        ):
            raise InvalidCapacityContractV1("capacity_current_forecast_invalid")


@dataclass(frozen=True, slots=True)
class ForecastAlertConditionV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-008"
    OWNER: ClassVar[str] = "PLAN-M05"

    resource_id: OpaqueIdV1
    account_id: OpaqueIdV1
    window_id: OpaqueIdV1
    generation: int
    state: Literal[
        "available", "insufficient_input", "not_applicable", "stale", "conflicted"
    ]
    exhaustion_at: datetime | None
    earliest_exhaustion_at: datetime | None
    latest_exhaustion_at: datetime | None
    reset_at: datetime | None
    before_reset: bool | None
    confidence: ConfidenceV1
    precision: PrecisionV1
    observation_ids: tuple[OpaqueIdV1, ...]
    reason_code: str
    observed_at: datetime | None
    recorded_at: datetime
    freshness_deadline: datetime | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if type(self.generation) is not int or self.generation < 1:
            raise InvalidCapacityContractV1(
                "capacity_forecast_condition_generation_invalid"
            )
        if self.state != "available" and (
            self.exhaustion_at is not None
            or self.earliest_exhaustion_at is not None
            or self.latest_exhaustion_at is not None
            or self.before_reset is not None
        ):
            raise InvalidCapacityContractV1(
                "capacity_forecast_condition_no_value_required"
            )
        if self.state == "available" and (
            self.exhaustion_at is None
            or self.earliest_exhaustion_at is None
            or self.latest_exhaustion_at is None
            or self.exhaustion_at != self.latest_exhaustion_at
        ):
            raise InvalidCapacityContractV1(
                "capacity_forecast_condition_bounds_invalid"
            )


CapacityAvailabilityStateV1 = Literal[
    "available",
    "unavailable",
    "blocked",
    "reauthentication_required",
    "unknown",
    "unsupported",
    "stale",
    "withheld_or_denied",
]


@dataclass(frozen=True, slots=True)
class CapacityAvailabilityAlertConditionV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-009"
    OWNER: ClassVar[str] = "PLAN-M05"

    resource_id: OpaqueIdV1
    account_id: OpaqueIdV1
    generation: int
    state: CapacityAvailabilityStateV1
    observation_ids: tuple[OpaqueIdV1, ...]
    evaluated_at: datetime
    reason_code: str
    capability_id: str
    signal_kind: Literal["authentication", "collector", "capability"]
    source_subject_id: OpaqueIdV1
    source_record_id: OpaqueIdV1
    source_generation: int
    source_contract_id: str
    observed_at: datetime | None
    recorded_at: datetime
    freshness_deadline: datetime | None
    recovery_of_generation: int | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.generation) is not int
            or self.generation < 1
            or type(self.source_generation) is not int
            or self.source_generation < 1
            or not _token(self.reason_code)
            or not _token(self.capability_id)
            or not _token(self.source_contract_id)
            or self.recovery_of_generation is not None
            and (
                self.state != "available"
                or self.recovery_of_generation >= self.generation
            )
        ):
            raise InvalidCapacityContractV1("capacity_availability_condition_invalid")


@dataclass(frozen=True, slots=True)
class CapacityAvailabilityQueryV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-009"
    OWNER: ClassVar[str] = "PLAN-M05"

    account_id: OpaqueIdV1
    resource_id: OpaqueIdV1 | None
    capability_id: str | None
    signal_kind: Literal["authentication", "collector", "capability"] | None
    as_of: datetime
    limit: int = 50
    after_key: str | None = None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.limit) is not int
            or not 1 <= self.limit <= 200
            or self.capability_id is not None
            and not _token(self.capability_id)
            or self.after_key is not None
            and _CURSOR_KEY.fullmatch(self.after_key) is None
        ):
            raise InvalidCapacityContractV1("capacity_availability_query_invalid")


@dataclass(frozen=True, slots=True)
class CapacityForecastChangedV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-008"
    OWNER: ClassVar[str] = "PLAN-M05"

    window_id: OpaqueIdV1
    previous_state: str | None
    current_state: str
    transition: Literal["active", "invalidated", "recovered", "not_evaluable"]
    generation: int
    source_generation: int
    input_set_digest: str
    reason_code: str
    latest_observation_id: OpaqueIdV1 | None
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class CapacityAvailabilityChangedV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-009"
    OWNER: ClassVar[str] = "PLAN-M05"

    stream_id: OpaqueIdV1
    previous_state: str | None
    current_state: CapacityAvailabilityStateV1
    transition: Literal["active", "recovered", "not_evaluable"]
    generation: int
    source_generation: int
    input_set_digest: str
    reason_code: str
    latest_observation_id: OpaqueIdV1 | None
    occurred_at: datetime


class ListCurrentCapacityForecastsV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-007"
    OWNER: ClassVar[str] = "PLAN-M05"

    def __call__(
        self, query: CapacityForecastQueryV1
    ) -> QueryPageV1[CurrentCapacityForecastV1]: ...


class ListForecastAlertConditionsV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-008"
    OWNER: ClassVar[str] = "PLAN-M05"

    def __call__(
        self, query: CapacityForecastQueryV1
    ) -> QueryPageV1[ForecastAlertConditionV1]: ...


class ListCapacityAvailabilityConditionsV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-009"
    OWNER: ClassVar[str] = "PLAN-M05"

    def __call__(
        self, query: CapacityAvailabilityQueryV1
    ) -> QueryPageV1[CapacityAvailabilityAlertConditionV1]: ...


CapacityProjectionEventPayloadV1 = (
    CapacityCommittedNoticeV1
    | CapacityForecastChangedV1
    | CapacityAvailabilityChangedV1
)


class ReadCapacityProjectionEventsV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-008"
    OWNER: ClassVar[str] = "PLAN-M05"

    def __call__(
        self,
        consumer_key: str,
        after_cursor: str | None,
        as_of: datetime,
        limit: int = 200,
    ) -> DurableEventBatchV1[CapacityProjectionEventPayloadV1]: ...


class AcknowledgeCapacityProjectionEventV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-008"
    OWNER: ClassVar[str] = "PLAN-M05"

    def __call__(
        self,
        consumer_key: str,
        event_id: OpaqueIdV1,
        payload_digest: str,
        receipt_id: OpaqueIdV1,
        as_of: datetime,
    ) -> None: ...

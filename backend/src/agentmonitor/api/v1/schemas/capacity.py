"""Safe exact wire models for M05 capacity queries."""

from datetime import datetime
from typing import Literal

from agentmonitor.api.v1.schemas.registry import AvailabilityV1, PageMetaV1
from pydantic import BaseModel, ConfigDict


class _ClosedV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExactQuantityWireV1(_ClosedV1):
    coefficient: str
    scale: int
    unit: str


class ExactMetricFieldWireV1(_ClosedV1):
    availability: Literal[
        "available",
        "missing",
        "null",
        "unknown",
        "unsupported",
        "unavailable",
        "not_applicable",
        "withheld_or_denied",
        "stale",
        "unresolved",
    ]
    value: ExactQuantityWireV1 | None
    precision: Literal["exact", "rounded", "range", "estimated", "unknown"]
    confidence: Literal["confirmed", "high", "medium", "low", "unknown"]
    value_kind: Literal[
        "authoritative", "provider_reported", "derived", "heuristic", "unknown"
    ]
    reason_code: str | None


class CapacitySubjectWireV1(_ClosedV1):
    provider_key: str
    installation_id: str
    account_id: str
    resource_id: str


class CapacityObservationProvenanceWireV1(_ClosedV1):
    capability_id: str
    capability_schema_version: str
    adapter_id: str
    adapter_version: str
    provider_protocol_version: str
    source_id: str
    source_class: Literal[
        "documented_api",
        "supported_cli",
        "approved_local_metadata",
        "experimental_private_or_browser",
    ]
    mechanism_version: str
    parser_version: str | None
    provider_version: str | None
    freshness_deadline: datetime | None
    freshness_policy_id: str
    precision: Literal["exact", "rounded", "range", "estimated", "unknown"]
    confidence: Literal["confirmed", "high", "medium", "low", "unknown"]
    confidence_reason_code: str
    is_experimental: bool
    decision_reference: str


class QuotaAllowanceViewV1(_ClosedV1):
    remaining_percentage: ExactMetricFieldWireV1
    calculation: Literal["remaining_ratio_times_100", "100_minus_used_percent"]
    input_observation_id: str


class QuotaWindowViewV1(_ClosedV1):
    window_id: str
    subject: CapacitySubjectWireV1
    window_key: str
    safe_label: str | None
    allowance: QuotaAllowanceViewV1 | None = None
    used: ExactMetricFieldWireV1
    remaining: ExactMetricFieldWireV1
    limit: ExactMetricFieldWireV1
    remaining_ratio: ExactMetricFieldWireV1
    provenance: CapacityObservationProvenanceWireV1 | None = None
    freshness: Literal[
        "fresh", "stale", "freshness_unknown", "conflicted", "no_observation"
    ]
    current_observation_id: str
    collection_run_id: str
    observed_at: datetime | None
    collected_at: datetime
    stored_at: datetime


class CapacityHealthViewV1(_ClosedV1):
    state: Literal[
        "available",
        "constrained",
        "critical",
        "exhausted",
        "reauthentication_required",
        "unknown",
    ]
    completeness: Literal["complete", "partial", "unknown"]
    freshness: Literal["fresh", "stale", "freshness_unknown", "conflicted"]
    constraining_window_id: str | None
    policy_id: str
    policy_version: str
    explanation_codes: tuple[str, ...]


class AccountCapacityItemV1(_ClosedV1):
    subject: CapacitySubjectWireV1
    windows: tuple[QuotaWindowViewV1, ...]
    health: CapacityHealthViewV1 | None


class AccountCapacityViewV1(_ClosedV1):
    account_id: str
    items: tuple[AccountCapacityItemV1, ...]
    availability: AvailabilityV1


class QuotaWindowPageV1(_ClosedV1):
    account_id: str
    items: tuple[QuotaWindowViewV1, ...]
    page: PageMetaV1
    availability: AvailabilityV1


class CapacityHistoryPointV1(_ClosedV1):
    observation_id: str
    window_id: str
    window_definition_id: str
    subject: CapacitySubjectWireV1
    window_key: str
    safe_label: str | None
    semantic_role: str
    native_unit: str | None
    definition_version: int
    metric: Literal["used", "remaining", "limit", "remaining_ratio"]
    series_kind: Literal["raw_provider", "poll_snapshot", "derived"]
    value: ExactMetricFieldWireV1
    provenance: CapacityObservationProvenanceWireV1
    freshness: Literal["fresh", "stale", "freshness_unknown"]
    completeness: Literal["complete", "partial", "unknown"]
    collection_run_id: str
    derivation_id: str | None
    observed_at: datetime
    interval_start: datetime | None
    interval_end: datetime | None
    reset_at: datetime | None
    reset_precision: Literal["exact", "rounded", "range", "estimated", "unknown"]
    collected_at: datetime
    stored_at: datetime


class CapacityHistoryPageV1(_ClosedV1):
    subject_id: str
    metric: Literal["used", "remaining", "limit", "remaining_ratio"]
    series_kind: Literal["raw_provider", "poll_snapshot", "derived"]
    items: tuple[CapacityHistoryPointV1, ...]
    page: PageMetaV1
    availability: AvailabilityV1

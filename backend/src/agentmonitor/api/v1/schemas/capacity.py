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


class CapacityCoverageWireV1(_ClosedV1):
    account_id: str
    resource_ids: tuple[str, ...]
    eligibility: Literal["eligible", "excluded"]
    coverage: Literal["covered", "missing", "partial", "excluded"]
    reason_codes: tuple[str, ...]
    health: CapacityHealthViewV1 | None
    windows: tuple[QuotaWindowViewV1, ...]
    input_observation_ids: tuple[str, ...]


class CapacityNumericAggregateWireV1(_ClosedV1):
    metric: Literal["used", "remaining", "limit"]
    quantity: ExactQuantityWireV1
    interval_start: datetime
    interval_end: datetime
    aggregation_group_id: str
    relationship_evidence_id: str
    input_observation_ids: tuple[str, ...]
    precision: Literal["exact", "rounded", "range", "estimated", "unknown"]
    confidence: Literal["confirmed", "high", "medium", "low", "unknown"]
    value_kind: Literal["derived"]


class CapacityWindowGroupWireV1(_ClosedV1):
    provider_key: str
    native_window_key: str
    semantic_role: str | None
    unit: str | None
    resource_ids: tuple[str, ...]
    account_ids: tuple[str, ...]
    input_observation_ids: tuple[str, ...]
    relationship_state: Literal["unknown"]
    reason_codes: tuple[str, ...]
    numeric_values: tuple[CapacityNumericAggregateWireV1, ...]


class CapacityCountWireV1(_ClosedV1):
    state: str
    count: int


class CapacityScopeViewV1(_ClosedV1):
    scope_kind: Literal["global", "organization", "provider", "account"]
    scope_id: str | None
    registry_revision: int
    generated_at: datetime
    completeness: Literal["complete", "partial", "unknown"]
    availability: Literal["available", "unavailable"]
    reason_codes: tuple[str, ...]
    registered_account_count: int
    eligible_account_count: int
    covered_account_count: int
    excluded_account_count: int
    missing_account_count: int
    observed_capacity_count: int
    eligible_account_ids: tuple[str, ...]
    covered_account_ids: tuple[str, ...]
    missing_accounts: tuple[CapacityCoverageWireV1, ...]
    excluded_accounts: tuple[CapacityCoverageWireV1, ...]
    accounts: tuple[CapacityCoverageWireV1, ...]
    window_groups: tuple[CapacityWindowGroupWireV1, ...]
    health_counts: tuple[CapacityCountWireV1, ...]
    freshness_counts: tuple[CapacityCountWireV1, ...]
    worst_health: str
    input_observation_ids: tuple[str, ...]
    input_set_digest: str
    policy_id: str
    policy_version: str


class CanonicalDecimalWireV1(_ClosedV1):
    coefficient: str
    scale: int


class CapacityBurnRateWireV1(_ClosedV1):
    estimate: ExactQuantityWireV1
    lower_bound: ExactQuantityWireV1
    upper_bound: ExactQuantityWireV1
    sample_count: int
    observed_span_seconds: CanonicalDecimalWireV1
    input_observation_ids: tuple[str, ...]
    time_basis: Literal["second"]


class CapacityForecastWireV1(_ClosedV1):
    forecast_id: str
    generation: int
    subject: CapacitySubjectWireV1
    window_id: str
    window_definition_id: str
    metric: Literal["used", "remaining", "limit", "remaining_ratio"]
    state: Literal[
        "available", "insufficient_input", "not_applicable", "stale", "conflicted"
    ]
    burn_rate: CapacityBurnRateWireV1 | None
    earliest_exhaustion_at: datetime | None
    latest_exhaustion_at: datetime | None
    reset_relation: Literal["before", "after", "unknown"]
    confidence: Literal["confirmed", "high", "medium", "low", "unknown"]
    precision: Literal["exact", "rounded", "range", "estimated", "unknown"]
    uncertainty_codes: tuple[str, ...]
    reason_codes: tuple[str, ...]
    input_observation_ids: tuple[str, ...]
    input_set_digest: str
    method_id: str
    method_version: str
    generated_at: datetime
    valid_until: datetime | None


class CapacityForecastPageV1(_ClosedV1):
    account_id: str
    items: tuple[CapacityForecastWireV1, ...]
    page: PageMetaV1
    availability: AvailabilityV1

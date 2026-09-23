"""Safe metadata-only wire models for M06 runtime queries."""

from datetime import datetime
from typing import Literal

from agentmonitor.api.v1.schemas.registry import AvailabilityV1, PageMetaV1
from pydantic import BaseModel, ConfigDict


class _ClosedV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FieldAvailabilityWireV1(_ClosedV1):
    state: Literal[
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


class FallbackAttemptWireV1(_ClosedV1):
    source_id: str
    failure_code: str


class ObservationProvenanceWireV1(_ClosedV1):
    provider_key: str
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
    provider_version_availability: FieldAvailabilityWireV1
    observed_at: datetime | None
    observed_at_availability: FieldAvailabilityWireV1
    collected_at: datetime
    freshness_deadline: datetime | None
    freshness_availability: FieldAvailabilityWireV1
    freshness_policy_id: str
    precision: Literal["exact", "rounded", "range", "estimated", "unknown"]
    confidence: Literal["confirmed", "high", "medium", "low", "unknown"]
    confidence_reason_code: str
    value_kind: Literal[
        "authoritative", "provider_reported", "derived", "heuristic", "unknown"
    ]
    is_experimental: bool
    fallback_lineage: tuple[FallbackAttemptWireV1, ...]
    warnings: tuple[str, ...]
    operation_id: str
    correlation_id: str
    decision_reference: str
    derivation_method: str | None
    input_observation_ids: tuple[str, ...]


class ProcessIdentityWireV1(_ClosedV1):
    platform_source: str
    platform_scope_id: str
    pid: int
    start_time_ticks: int


class ProcessLabelFieldWireV1(_ClosedV1):
    state: Literal[
        "present",
        "not_requested",
        "not_found",
        "unsupported",
        "permission_denied",
        "process_exited",
        "identity_conflict",
        "unverified_source",
        "deadline_exceeded",
        "changed_during_read",
        "unsafe_layout",
        "redacted_by_policy",
    ]
    value: str | None
    reason_code: str | None


class ProcessMetricFieldWireV1(_ClosedV1):
    state: Literal[
        "present",
        "not_requested",
        "not_found",
        "unsupported",
        "permission_denied",
        "process_exited",
        "identity_conflict",
        "unverified_source",
        "deadline_exceeded",
        "changed_during_read",
        "unsafe_layout",
        "redacted_by_policy",
    ]
    value: int | None
    unit: str | None
    reason_code: str | None


class ProcessCodeFieldWireV1(_ClosedV1):
    state: Literal[
        "present",
        "not_requested",
        "not_found",
        "unsupported",
        "permission_denied",
        "process_exited",
        "identity_conflict",
        "unverified_source",
        "deadline_exceeded",
        "changed_during_read",
        "unsafe_layout",
        "redacted_by_policy",
    ]
    value: str | None
    reason_code: str | None


class AgentProcessViewV1(_ClosedV1):
    process_id: str
    identity: ProcessIdentityWireV1
    provider_key: str | None
    installation_id: str | None
    executable_label: ProcessLabelFieldWireV1
    provenance: ObservationProvenanceWireV1
    first_observed_at: datetime
    last_observed_at: datetime
    presence: Literal["running", "exited", "unknown"]
    current_snapshot_id: str
    revision: int


class AgentProcessPageV1(_ClosedV1):
    items: tuple[AgentProcessViewV1, ...]
    page: PageMetaV1
    availability: AvailabilityV1


class AgentProcessMetricViewV1(AgentProcessViewV1):
    parent_pid: ProcessMetricFieldWireV1
    user_cpu_ticks: ProcessMetricFieldWireV1
    system_cpu_ticks: ProcessMetricFieldWireV1
    resident_pages: ProcessMetricFieldWireV1
    thread_count: ProcessMetricFieldWireV1
    kernel_state: ProcessCodeFieldWireV1
    clock_ticks_per_second: int
    page_size_bytes: int


class AgentProcessMetricPageV1(_ClosedV1):
    items: tuple[AgentProcessMetricViewV1, ...]
    page: PageMetaV1
    availability: AvailabilityV1


class SessionIdentityWireV1(_ClosedV1):
    provider_key: str
    installation_id: str
    identity_kind: str
    identity_value: str


class AgentSessionViewV1(_ClosedV1):
    session_id: str
    identity: SessionIdentityWireV1
    provenance: ObservationProvenanceWireV1
    first_observed_at: datetime
    last_observed_at: datetime
    correlation_state: Literal[
        "automatic_matched",
        "confirmation_required",
        "owner_confirmed",
        "unresolved",
        "conflict",
        "invalidated",
        "unsupported",
    ]
    account_id: str | None
    revision: int


class AgentSessionPageV1(_ClosedV1):
    items: tuple[AgentSessionViewV1, ...]
    page: PageMetaV1
    availability: AvailabilityV1

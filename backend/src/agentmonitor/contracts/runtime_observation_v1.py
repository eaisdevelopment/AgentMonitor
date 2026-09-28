"""M06 runtime-observation V1 contracts.

The contract contains only bounded operational metadata.  Process command lines,
environments, terminal data, provider payloads, and process-control operations are
deliberately absent.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import ClassVar, Literal, Protocol, runtime_checkable

from agentmonitor.contracts.collection_control_v1 import (
    CollectionCommitReceiptV1,
    CollectionCommitStatusV1,
    CollectionOutcomeCommitV1,
)
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_v1 import (
    OpaqueIdV1,
    QueryAvailabilityV1,
    TechnicalValueV1,
)

ProviderKeyV1 = Literal["claude", "codex", "ollama"]
RuntimeFieldStateV1 = Literal[
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
PlatformInspectionStateV1 = Literal[
    "success",
    "partial",
    "unsupported",
    "permission_denied",
    "source_unavailable",
    "unverified_platform_version",
    "deadline_exceeded",
    "invalid_request",
    "invalid_platform_data",
    "internal_adapter_error",
]
CorrelationEvidenceClassV1 = Literal["strong", "corroborated", "weak"]
SessionProcessRelationshipKindV1 = Literal[
    "primary", "worker", "wrapper", "observer", "unknown"
]
RuntimeCertaintyV1 = Literal["definitive", "inferred", "unknown"]
CorrelationDecisionStateV1 = Literal[
    "unresolved",
    "automatic_matched",
    "confirmation_required",
    "conflict",
    "unsupported",
    "owner_confirmed",
    "invalidated",
]
TopologyEvidenceStateV1 = Literal["eligible", "excluded", "unknown"]
PresenceStateV1 = Literal["running", "exited", "unknown"]
MetricSemanticsV1 = Literal["gauge", "interval", "cumulative"]
MetricOverlapV1 = Literal["disjoint", "inclusive", "unknown", "not_applicable"]
NormalizedRuntimeStateV1 = Literal[
    "working",
    "waiting_for_input",
    "waiting_for_permission",
    "idle",
    "quota_or_rate_limited",
    "reauthentication_required",
    "provider_or_network_error",
    "possibly_stuck",
    "exited_successfully",
    "crashed",
    "unknown",
]
RuntimeStateCertaintyV1 = Literal["definitive", "inferred", "unknown"]
StallEvaluationStateV1 = Literal["not_evaluable", "not_stalled", "possible_stall"]
StallPolicyScopeV1 = Literal["global", "organization", "provider", "account"]
_NORMALIZED_RUNTIME_STATES = frozenset(
    {
        "working",
        "waiting_for_input",
        "waiting_for_permission",
        "idle",
        "quota_or_rate_limited",
        "reauthentication_required",
        "provider_or_network_error",
        "possibly_stuck",
        "exited_successfully",
        "crashed",
        "unknown",
    }
)
_RUNTIME_STATE_CERTAINTIES = frozenset({"definitive", "inferred", "unknown"})

_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:@/-]{0,127}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_PROCESS_FIELDS = frozenset(
    {
        "kernel_state",
        "parent_pid",
        "resident_pages",
        "system_cpu_ticks",
        "thread_count",
        "user_cpu_ticks",
    }
)


class InvalidRuntimeObservationV1(ValueError):
    """A runtime contract value violates a stable V1 invariant."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _token(value: object, maximum: int = 128) -> bool:
    return (
        type(value) is str
        and 1 <= len(value) <= maximum
        and value == value.strip()
        and value.isprintable()
        and _TOKEN.fullmatch(value) is not None
    )


def _utc(value: datetime) -> bool:
    return isinstance(value, datetime) and value.utcoffset() == timedelta(0)


@dataclass(frozen=True, slots=True)
class ProcessIdentityV1(TechnicalValueV1):
    """Portable identity that is safe against PID reuse."""

    CONTRACT_ID: ClassVar[str] = "CTR-RUN-001"
    OWNER: ClassVar[str] = "PLAN-M06"

    platform_source: str
    platform_scope_id: str
    pid: int
    start_time_ticks: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not _token(self.platform_source)
            or not _token(self.platform_scope_id)
            or type(self.pid) is not int
            or self.pid <= 0
            or type(self.start_time_ticks) is not int
            or self.start_time_ticks <= 0
        ):
            raise InvalidRuntimeObservationV1("runtime_process_identity_incomplete")


@dataclass(frozen=True, slots=True)
class SessionIdentityV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-RUN-002"
    OWNER: ClassVar[str] = "PLAN-M06"

    provider_key: str
    installation_id: str
    identity_kind: str
    identity_value: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not all(
            _token(value)
            for value in (
                self.provider_key,
                self.installation_id,
                self.identity_kind,
                self.identity_value,
            )
        ):
            raise InvalidRuntimeObservationV1("runtime_session_identity_incomplete")


@dataclass(frozen=True, slots=True)
class ProcessMetricFieldV1(TechnicalValueV1):
    """One optional integral Linux fact with explicit source semantics."""

    CONTRACT_ID: ClassVar[str] = "CTR-RUN-006"
    OWNER: ClassVar[str] = "PLAN-M06"

    state: RuntimeFieldStateV1
    value: int | None
    unit: str | None
    reason_code: str | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        present = self.state == "present"
        if present != (self.value is not None and self.unit is not None):
            raise InvalidRuntimeObservationV1("runtime_process_field_pair_invalid")
        if present and (
            self.reason_code is not None or self.value is None or self.value < 0
        ):
            raise InvalidRuntimeObservationV1("runtime_process_field_value_invalid")
        if not present and (
            self.value is not None
            or self.unit is not None
            or not _token(self.reason_code)
        ):
            raise InvalidRuntimeObservationV1("runtime_process_field_reason_invalid")
        if self.unit is not None and not _token(self.unit):
            raise InvalidRuntimeObservationV1("runtime_process_field_unit_invalid")


@dataclass(frozen=True, slots=True)
class ProcessCodeFieldV1(TechnicalValueV1):
    """One bounded code field with explicit missing-state semantics."""

    CONTRACT_ID: ClassVar[str] = "CTR-RUN-006"
    OWNER: ClassVar[str] = "PLAN-M06"

    state: RuntimeFieldStateV1
    value: str | None
    reason_code: str | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        present = self.state == "present"
        if present != (self.value is not None):
            raise InvalidRuntimeObservationV1("runtime_process_code_pair_invalid")
        if present and (
            self.reason_code is not None
            or self.value is None
            or len(self.value) != 1
            or not self.value.isascii()
            or not self.value.isalpha()
        ):
            raise InvalidRuntimeObservationV1("runtime_process_code_value_invalid")
        if not present and not _token(self.reason_code):
            raise InvalidRuntimeObservationV1("runtime_process_code_reason_invalid")


@dataclass(frozen=True, slots=True)
class ProcessLabelFieldV1(TechnicalValueV1):
    """One bounded safe label field with explicit missing-state semantics."""

    CONTRACT_ID: ClassVar[str] = "CTR-RUN-006"
    OWNER: ClassVar[str] = "PLAN-M06"

    state: RuntimeFieldStateV1
    value: str | None
    reason_code: str | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        present = self.state == "present"
        if present != (self.value is not None):
            raise InvalidRuntimeObservationV1("runtime_process_label_pair_invalid")
        if present and (
            self.reason_code is not None or self.value is None or not _token(self.value)
        ):
            raise InvalidRuntimeObservationV1("runtime_process_label_value_invalid")
        if not present and not _token(self.reason_code):
            raise InvalidRuntimeObservationV1("runtime_process_label_reason_invalid")


@dataclass(frozen=True, slots=True)
class ProcessSnapshotInputV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-RUN-001"
    OWNER: ClassVar[str] = "PLAN-M06"

    observation_id: str
    identity: ProcessIdentityV1
    provider_key: str | None
    installation_id: str | None
    executable_label: ProcessLabelFieldV1
    parent_pid: ProcessMetricFieldV1
    user_cpu_ticks: ProcessMetricFieldV1
    system_cpu_ticks: ProcessMetricFieldV1
    resident_pages: ProcessMetricFieldV1
    thread_count: ProcessMetricFieldV1
    kernel_state: ProcessCodeFieldV1
    observed_at: datetime
    source_id: str
    source_version: str
    adapter_version: str
    clock_ticks_per_second: int
    page_size_bytes: int
    executable_identity: str | None = None
    presence: PresenceStateV1 = "running"

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not all(
            _token(value)
            for value in (
                self.observation_id,
                self.source_id,
                self.source_version,
                self.adapter_version,
            )
        ):
            raise InvalidRuntimeObservationV1("runtime_process_snapshot_invalid")
        if self.provider_key is not None and not _token(self.provider_key):
            raise InvalidRuntimeObservationV1("runtime_process_snapshot_invalid")
        if self.installation_id is not None and not _token(self.installation_id):
            raise InvalidRuntimeObservationV1("runtime_process_snapshot_invalid")
        if (
            self.executable_identity is not None
            and _SHA256.fullmatch(self.executable_identity) is None
        ):
            raise InvalidRuntimeObservationV1("runtime_executable_identity_invalid")
        if (self.provider_key is None and self.installation_id is not None) or (
            (self.provider_key is not None or self.installation_id is not None)
            and self.executable_identity is None
        ):
            raise InvalidRuntimeObservationV1("runtime_process_attribution_invalid")
        if not _utc(self.observed_at):
            raise InvalidRuntimeObservationV1("runtime_process_timestamp_invalid")
        if (
            type(self.clock_ticks_per_second) is not int
            or self.clock_ticks_per_second <= 0
            or type(self.page_size_bytes) is not int
            or self.page_size_bytes <= 0
        ):
            raise InvalidRuntimeObservationV1("runtime_process_units_invalid")
        if self.kernel_state.state == "present" and (
            self.kernel_state.value is None
            or len(self.kernel_state.value) != 1
            or not self.kernel_state.value.isascii()
            or not self.kernel_state.value.isalpha()
        ):
            raise InvalidRuntimeObservationV1("runtime_process_state_invalid")


@dataclass(frozen=True, slots=True)
class PlatformInspectionRequestV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-RUN-006"
    OWNER: ClassVar[str] = "PLAN-M06"

    operation_id: str
    correlation_id: str
    provider_key: str | None
    installation_id: str | None
    provider_version: str | None
    source_id: str
    selector_id: str
    executable_identity: str
    requested_fields: tuple[str, ...]
    maximum_candidates: int
    maximum_results: int
    deadline_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not all(
            _token(value)
            for value in (
                self.operation_id,
                self.correlation_id,
                self.source_id,
                self.selector_id,
                self.executable_identity,
            )
        ):
            raise InvalidRuntimeObservationV1("runtime_inspection_request_invalid")
        attribution = (
            self.provider_key,
            self.installation_id,
            self.provider_version,
        )
        if not (
            all(value is None for value in attribution)
            or all(_token(value) for value in attribution)
        ):
            raise InvalidRuntimeObservationV1("runtime_inspection_request_invalid")
        if (
            not _utc(self.deadline_at)
            or type(self.maximum_candidates) is not int
            or not 1 <= self.maximum_candidates <= 16_384
            or type(self.maximum_results) is not int
            or not 1 <= self.maximum_results <= min(self.maximum_candidates, 512)
            or self.requested_fields != tuple(sorted(set(self.requested_fields)))
            or not set(self.requested_fields) <= _PROCESS_FIELDS
        ):
            raise InvalidRuntimeObservationV1("runtime_inspection_request_invalid")


@dataclass(frozen=True, slots=True)
class PlatformInspectionOutcomeV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-RUN-006"
    OWNER: ClassVar[str] = "PLAN-M06"

    state: PlatformInspectionStateV1
    processes: tuple[ProcessSnapshotInputV1, ...]
    observed_at: datetime
    source_id: str
    source_version: str
    candidate_count: int
    truncated: bool
    omission_codes: tuple[str, ...] = ()
    error_code: str | None = None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not _utc(self.observed_at)
            or not _token(self.source_id)
            or not _token(self.source_version)
            or type(self.candidate_count) is not int
            or self.candidate_count < len(self.processes)
            or type(self.truncated) is not bool
            or self.omission_codes != tuple(sorted(set(self.omission_codes)))
            or not all(_token(code) for code in self.omission_codes)
        ):
            raise InvalidRuntimeObservationV1("runtime_inspection_outcome_invalid")
        succeeded = self.state in {"success", "partial"}
        if succeeded == (self.error_code is not None):
            raise InvalidRuntimeObservationV1("runtime_inspection_outcome_invalid")
        if self.state == "success" and (self.omission_codes or self.truncated):
            raise InvalidRuntimeObservationV1("runtime_inspection_success_partial")
        if self.state == "partial" and not (self.omission_codes or self.truncated):
            raise InvalidRuntimeObservationV1(
                "runtime_inspection_partial_reason_required"
            )
        if self.error_code is not None and not _token(self.error_code):
            raise InvalidRuntimeObservationV1("runtime_inspection_error_invalid")


@dataclass(frozen=True, slots=True)
class LocalSessionObservationInputV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-RUN-002"
    OWNER: ClassVar[str] = "PLAN-M06"

    observation_id: str
    session_identity: SessionIdentityV1
    observed_at: datetime
    source_id: str
    source_version: str
    parser_version: str
    provider_version: str
    activity_state: RuntimeFieldStateV1
    activity_code: str | None
    activity_reason_code: str | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not _token(self.observation_id)
            or not _utc(self.observed_at)
            or not all(
                _token(value)
                for value in (
                    self.source_id,
                    self.source_version,
                    self.parser_version,
                    self.provider_version,
                )
            )
        ):
            raise InvalidRuntimeObservationV1("runtime_session_observation_invalid")
        activity_present = self.activity_state == "present"
        if activity_present != (self.activity_code is not None):
            raise InvalidRuntimeObservationV1("runtime_session_activity_pair_invalid")
        if activity_present and self.activity_reason_code is not None:
            raise InvalidRuntimeObservationV1("runtime_session_activity_pair_invalid")
        if not activity_present and not _token(self.activity_reason_code):
            raise InvalidRuntimeObservationV1("runtime_session_activity_pair_invalid")
        if self.activity_code is not None and not _token(self.activity_code):
            raise InvalidRuntimeObservationV1("runtime_session_activity_pair_invalid")


@dataclass(frozen=True, slots=True)
class SessionProcessLinkInputV1(TechnicalValueV1):
    """Exact session/process join supplied by an approved provider source."""

    CONTRACT_ID: ClassVar[str] = "CTR-RUN-002"
    OWNER: ClassVar[str] = "PLAN-M06"

    link_id: str
    session_identity: SessionIdentityV1
    process_identity: ProcessIdentityV1
    relationship_kind: SessionProcessRelationshipKindV1
    evidence_class: CorrelationEvidenceClassV1
    certainty: RuntimeCertaintyV1
    source_id: str
    source_version: str
    observed_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not all(
                _token(value)
                for value in (self.link_id, self.source_id, self.source_version)
            )
            or not _utc(self.observed_at)
            or (self.evidence_class == "strong") != (self.certainty == "definitive")
        ):
            raise InvalidRuntimeObservationV1("runtime_session_process_link_invalid")


@dataclass(frozen=True, slots=True)
class RuntimeMetricObservationInputV1(TechnicalValueV1):
    """Exact decimal runtime metric with explicit temporal/overlap semantics."""

    CONTRACT_ID: ClassVar[str] = "CTR-RUN-002"
    OWNER: ClassVar[str] = "PLAN-M06"

    metric_id: str
    session_identity: SessionIdentityV1
    process_identity: ProcessIdentityV1 | None
    metric_kind: str
    coefficient: str
    scale: int
    unit: str
    scope: str
    semantics: MetricSemanticsV1
    overlap_class: MetricOverlapV1
    interval_start: datetime | None
    interval_end: datetime | None
    observed_at: datetime
    source_id: str
    source_version: str
    parser_version: str
    provider_version: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not all(
            _token(value)
            for value in (
                self.metric_id,
                self.metric_kind,
                self.unit,
                self.scope,
                self.source_id,
                self.source_version,
                self.parser_version,
                self.provider_version,
            )
        ):
            raise InvalidRuntimeObservationV1("runtime_metric_invalid")
        if (
            re.fullmatch(r"-?(0|[1-9][0-9]{0,79})", self.coefficient) is None
            or type(self.scale) is not int
            or not 0 <= self.scale <= 18
            or not _utc(self.observed_at)
        ):
            raise InvalidRuntimeObservationV1("runtime_metric_invalid")
        has_interval = self.interval_start is not None and self.interval_end is not None
        if (self.interval_start is None) != (self.interval_end is None):
            raise InvalidRuntimeObservationV1("runtime_metric_interval_invalid")
        if has_interval:
            assert self.interval_start is not None and self.interval_end is not None
            if (
                not _utc(self.interval_start)
                or not _utc(self.interval_end)
                or self.interval_end < self.interval_start
            ):
                raise InvalidRuntimeObservationV1("runtime_metric_interval_invalid")
        if (self.semantics == "gauge") != (not has_interval):
            raise InvalidRuntimeObservationV1("runtime_metric_interval_invalid")
        if (self.semantics == "gauge") != (self.overlap_class == "not_applicable"):
            raise InvalidRuntimeObservationV1("runtime_metric_overlap_invalid")


@dataclass(frozen=True, slots=True)
class CorrelationEvidenceInputV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-RUN-007"
    OWNER: ClassVar[str] = "PLAN-M06"

    evidence_id: str
    session_identity: SessionIdentityV1
    evidence_class: CorrelationEvidenceClassV1
    rule_id: str
    account_id: str | None
    observed_at: datetime
    source_id: str
    source_version: str
    reason_code: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not all(
                _token(value)
                for value in (
                    self.evidence_id,
                    self.rule_id,
                    self.source_id,
                    self.source_version,
                    self.reason_code,
                )
            )
            or (self.account_id is not None and not _token(self.account_id))
            or not _utc(self.observed_at)
            or (self.evidence_class == "strong") != (self.account_id is not None)
        ):
            raise InvalidRuntimeObservationV1("runtime_correlation_evidence_invalid")


@dataclass(frozen=True, slots=True)
class ApprovedStrongCorrelationRuleV1(TechnicalValueV1):
    """Owner-approved rule tuple; an empty catalog is the fail-closed default."""

    CONTRACT_ID: ClassVar[str] = "CTR-RUN-007"
    OWNER: ClassVar[str] = "PLAN-M06"

    rule_id: str
    source_id: str
    source_version: str
    decision_reference: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not all(
            _token(value)
            for value in (
                self.rule_id,
                self.source_id,
                self.source_version,
                self.decision_reference,
            )
        ):
            raise InvalidRuntimeObservationV1("runtime_correlation_policy_invalid")


@dataclass(frozen=True, slots=True)
class SessionCorrelationDecisionV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-RUN-007"
    OWNER: ClassVar[str] = "PLAN-M06"

    session_identity: SessionIdentityV1
    state: CorrelationDecisionStateV1
    account_id: str | None
    evidence_ids: tuple[str, ...]
    reason_code: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            self.evidence_ids != tuple(sorted(set(self.evidence_ids)))
            or not all(_token(value) for value in self.evidence_ids)
            or not _token(self.reason_code)
            or (self.account_id is not None and not _token(self.account_id))
            or (self.state in {"automatic_matched", "owner_confirmed"})
            != (self.account_id is not None)
        ):
            raise InvalidRuntimeObservationV1("runtime_correlation_decision_invalid")


@dataclass(frozen=True, slots=True)
class RuntimeStateEvidenceSummaryV1(TechnicalValueV1):
    """Closed, source-derived state summary; it never carries free-form text."""

    CONTRACT_ID: ClassVar[str] = "CTR-RUN-004"
    OWNER: ClassVar[str] = "PLAN-M06"

    session_id: OpaqueIdV1
    state: NormalizedRuntimeStateV1
    certainty: RuntimeStateCertaintyV1
    reason_code: str
    observed_at: datetime
    freshness_deadline: datetime
    evidence_ids: tuple[OpaqueIdV1, ...]

    def __post_init__(self) -> None:
        if (
            self.state not in _NORMALIZED_RUNTIME_STATES
            or self.certainty not in _RUNTIME_STATE_CERTAINTIES
        ):
            raise InvalidRuntimeObservationV1("runtime_state_evidence_invalid")
        TechnicalValueV1.__post_init__(self)
        unknown_pair = self.state == "unknown" and self.certainty == "unknown"
        if (
            not _token(self.reason_code)
            or not _utc(self.observed_at)
            or not _utc(self.freshness_deadline)
            or self.freshness_deadline < self.observed_at
            or len(self.evidence_ids) != len(set(self.evidence_ids))
            or (self.state == "unknown") != (self.certainty == "unknown")
            or (not unknown_pair and not self.evidence_ids)
            or (self.state == "possibly_stuck" and self.certainty != "inferred")
        ):
            raise InvalidRuntimeObservationV1("runtime_state_evidence_invalid")


@dataclass(frozen=True, slots=True)
class RuntimeStateChangedV1(TechnicalValueV1):
    """Minimum ordered state-transition payload for the M06 session stream."""

    CONTRACT_ID: ClassVar[str] = "CTR-RUN-004"
    OWNER: ClassVar[str] = "PLAN-M06"

    session_id: OpaqueIdV1
    previous_state: NormalizedRuntimeStateV1
    current: RuntimeStateEvidenceSummaryV1
    evaluated_at: datetime
    classifier_version: str
    runtime_revision: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            self.current.session_id != self.session_id
            or self.previous_state == self.current.state
            or not _utc(self.evaluated_at)
            or self.evaluated_at < self.current.observed_at
            or not _token(self.classifier_version)
            or type(self.runtime_revision) is not int
            or self.runtime_revision < 1
        ):
            raise InvalidRuntimeObservationV1("runtime_state_transition_invalid")


@dataclass(frozen=True, slots=True)
class RuntimeStallPolicyViewV1(TechnicalValueV1):
    """Effective fail-closed stall policy; V1 global default is 600 seconds."""

    CONTRACT_ID: ClassVar[str] = "CTR-RUN-005"
    OWNER: ClassVar[str] = "PLAN-M06"

    policy_id: OpaqueIdV1
    policy_version: int
    scope_kind: StallPolicyScopeV1
    scope_id: str
    threshold_seconds: int
    enabled: bool

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.policy_version) is not int
            or self.policy_version < 1
            or not _token(self.scope_id)
            or (self.scope_kind == "global") != (self.scope_id == "global")
            or type(self.threshold_seconds) is not int
            or not 60 <= self.threshold_seconds <= 86_400
            or type(self.enabled) is not bool
        ):
            raise InvalidRuntimeObservationV1("runtime_stall_policy_invalid")


@dataclass(frozen=True, slots=True)
class PossibleStallEvaluationV1(TechnicalValueV1):
    """Pure policy result; only `possible_stall` may carry inferred certainty."""

    CONTRACT_ID: ClassVar[str] = "CTR-RUN-005"
    OWNER: ClassVar[str] = "PLAN-M06"

    session_id: OpaqueIdV1
    evaluation_state: StallEvaluationStateV1
    certainty: RuntimeStateCertaintyV1
    reason_code: str
    evaluated_at: datetime
    effective_since: datetime | None
    elapsed_seconds: int | None
    threshold_seconds: int
    policy_id: OpaqueIdV1
    policy_version: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        possible = self.evaluation_state == "possible_stall"
        if (
            not _token(self.reason_code)
            or not _utc(self.evaluated_at)
            or type(self.threshold_seconds) is not int
            or not 60 <= self.threshold_seconds <= 86_400
            or type(self.policy_version) is not int
            or self.policy_version < 1
            or possible != (self.certainty == "inferred")
            or possible
            != (
                self.effective_since is not None
                and self.elapsed_seconds is not None
                and self.elapsed_seconds >= self.threshold_seconds
            )
            or (
                self.effective_since is not None
                and (
                    not _utc(self.effective_since)
                    or self.effective_since > self.evaluated_at
                )
            )
            or (self.elapsed_seconds is not None and self.elapsed_seconds < 0)
        ):
            raise InvalidRuntimeObservationV1("runtime_stall_evaluation_invalid")


@dataclass(frozen=True, slots=True)
class PossibleStallDetectedV1(TechnicalValueV1):
    """Safe event payload emitted only from an inferred possible-stall result."""

    CONTRACT_ID: ClassVar[str] = "CTR-RUN-005"
    OWNER: ClassVar[str] = "PLAN-M06"

    condition_fingerprint: str
    evaluation: PossibleStallEvaluationV1
    evidence_ids: tuple[OpaqueIdV1, ...]
    runtime_revision: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            _SHA256.fullmatch(self.condition_fingerprint) is None
            or self.evaluation.evaluation_state != "possible_stall"
            or not self.evidence_ids
            or len(self.evidence_ids) != len(set(self.evidence_ids))
            or type(self.runtime_revision) is not int
            or self.runtime_revision < 1
        ):
            raise InvalidRuntimeObservationV1("runtime_stall_event_invalid")


@dataclass(frozen=True, slots=True)
class RuntimeObservationBatchV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-RUN-002"
    OWNER: ClassVar[str] = "PLAN-M06"

    process_snapshots: tuple[ProcessSnapshotInputV1, ...]
    session_observations: tuple[LocalSessionObservationInputV1, ...]
    correlation_evidence: tuple[CorrelationEvidenceInputV1, ...]
    completeness: Literal["complete_scope", "partial_scope"]
    metric_observations: tuple[RuntimeMetricObservationInputV1, ...] = ()
    session_process_links: tuple[SessionProcessLinkInputV1, ...] = ()
    omission_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not (
            self.process_snapshots
            or self.session_observations
            or self.metric_observations
        ):
            raise InvalidRuntimeObservationV1("runtime_observation_batch_empty")
        if (
            self.omission_codes != tuple(sorted(set(self.omission_codes)))
            or not all(_token(code) for code in self.omission_codes)
            or (self.completeness == "partial_scope") != bool(self.omission_codes)
        ):
            raise InvalidRuntimeObservationV1(
                "runtime_observation_batch_partial_invalid"
            )
        session_identities = {
            item.session_identity for item in self.session_observations
        }
        invalid_evidence = any(
            item.session_identity not in session_identities
            for item in self.correlation_evidence
        )
        invalid_metrics = any(
            item.session_identity not in session_identities
            for item in self.metric_observations
        )
        invalid_links = any(
            item.session_identity not in session_identities
            for item in self.session_process_links
        )
        if invalid_evidence or invalid_metrics or invalid_links:
            raise InvalidRuntimeObservationV1(
                "runtime_observation_session_reference_invalid"
            )
        observation_ids = (
            tuple(item.observation_id for item in self.process_snapshots)
            + tuple(item.observation_id for item in self.session_observations)
            + tuple(item.metric_id for item in self.metric_observations)
            + tuple(item.link_id for item in self.session_process_links)
            + tuple(item.evidence_id for item in self.correlation_evidence)
        )
        if len(observation_ids) != len(set(observation_ids)):
            raise InvalidRuntimeObservationV1(
                "runtime_observation_identifier_duplicate"
            )

    def canonical_digest(self) -> str:
        """Hash every closed batch field with stable V1 canonicalization."""
        document = {
            "completeness": self.completeness,
            "omission_codes": list(self.omission_codes),
            "process_snapshots": [
                {
                    "observation_id": item.observation_id,
                    "identity": {
                        "platform_source": item.identity.platform_source,
                        "platform_scope_id": item.identity.platform_scope_id,
                        "pid": item.identity.pid,
                        "start_time_ticks": item.identity.start_time_ticks,
                    },
                    "provider_key": item.provider_key,
                    "installation_id": item.installation_id,
                    "executable_identity": item.executable_identity,
                    "executable_label": [
                        item.executable_label.state,
                        item.executable_label.value,
                        item.executable_label.reason_code,
                    ],
                    "parent_pid": [
                        item.parent_pid.state,
                        item.parent_pid.value,
                        item.parent_pid.unit,
                        item.parent_pid.reason_code,
                    ],
                    "user_cpu_ticks": [
                        item.user_cpu_ticks.state,
                        item.user_cpu_ticks.value,
                        item.user_cpu_ticks.unit,
                        item.user_cpu_ticks.reason_code,
                    ],
                    "system_cpu_ticks": [
                        item.system_cpu_ticks.state,
                        item.system_cpu_ticks.value,
                        item.system_cpu_ticks.unit,
                        item.system_cpu_ticks.reason_code,
                    ],
                    "resident_pages": [
                        item.resident_pages.state,
                        item.resident_pages.value,
                        item.resident_pages.unit,
                        item.resident_pages.reason_code,
                    ],
                    "thread_count": [
                        item.thread_count.state,
                        item.thread_count.value,
                        item.thread_count.unit,
                        item.thread_count.reason_code,
                    ],
                    "kernel_state": [
                        item.kernel_state.state,
                        item.kernel_state.value,
                        item.kernel_state.reason_code,
                    ],
                    "observed_at": item.observed_at.isoformat(),
                    "source_id": item.source_id,
                    "source_version": item.source_version,
                    "adapter_version": item.adapter_version,
                    "clock_ticks_per_second": item.clock_ticks_per_second,
                    "page_size_bytes": item.page_size_bytes,
                    "presence": item.presence,
                }
                for item in self.process_snapshots
            ],
            "session_observations": [
                {
                    "observation_id": item.observation_id,
                    "identity": [
                        item.session_identity.provider_key,
                        item.session_identity.installation_id,
                        item.session_identity.identity_kind,
                        item.session_identity.identity_value,
                    ],
                    "observed_at": item.observed_at.isoformat(),
                    "source_id": item.source_id,
                    "source_version": item.source_version,
                    "parser_version": item.parser_version,
                    "provider_version": item.provider_version,
                    "activity_state": item.activity_state,
                    "activity_code": item.activity_code,
                    "activity_reason_code": item.activity_reason_code,
                }
                for item in self.session_observations
            ],
            "metric_observations": [
                {
                    "metric_id": item.metric_id,
                    "session_identity": [
                        item.session_identity.provider_key,
                        item.session_identity.installation_id,
                        item.session_identity.identity_kind,
                        item.session_identity.identity_value,
                    ],
                    "process_identity": (
                        [
                            item.process_identity.platform_source,
                            item.process_identity.platform_scope_id,
                            item.process_identity.pid,
                            item.process_identity.start_time_ticks,
                        ]
                        if item.process_identity is not None
                        else None
                    ),
                    "metric_kind": item.metric_kind,
                    "coefficient": item.coefficient,
                    "scale": item.scale,
                    "unit": item.unit,
                    "scope": item.scope,
                    "semantics": item.semantics,
                    "overlap_class": item.overlap_class,
                    "interval_start": item.interval_start.isoformat()
                    if item.interval_start is not None
                    else None,
                    "interval_end": item.interval_end.isoformat()
                    if item.interval_end is not None
                    else None,
                    "observed_at": item.observed_at.isoformat(),
                    "source_id": item.source_id,
                    "source_version": item.source_version,
                    "parser_version": item.parser_version,
                    "provider_version": item.provider_version,
                }
                for item in self.metric_observations
            ],
            "session_process_links": [
                {
                    "link_id": item.link_id,
                    "session_identity": [
                        item.session_identity.provider_key,
                        item.session_identity.installation_id,
                        item.session_identity.identity_kind,
                        item.session_identity.identity_value,
                    ],
                    "process_identity": [
                        item.process_identity.platform_source,
                        item.process_identity.platform_scope_id,
                        item.process_identity.pid,
                        item.process_identity.start_time_ticks,
                    ],
                    "relationship_kind": item.relationship_kind,
                    "evidence_class": item.evidence_class,
                    "certainty": item.certainty,
                    "source_id": item.source_id,
                    "source_version": item.source_version,
                    "observed_at": item.observed_at.isoformat(),
                }
                for item in self.session_process_links
            ],
            "correlation_evidence": [
                {
                    "evidence_id": item.evidence_id,
                    "identity": [
                        item.session_identity.provider_key,
                        item.session_identity.installation_id,
                        item.session_identity.identity_kind,
                        item.session_identity.identity_value,
                    ],
                    "evidence_class": item.evidence_class,
                    "rule_id": item.rule_id,
                    "account_id": item.account_id,
                    "observed_at": item.observed_at.isoformat(),
                    "source_id": item.source_id,
                    "source_version": item.source_version,
                    "reason_code": item.reason_code,
                }
                for item in self.correlation_evidence
            ],
        }
        canonical = json.dumps(
            document, ensure_ascii=True, separators=(",", ":"), sort_keys=True
        )
        return hashlib.sha256(canonical.encode()).hexdigest()


class RuntimeCommitRequestV1(CollectionOutcomeCommitV1[RuntimeObservationBatchV1]):
    CONTRACT_ID: ClassVar[str] = "CTR-RUN-002"
    OWNER: ClassVar[str] = "PLAN-M06"


class RuntimeCommitReceiptV1(CollectionCommitReceiptV1):
    CONTRACT_ID: ClassVar[str] = "CTR-RUN-002"
    OWNER: ClassVar[str] = "PLAN-M06"


class RuntimeCommitStatusV1(CollectionCommitStatusV1):
    CONTRACT_ID: ClassVar[str] = "CTR-RUN-002"
    OWNER: ClassVar[str] = "PLAN-M06"


@dataclass(frozen=True, slots=True)
class AgentProcessRecordV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-RUN-001"
    OWNER: ClassVar[str] = "PLAN-M06"

    process_id: OpaqueIdV1
    identity: ProcessIdentityV1
    provider_key: str | None
    installation_id: str | None
    executable_label: ProcessLabelFieldV1
    parent_pid: ProcessMetricFieldV1
    user_cpu_ticks: ProcessMetricFieldV1
    system_cpu_ticks: ProcessMetricFieldV1
    resident_pages: ProcessMetricFieldV1
    thread_count: ProcessMetricFieldV1
    kernel_state: ProcessCodeFieldV1
    clock_ticks_per_second: int
    page_size_bytes: int
    provenance: ObservationProvenanceV1
    first_observed_at: datetime
    last_observed_at: datetime
    presence: PresenceStateV1
    current_snapshot_id: OpaqueIdV1
    revision: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            (self.provider_key is not None and not _token(self.provider_key))
            or (self.installation_id is not None and not _token(self.installation_id))
            or (self.provider_key is None and self.installation_id is not None)
            or not isinstance(self.parent_pid, ProcessMetricFieldV1)
            or not isinstance(self.user_cpu_ticks, ProcessMetricFieldV1)
            or not isinstance(self.system_cpu_ticks, ProcessMetricFieldV1)
            or not isinstance(self.resident_pages, ProcessMetricFieldV1)
            or not isinstance(self.thread_count, ProcessMetricFieldV1)
            or not isinstance(self.kernel_state, ProcessCodeFieldV1)
            or type(self.clock_ticks_per_second) is not int
            or self.clock_ticks_per_second <= 0
            or type(self.page_size_bytes) is not int
            or self.page_size_bytes <= 0
            or not isinstance(self.provenance, ObservationProvenanceV1)
            or not _utc(self.first_observed_at)
            or not _utc(self.last_observed_at)
            or self.last_observed_at < self.first_observed_at
            or type(self.revision) is not int
            or self.revision < 1
        ):
            raise InvalidRuntimeObservationV1("runtime_process_view_invalid")


@dataclass(frozen=True, slots=True)
class AgentSessionRecordV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-RUN-002"
    OWNER: ClassVar[str] = "PLAN-M06"

    session_id: OpaqueIdV1
    identity: SessionIdentityV1
    provenance: ObservationProvenanceV1
    first_observed_at: datetime
    last_observed_at: datetime
    correlation_state: CorrelationDecisionStateV1
    account_id: str | None
    revision: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not isinstance(self.provenance, ObservationProvenanceV1)
            or not _utc(self.first_observed_at)
            or not _utc(self.last_observed_at)
            or self.last_observed_at < self.first_observed_at
            or (self.account_id is not None and not _token(self.account_id))
            or (self.correlation_state in {"automatic_matched", "owner_confirmed"})
            != (self.account_id is not None)
            or type(self.revision) is not int
            or self.revision < 1
        ):
            raise InvalidRuntimeObservationV1("runtime_session_view_invalid")


@dataclass(frozen=True, slots=True)
class SessionTopologyFactV1(TechnicalValueV1):
    """Published read-only evidence for one CTR-RUN-003 topology node."""

    CONTRACT_ID: ClassVar[str] = "CTR-RUN-003"
    OWNER: ClassVar[str] = "PLAN-M06"

    session: AgentSessionRecordV1
    primary_process_id: OpaqueIdV1 | None
    evidence_state: TopologyEvidenceStateV1
    reason_code: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not isinstance(self.session, AgentSessionRecordV1)
            or self.evidence_state not in {"eligible", "excluded", "unknown"}
            or (self.evidence_state == "eligible")
            != (self.primary_process_id is not None)
            or not _token(self.reason_code)
        ):
            raise InvalidRuntimeObservationV1("runtime_topology_fact_invalid")


@dataclass(frozen=True, slots=True)
class SessionTopologySnapshotV1(TechnicalValueV1):
    """One bounded repository snapshot consumed by the pure tree builder."""

    CONTRACT_ID: ClassVar[str] = "CTR-RUN-003"
    OWNER: ClassVar[str] = "PLAN-M06"

    sessions: tuple[SessionTopologyFactV1, ...]
    processes: tuple[AgentProcessRecordV1, ...]

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not all(
            isinstance(item, SessionTopologyFactV1) for item in self.sessions
        ) or not all(isinstance(item, AgentProcessRecordV1) for item in self.processes):
            raise InvalidRuntimeObservationV1("runtime_topology_snapshot_invalid")


@dataclass(frozen=True, slots=True)
class ProcessHistoryEntryV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-RUN-001"
    OWNER: ClassVar[str] = "PLAN-M06"

    snapshot_id: OpaqueIdV1
    process_id: OpaqueIdV1
    observed_at: datetime
    collection_run_id: OpaqueIdV1
    source_id: str
    presence: PresenceStateV1
    provenance: ObservationProvenanceV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not _utc(self.observed_at)
            or not _token(self.source_id)
            or not isinstance(self.provenance, ObservationProvenanceV1)
            or self.provenance.source_id != self.source_id
        ):
            raise InvalidRuntimeObservationV1("runtime_process_history_invalid")


@dataclass(frozen=True, slots=True)
class SessionTreeNodeV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-RUN-003"
    OWNER: ClassVar[str] = "PLAN-M06"

    session: AgentSessionRecordV1
    parent_session_id: OpaqueIdV1 | None
    child_session_ids: tuple[OpaqueIdV1, ...]
    orphan_reason: str | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            len(set(self.child_session_ids)) != len(self.child_session_ids)
            or self.session.session_id == self.parent_session_id
            or self.session.session_id in self.child_session_ids
        ):
            raise InvalidRuntimeObservationV1("runtime_session_tree_duplicate_child")
        if self.orphan_reason is not None and not _token(self.orphan_reason):
            raise InvalidRuntimeObservationV1("runtime_session_tree_orphan_invalid")


@dataclass(frozen=True, slots=True)
class SessionTreeViewV1(TechnicalValueV1):
    """Bounded hierarchy with explicit rendered, omitted, and unresolved counts.

    ``included_count`` is the exact number of nodes returned. ``excluded_count``
    counts known reachable descendants omitted by the requested bounds.
    ``unknown_count`` counts returned nodes whose parent relation cannot be
    proven from current strong evidence. The latter intentionally overlaps the
    included count; it is never inferred as zero from absent evidence.
    """

    CONTRACT_ID: ClassVar[str] = "CTR-RUN-003"
    OWNER: ClassVar[str] = "PLAN-M06"

    root_session_id: OpaqueIdV1
    as_of: datetime
    nodes: tuple[SessionTreeNodeV1, ...]
    included_count: int
    excluded_count: int
    unknown_count: int
    partial: bool
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        node_ids = tuple(node.session.session_id for node in self.nodes)
        if (
            not _utc(self.as_of)
            or type(self.included_count) is not int
            or self.included_count != len(self.nodes)
            or len(set(node_ids)) != len(node_ids)
            or self.root_session_id not in node_ids
            or type(self.excluded_count) is not int
            or self.excluded_count < 0
            or type(self.unknown_count) is not int
            or self.unknown_count
            != sum(node.orphan_reason is not None for node in self.nodes)
            or type(self.partial) is not bool
            or self.reason_codes != tuple(sorted(set(self.reason_codes)))
            or not all(_token(code) for code in self.reason_codes)
            or self.partial != bool(self.reason_codes)
        ):
            raise InvalidRuntimeObservationV1("runtime_session_tree_invalid")


# Existing dashboard summary contract retained as a compatible projection.
@dataclass(frozen=True, slots=True)
class InspectedAgentProcessCountV1(TechnicalValueV1):
    provider_key: ProviderKeyV1
    process_count: int


@dataclass(frozen=True, slots=True)
class ProcessInspectionSnapshotV1(TechnicalValueV1):
    observed_at: datetime
    source: str
    providers: tuple[InspectedAgentProcessCountV1, ...]


@dataclass(frozen=True, slots=True)
class AgentProcessViewV1(TechnicalValueV1):
    provider_key: ProviderKeyV1
    process_count: int
    state: Literal["active", "idle"]


@dataclass(frozen=True, slots=True)
class RuntimeOverviewViewV1(TechnicalValueV1):
    observed_at: datetime
    source: str
    total_processes: int
    providers: tuple[AgentProcessViewV1, ...]


@runtime_checkable
class InspectProcessesV1(Protocol):
    def __call__(
        self, request: PlatformInspectionRequestV1
    ) -> PlatformInspectionOutcomeV1: ...


@dataclass(frozen=True, slots=True)
class LiveProcessLocationV1:
    """Guarded process presence and cwd; no account or working-state inference."""

    CONTRACT_ID: ClassVar[str] = "CTR-RUN-006"
    OWNER: ClassVar[str] = "PLAN-M06"

    identity: ProcessIdentityV1
    provider_key: str
    working_directory: str | None
    observed_at: datetime


@dataclass(frozen=True, slots=True)
class LiveProcessLocationsV1:
    CONTRACT_ID: ClassVar[str] = "CTR-RUN-006"
    OWNER: ClassVar[str] = "PLAN-M06"

    items: tuple[LiveProcessLocationV1, ...]
    availability: QueryAvailabilityV1
    provider_version: str | None
    truncated: bool

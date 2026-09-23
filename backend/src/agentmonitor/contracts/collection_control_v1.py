"""M04 collection-control V1 contracts; no provider payload is retained here."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Literal, Protocol, runtime_checkable

from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1, TechnicalValueV1

CollectionRunStateV1 = Literal[
    "requested",
    "queued",
    "running",
    "committing",
    "succeeded",
    "partial",
    "failed",
    "blocked",
    "cancelled",
    "unsupported",
]
CollectionTriggerV1 = Literal[
    "scheduled",
    "manual",
    "observable_request",
    "observable_error",
    "authentication_recovered",
    "registry_changed",
    "reauth_verification",
]
CollectionCommitStatusStateV1 = Literal[
    "not_committed", "committed", "conflict", "unavailable"
]

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SAFE_CODE = re.compile(r"[a-z][a-z0-9_]{0,127}\Z")


class InvalidCollectionControlV1(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _bounded(value: object, maximum: int = 128) -> bool:
    return (
        type(value) is str
        and value == value.strip()
        and 1 <= len(value) <= maximum
        and value.isprintable()
    )


@dataclass(frozen=True, slots=True)
class CollectionTargetV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-COL-001"
    OWNER: ClassVar[str] = "PLAN-M04"

    provider_key: str
    installation_id: OpaqueIdV1
    account_id: OpaqueIdV1 | None
    profile_id: OpaqueIdV1 | None
    resource_id: OpaqueIdV1 | None
    capability_id: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not _bounded(self.provider_key, 64) or not _bounded(self.capability_id, 128):
            raise InvalidCollectionControlV1("collection_target_invalid")


@dataclass(frozen=True, slots=True)
class CollectionRequestV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-COL-001"
    OWNER: ClassVar[str] = "PLAN-M04"

    request_id: OpaqueIdV1
    target: CollectionTargetV1
    trigger: CollectionTriggerV1
    requested_at: datetime
    correlation_id: OpaqueIdV1
    idempotency_key_digest: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if _SHA256.fullmatch(self.idempotency_key_digest) is None:
            raise InvalidCollectionControlV1("collection_request_digest_invalid")


@dataclass(frozen=True, slots=True)
class CollectionRunAdmissionV1(TechnicalValueV1):
    """Durable pre-I/O admission metadata; contains no observation values."""

    CONTRACT_ID: ClassVar[str] = "CTR-COL-002"
    OWNER: ClassVar[str] = "PLAN-M04"

    run_id: OpaqueIdV1
    schedule_id: OpaqueIdV1
    request_id: OpaqueIdV1
    trigger: CollectionTriggerV1
    operation_family: str
    requested_capability_ids: tuple[str, ...]
    capability_set_version: str
    request_auth_method: str
    request_principal_id: OpaqueIdV1 | None
    correlation_id: OpaqueIdV1
    causation_id: OpaqueIdV1 | None
    target_key_digest: str
    provider_key: str
    installation_id: OpaqueIdV1
    account_id: OpaqueIdV1 | None
    profile_id: OpaqueIdV1 | None
    resource_id: OpaqueIdV1 | None
    capability_id: str
    source_id: str
    adapter_version: str
    provider_version: str | None
    adapter_protocol_version: str
    manifest_fingerprint: str
    collection_policy_version: str
    registry_revision: int
    retry_chain_id: OpaqueIdV1
    attempt_ordinal: int
    target_generation: int
    scheduler_instance_id: OpaqueIdV1
    lease_policy_version: str
    budget_policy_id: str
    budget_policy_version: str
    budget_scope_digest: str
    budget_dimension: str
    budget_unit: str
    budget_units: int
    budget_limit_units: int
    budget_window_start: datetime
    budget_window_end: datetime
    payload_schema: str
    idempotency_key_digest: str | None
    request_digest: str
    requested_at: datetime
    deadline_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            _SHA256.fullmatch(self.target_key_digest) is None
            or _SHA256.fullmatch(self.request_digest) is None
            or (
                self.idempotency_key_digest is not None
                and _SHA256.fullmatch(self.idempotency_key_digest) is None
            )
            or (self.trigger == "manual" and self.idempotency_key_digest is None)
            or _SHA256.fullmatch(self.budget_scope_digest) is None
            or _SHA256.fullmatch(self.manifest_fingerprint) is None
            or not all(
                _bounded(value)
                for value in (
                    self.operation_family,
                    self.capability_set_version,
                    self.request_auth_method,
                    self.provider_key,
                    self.capability_id,
                    self.source_id,
                    self.adapter_version,
                    self.adapter_protocol_version,
                    self.collection_policy_version,
                    self.lease_policy_version,
                    self.budget_policy_id,
                    self.budget_policy_version,
                    self.budget_dimension,
                    self.budget_unit,
                    self.payload_schema,
                )
            )
            or not self.requested_capability_ids
            or len(self.requested_capability_ids) > 16
            or self.requested_capability_ids
            != tuple(sorted(set(self.requested_capability_ids)))
            or not all(_bounded(value) for value in self.requested_capability_ids)
            or (
                self.provider_version is not None
                and not _bounded(self.provider_version)
            )
            or type(self.target_generation) is not int
            or self.target_generation < 1
            or type(self.registry_revision) is not int
            or self.registry_revision < 1
            or type(self.attempt_ordinal) is not int
            or self.attempt_ordinal < 1
            or type(self.budget_units) is not int
            or self.budget_units < 0
            or type(self.budget_limit_units) is not int
            or self.budget_limit_units < self.budget_units
            or self.budget_window_end <= self.budget_window_start
            or self.deadline_at <= self.requested_at
        ):
            raise InvalidCollectionControlV1("collection_admission_invalid")


@dataclass(frozen=True, slots=True)
class CollectionRunViewV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-COL-002"
    OWNER: ClassVar[str] = "PLAN-M04"

    run_id: OpaqueIdV1
    schedule_id: OpaqueIdV1
    provider_key: str
    account_id: OpaqueIdV1 | None
    resource_id: OpaqueIdV1 | None
    capability_id: str
    state: CollectionRunStateV1
    source_id: str
    adapter_version: str
    provider_version: str | None
    target_generation: int
    fencing_token: int
    requested_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    deadline_at: datetime
    duration_ms: int | None
    payload_digest: str | None
    outcome_code: str | None
    error_code: str | None
    observation_ids: tuple[OpaqueIdV1, ...]

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if self.duration_ms is not None and (
            type(self.duration_ms) is not int or self.duration_ms < 0
        ):
            raise InvalidCollectionControlV1("collection_duration_invalid")
        if (
            self.payload_digest is not None
            and _SHA256.fullmatch(self.payload_digest) is None
        ):
            raise InvalidCollectionControlV1("collection_payload_digest_invalid")
        pre_dispatch = self.state in {"requested", "queued"}
        running = self.state == "running"
        committing = self.state == "committing"
        committed = self.state in {"succeeded", "partial"}
        failed = self.state in {"failed", "blocked", "cancelled", "unsupported"}
        if (
            type(self.target_generation) is not int
            or self.target_generation < 1
            or type(self.fencing_token) is not int
            or self.fencing_token < 1
            or self.deadline_at <= self.requested_at
            or (self.started_at is not None and self.started_at < self.requested_at)
            or (
                self.completed_at is not None
                and self.started_at is not None
                and self.completed_at < self.started_at
            )
        ):
            raise InvalidCollectionControlV1("collection_run_state_invalid")
        valid = (
            (
                pre_dispatch
                and self.started_at is None
                and self.completed_at is None
                and self.duration_ms is None
                and self.payload_digest is None
                and self.outcome_code is None
                and self.error_code is None
                and not self.observation_ids
            )
            or (
                running
                and self.started_at is not None
                and self.completed_at is None
                and self.duration_ms is None
                and self.payload_digest is None
                and self.outcome_code is None
                and self.error_code is None
                and not self.observation_ids
            )
            or (
                committing
                and self.started_at is not None
                and self.completed_at is None
                and self.duration_ms is None
                and self.payload_digest is not None
                and self.outcome_code in {"succeeded", "partial"}
                and self.error_code is None
                and not self.observation_ids
            )
            or (
                committed
                and self.started_at is not None
                and self.completed_at is not None
                and self.duration_ms is not None
                and self.payload_digest is not None
                and self.outcome_code == self.state
                and self.error_code is None
                and bool(self.observation_ids)
            )
            or (
                failed
                and self.started_at is not None
                and self.completed_at is not None
                and self.duration_ms is not None
                and self.outcome_code == self.error_code
                and self.error_code is not None
                and _SAFE_CODE.fullmatch(self.error_code) is not None
                and not self.observation_ids
            )
        )
        if not valid:
            raise InvalidCollectionControlV1("collection_run_state_invalid")


@dataclass(frozen=True, slots=True)
class CollectionOutcomeCommitV1[PayloadT: TechnicalValueV1](TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-COL-006"
    OWNER: ClassVar[str] = "PLAN-M04"

    run_id: OpaqueIdV1
    target_generation: int
    capability_id: str
    payload_schema: str
    payload_digest: str
    terminal_state: Literal["succeeded", "partial"]
    payload: PayloadT
    provenance: ObservationProvenanceV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.target_generation) is not int
            or self.target_generation < 1
            or not _bounded(self.capability_id)
            or not _bounded(self.payload_schema)
            or _SHA256.fullmatch(self.payload_digest) is None
        ):
            raise InvalidCollectionControlV1("collection_commit_invalid")


@dataclass(frozen=True, slots=True)
class CollectionCommitReceiptV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-COL-006"
    OWNER: ClassVar[str] = "PLAN-M04"

    run_id: OpaqueIdV1
    target_generation: int
    capability_id: str
    payload_schema: str
    payload_digest: str
    consumer_key: str
    consumer_version: str
    observation_ids: tuple[OpaqueIdV1, ...]
    observation_set_digest: str
    stored_at_start: datetime
    stored_at_end: datetime
    affected_projection_ids: tuple[OpaqueIdV1, ...]
    projection_versions: tuple[int, ...]
    event_ids: tuple[OpaqueIdV1, ...]
    stored_at: datetime
    receipt_version: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.target_generation) is not int
            or self.target_generation < 1
            or _SHA256.fullmatch(self.payload_digest) is None
            or not _bounded(self.capability_id)
            or not _bounded(self.payload_schema)
            or not _bounded(self.consumer_key)
            or not _bounded(self.consumer_version)
            or not self.observation_ids
            or len(set(self.observation_ids)) != len(self.observation_ids)
            or _SHA256.fullmatch(self.observation_set_digest) is None
            or self.stored_at_end < self.stored_at_start
            or self.stored_at != self.stored_at_end
            or not self.affected_projection_ids
            or len(set(self.affected_projection_ids))
            != len(self.affected_projection_ids)
            or len(self.affected_projection_ids) != len(self.projection_versions)
            or any(
                type(version) is not int or version < 1
                for version in self.projection_versions
            )
            or not self.event_ids
            or len(set(self.event_ids)) != len(self.event_ids)
            or type(self.receipt_version) is not int
            or self.receipt_version < 1
        ):
            raise InvalidCollectionControlV1("collection_receipt_invalid")


@dataclass(frozen=True, slots=True)
class CollectionCommitStatusV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-COL-006"
    OWNER: ClassVar[str] = "PLAN-M04"

    state: CollectionCommitStatusStateV1
    receipt: CollectionCommitReceiptV1 | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (self.state == "committed") != (self.receipt is not None):
            raise InvalidCollectionControlV1("collection_commit_status_invalid")


@runtime_checkable
class CollectionOutcomeCommitPortV1[PayloadT: TechnicalValueV1](Protocol):
    def commit(
        self, request: CollectionOutcomeCommitV1[PayloadT]
    ) -> CollectionCommitReceiptV1: ...

    def get_commit_status(
        self, run_id: OpaqueIdV1, capability_id: str
    ) -> CollectionCommitStatusV1: ...


@dataclass(frozen=True, slots=True)
class CollectionCompletedV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-COL-003"
    OWNER: ClassVar[str] = "PLAN-M04"

    run_id: OpaqueIdV1
    terminal_state: Literal["succeeded", "partial"]
    observation_ids: tuple[OpaqueIdV1, ...]
    completed_at: datetime


@dataclass(frozen=True, slots=True)
class CollectionFailedV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-COL-004"
    OWNER: ClassVar[str] = "PLAN-M04"

    run_id: OpaqueIdV1
    terminal_state: Literal["failed", "blocked", "cancelled", "unsupported"]
    error_code: str
    completed_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if _SAFE_CODE.fullmatch(self.error_code) is None:
            raise InvalidCollectionControlV1("collection_error_code_invalid")


@dataclass(frozen=True, slots=True)
class CollectorHealthV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-COL-005"
    OWNER: ClassVar[str] = "PLAN-M04"

    state: Literal["healthy", "degraded", "blocked", "stopping", "unavailable"]
    due_count: int
    running_count: int
    blocked_count: int
    checked_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if any(
            type(value) is not int or value < 0
            for value in (self.due_count, self.running_count, self.blocked_count)
        ):
            raise InvalidCollectionControlV1("collector_health_count_invalid")

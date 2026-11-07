"""M04 collection-control V1 contracts; no provider payload is retained here."""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import ClassVar, Literal, Protocol, get_args, runtime_checkable

from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1, QueryPageV1, TechnicalValueV1
from agentmonitor.contracts.provider_system_v1 import OutcomeStateV1, RetryAdviceV1
from agentmonitor.contracts.registry_v1 import ProviderTargetRefV1

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
OllamaCloudAdmissionDecisionStateV1 = Literal[
    "acquired",
    "replayed_active",
    "replayed_terminal",
    "not_due",
    "busy",
    "no_candidate",
]
OllamaCloudAdmissionOutcomeV1 = Literal["succeeded", "rate_limited", "failed"]
OllamaCloudVerificationJobStateV1 = Literal["queued", "claimed", "admitted", "terminal"]
OllamaCloudVerificationGateStateV1 = Literal["ready", "not_due", "busy", "unresolved"]
OllamaCloudVerificationDispatchCertaintyV1 = Literal[
    "not_started", "may_have_started", "response_received"
]
OllamaCloudSourceAuthorizationSignalV1 = Literal[
    "verified_success",
    "credential_unauthorized",
    "provider_schema_incompatible",
    "rate_limited",
    "transient_failure",
    "authorization_unavailable",
    "credential_update_in_progress",
    "outcome_unresolved",
]


@dataclass(frozen=True, slots=True)
class CloudScheduleStatusV1(TechnicalValueV1):
    """Read-only M04 scheduled-lane identity for operational presentation."""

    CONTRACT_ID: ClassVar[str] = "CTR-COL-011"
    OWNER: ClassVar[str] = "PLAN-M04"

    schedule_id: str
    target_key_digest: str
    account_id: str
    profile_id: str
    resource_id: str
    access_target_id: str
    target_generation: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            any(
                not isinstance(value, str) or not value.strip() or len(value) > 256
                for value in (
                    self.schedule_id,
                    self.account_id,
                    self.profile_id,
                    self.resource_id,
                    self.access_target_id,
                )
            )
            or len(self.target_key_digest) != 64
            or any(value not in "0123456789abcdef" for value in self.target_key_digest)
            or type(self.target_generation) is not int
            or self.target_generation < 1
        ):
            raise ValueError("cloud_schedule_status_invalid")


CollectorHealthStateV1 = Literal[
    "healthy",
    "degraded",
    "failed",
    "blocked",
    "backoff",
    "unsupported",
    "paused",
    "unknown",
]
CollectorFreshnessStateV1 = Literal[
    "current", "stale", "unknown", "unsupported", "not_applicable"
]
CollectorRetryCategoryV1 = Literal[
    "none",
    "rate_backoff",
    "transient_backoff",
    "authentication",
    "authorization",
    "user_action",
    "compatibility",
    "unknown_constraints",
    "unsupported",
    "cancelled",
    "unclassified",
]
CollectorConditionReasonV1 = Literal[
    "collector_healthy",
    "collector_partial",
    "collector_failed",
    "collector_blocked_authentication",
    "collector_blocked_authorization",
    "collector_blocked_user_action",
    "collector_blocked_compatibility",
    "collector_blocked_unknown_constraints",
    "collector_blocked_unclassified",
    "collector_rate_backoff",
    "collector_transient_backoff",
    "collector_unsupported",
    "collector_cancelled",
    "collector_paused",
    "collector_no_success",
    "collector_stale",
    "collector_source_unknown",
    "collector_clock_invalid",
]


@dataclass(frozen=True, slots=True)
class CollectorAlertConditionV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-COL-007"
    OWNER: ClassVar[str] = "PLAN-M04"
    target_id: OpaqueIdV1
    account_id: OpaqueIdV1 | None
    provider_key: str
    capability_id: str
    generation: int
    health_state: CollectorHealthStateV1
    freshness_state: CollectorFreshnessStateV1
    retry_category: CollectorRetryCategoryV1
    latest_run_id: OpaqueIdV1 | None
    last_successful_at: datetime | None
    freshness_deadline: datetime | None
    not_before_at: datetime | None
    evaluated_at: datetime
    reason_code: CollectorConditionReasonV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.generation) is not int
            or self.generation < 1
            or not _bounded(self.provider_key, 64)
            or not _bounded(self.capability_id)
            or (self.last_successful_at is None) != (self.freshness_deadline is None)
            or (
                self.last_successful_at is not None
                and self.freshness_deadline is not None
                and self.freshness_deadline <= self.last_successful_at
            )
            or (
                self.freshness_state in {"current", "stale"}
                and self.freshness_deadline is None
            )
            or (
                self.freshness_state == "current"
                and (
                    self.health_state != "healthy"
                    or self.freshness_deadline is None
                    or self.evaluated_at >= self.freshness_deadline
                )
            )
            or (
                self.freshness_state == "stale"
                and (
                    self.freshness_deadline is None
                    or self.evaluated_at < self.freshness_deadline
                )
            )
            or (
                self.health_state == "backoff"
                and (
                    self.not_before_at is None
                    or self.not_before_at <= self.evaluated_at
                )
            )
        ):
            raise InvalidCollectionControlV1("collector_condition_invalid")


@dataclass(frozen=True, slots=True)
class CollectorAlertQueryV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-COL-007"
    OWNER: ClassVar[str] = "PLAN-M04"
    as_of: datetime
    deadline: datetime
    correlation_id: OpaqueIdV1
    provider_key: str | None = None
    account_id: OpaqueIdV1 | None = None
    target_id: OpaqueIdV1 | None = None
    minimum_generation: int | None = None
    limit: int = 100
    after_target_id: OpaqueIdV1 | None = None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not timedelta(0) < self.deadline - self.as_of <= timedelta(seconds=2)
            or type(self.limit) is not int
            or not 1 <= self.limit <= 200
            or (self.provider_key is not None and not _bounded(self.provider_key, 64))
            or (
                self.minimum_generation is not None
                and (
                    self.target_id is None
                    or type(self.minimum_generation) is not int
                    or self.minimum_generation < 1
                )
            )
        ):
            raise InvalidCollectionControlV1("collector_condition_query_invalid")


@dataclass(frozen=True, slots=True)
class CollectorHealthChangedV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-COL-007"
    OWNER: ClassVar[str] = "PLAN-M04"
    previous_health_state: CollectorHealthStateV1 | None
    previous_freshness_state: CollectorFreshnessStateV1 | None
    current: CollectorAlertConditionV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            (self.previous_health_state is None)
            != (self.previous_freshness_state is None)
            or (
                self.previous_health_state is not None
                and self.previous_health_state not in get_args(CollectorHealthStateV1)
            )
            or (
                self.previous_freshness_state is not None
                and self.previous_freshness_state
                not in get_args(CollectorFreshnessStateV1)
            )
        ):
            raise InvalidCollectionControlV1("collector_transition_invalid")


@dataclass(frozen=True, slots=True)
class CollectionFailurePolicyV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-COL-004"
    OWNER: ClassVar[str] = "PLAN-M04"
    provider_outcome: OutcomeStateV1
    retry: RetryAdviceV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if self.provider_outcome in {"success", "partial"}:
            raise InvalidCollectionControlV1("collection_failure_policy_invalid")


class GetCurrentCollectorAlertInputsV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-COL-007"
    OWNER: ClassVar[str] = "PLAN-M04"

    async def __call__(
        self, query: CollectorAlertQueryV1
    ) -> QueryPageV1[CollectorAlertConditionV1]: ...


class RefreshCollectorAlertInputsV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-COL-007"
    OWNER: ClassVar[str] = "PLAN-M04"

    async def __call__(
        self, query: CollectorAlertQueryV1
    ) -> QueryPageV1[CollectorAlertConditionV1]: ...


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


def _utc(value: object) -> bool:
    return isinstance(value, datetime) and value.utcoffset() == timedelta(0)


@dataclass(frozen=True, slots=True)
class OllamaCloudRequestAcquireV1(TechnicalValueV1):
    """One create-once attempt to acquire the global cloud request gate."""

    CONTRACT_ID: ClassVar[str] = "CTR-COL-008"
    OWNER: ClassVar[str] = "PLAN-M04"

    admission_id: OpaqueIdV1
    scheduler_instance_id: OpaqueIdV1
    requested_at: datetime
    lease_expires_at: datetime
    jitter_seconds: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not _utc(self.requested_at)
            or not _utc(self.lease_expires_at)
            or not timedelta(0)
            < self.lease_expires_at - self.requested_at
            <= timedelta(seconds=60)
            or type(self.jitter_seconds) is not int
            or not 0 <= self.jitter_seconds <= 10
        ):
            raise InvalidCollectionControlV1("ollama_cloud_acquire_invalid")


@dataclass(frozen=True, slots=True)
class OllamaCloudVerificationAcquireV1(TechnicalValueV1):
    """One owner-targeted first-verification acquire on the global rate gate."""

    CONTRACT_ID: ClassVar[str] = "CTR-COL-010"
    OWNER: ClassVar[str] = "PLAN-M04"

    admission_id: OpaqueIdV1
    scheduler_instance_id: OpaqueIdV1
    schedule_id: OpaqueIdV1
    account_id: OpaqueIdV1
    target_generation: int
    requested_at: datetime
    lease_expires_at: datetime
    jitter_seconds: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.target_generation) is not int
            or self.target_generation < 1
            or not _utc(self.requested_at)
            or not _utc(self.lease_expires_at)
            or not timedelta(0)
            < self.lease_expires_at - self.requested_at
            <= timedelta(seconds=60)
            or type(self.jitter_seconds) is not int
            or not 0 <= self.jitter_seconds <= 10
        ):
            raise InvalidCollectionControlV1(
                "ollama_cloud_verification_acquire_invalid"
            )


@dataclass(frozen=True, slots=True)
class OllamaCloudVerificationTargetV1(TechnicalValueV1):
    """Exact cloud-only target registered for one owner verification attempt."""

    CONTRACT_ID: ClassVar[str] = "CTR-COL-010"
    OWNER: ClassVar[str] = "PLAN-M04"

    schedule_id: OpaqueIdV1
    account_id: OpaqueIdV1
    profile_id: OpaqueIdV1
    resource_id: OpaqueIdV1
    provider_target: ProviderTargetRefV1
    target_key_digest: str
    target_generation: int
    requested_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            self.provider_target.target_kind != "cloud_service"
            or _SHA256.fullmatch(self.target_key_digest) is None
            or type(self.target_generation) is not int
            or self.target_generation < 1
            or not _utc(self.requested_at)
        ):
            raise InvalidCollectionControlV1("ollama_cloud_verification_target_invalid")


def _verification_job_id(value: OpaqueIdV1) -> bool:
    raw = value.value
    return (
        len(raw) == 37
        and raw.startswith("amvj_")
        and all(character in "0123456789abcdef" for character in raw[5:])
    )


def _cloud_access_target_id(value: OpaqueIdV1) -> bool:
    raw = value.value
    return (
        len(raw) == 37
        and raw.startswith("amat_")
        and all(character in "0123456789abcdef" for character in raw[5:])
    )


@dataclass(frozen=True, slots=True)
class OllamaCloudVerificationReplayQueryV1(TechnicalValueV1):
    """Lookup one external initiation request before current-state fencing."""

    CONTRACT_ID: ClassVar[str] = "CTR-COL-010"
    OWNER: ClassVar[str] = "PLAN-M04"

    idempotency_key: OpaqueIdV1
    principal_id: OpaqueIdV1
    account_id: OpaqueIdV1
    expected_account_record_version: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.expected_account_record_version) is not int
            or self.expected_account_record_version < 1
        ):
            raise InvalidCollectionControlV1(
                "ollama_cloud_verification_replay_query_invalid"
            )


@dataclass(frozen=True, slots=True)
class OllamaCloudVerificationEnqueueV1(TechnicalValueV1):
    """Create-once owner request bound to one exact cloud credential generation."""

    CONTRACT_ID: ClassVar[str] = "CTR-COL-010"
    OWNER: ClassVar[str] = "PLAN-M04"

    idempotency_key: OpaqueIdV1
    principal_id: OpaqueIdV1
    schedule_id: OpaqueIdV1
    account_id: OpaqueIdV1
    access_target_id: OpaqueIdV1
    binding_generation: int
    requested_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not _cloud_access_target_id(self.access_target_id)
            or type(self.binding_generation) is not int
            or self.binding_generation < 1
            or not _utc(self.requested_at)
        ):
            raise InvalidCollectionControlV1(
                "ollama_cloud_verification_enqueue_invalid"
            )


@dataclass(frozen=True, slots=True)
class OllamaCloudVerificationEnqueueV2(OllamaCloudVerificationEnqueueV1):
    """V2 initiation retains the external account version.

    The client identity is principal/idempotency/account/expected account
    version. Schedule, target and binding generation are server-derived facts
    frozen by the first successful insertion and are not recomputed for replay.
    """

    CONTRACT_ID: ClassVar[str] = "CTR-COL-010"
    CONTRACT_VERSION: ClassVar[str] = "2.0.0"
    OWNER: ClassVar[str] = "PLAN-M04"

    expected_account_record_version: int

    def __post_init__(self) -> None:
        super(OllamaCloudVerificationEnqueueV2, self).__post_init__()
        if (
            type(self.expected_account_record_version) is not int
            or self.expected_account_record_version < 1
        ):
            raise InvalidCollectionControlV1(
                "ollama_cloud_verification_enqueue_v2_invalid"
            )


@dataclass(frozen=True, slots=True)
class OllamaCloudVerificationClaimRequestV1(TechnicalValueV1):
    """Bounded worker claim; expiry permits replay only before rate admission."""

    CONTRACT_ID: ClassVar[str] = "CTR-COL-010"
    OWNER: ClassVar[str] = "PLAN-M04"

    worker_instance_id: OpaqueIdV1
    claimed_at: datetime
    claim_expires_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not _utc(self.claimed_at)
            or not _utc(self.claim_expires_at)
            or not timedelta(0)
            < self.claim_expires_at - self.claimed_at
            <= timedelta(seconds=60)
        ):
            raise InvalidCollectionControlV1("ollama_cloud_verification_claim_invalid")


@dataclass(frozen=True, slots=True)
class OllamaCloudVerificationJobClaimV1(TechnicalValueV1):
    """Exact claim fence returned to one verification worker."""

    CONTRACT_ID: ClassVar[str] = "CTR-COL-010"
    OWNER: ClassVar[str] = "PLAN-M04"

    job_id: OpaqueIdV1
    worker_instance_id: OpaqueIdV1
    request_principal_id: OpaqueIdV1
    idempotency_key_digest: str
    schedule_id: OpaqueIdV1
    account_id: OpaqueIdV1
    access_target_id: OpaqueIdV1
    binding_generation: int
    fencing_token: int
    claimed_at: datetime
    claim_expires_at: datetime
    record_version: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not _verification_job_id(self.job_id)
            or not isinstance(self.request_principal_id, OpaqueIdV1)
            or _SHA256.fullmatch(self.idempotency_key_digest) is None
            or not _cloud_access_target_id(self.access_target_id)
            or type(self.binding_generation) is not int
            or self.binding_generation < 1
            or type(self.fencing_token) is not int
            or self.fencing_token < 1
            or type(self.record_version) is not int
            or self.record_version < 1
            or not _utc(self.claimed_at)
            or not _utc(self.claim_expires_at)
            or not timedelta(0)
            < self.claim_expires_at - self.claimed_at
            <= timedelta(seconds=60)
        ):
            raise InvalidCollectionControlV1("ollama_cloud_verification_claim_invalid")


@dataclass(frozen=True, slots=True)
class OllamaCloudVerificationClaimTerminalV1(TechnicalValueV1):
    """Fenced terminal known to precede rate admission and provider dispatch."""

    CONTRACT_ID: ClassVar[str] = "CTR-COL-010"
    OWNER: ClassVar[str] = "PLAN-M04"

    job_id: OpaqueIdV1
    worker_instance_id: OpaqueIdV1
    fencing_token: int
    claimed_at: datetime
    claim_expires_at: datetime
    terminal_at: datetime
    reason_code: Literal["worker_unavailable", "target_unavailable"]

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not _verification_job_id(self.job_id)
            or type(self.fencing_token) is not int
            or self.fencing_token < 1
            or not all(
                _utc(value)
                for value in (
                    self.claimed_at,
                    self.claim_expires_at,
                    self.terminal_at,
                )
            )
            or not timedelta(0)
            < self.claim_expires_at - self.claimed_at
            <= timedelta(seconds=60)
            or not self.claimed_at <= self.terminal_at <= self.claim_expires_at
            or self.reason_code not in {"worker_unavailable", "target_unavailable"}
        ):
            raise InvalidCollectionControlV1(
                "ollama_cloud_verification_terminal_invalid"
            )


@dataclass(frozen=True, slots=True)
class OllamaCloudVerificationInterruptionProofV1(TechnicalValueV1):
    """Trusted composition proof that no consumer or M02 receipt committed."""

    CONTRACT_ID: ClassVar[str] = "CTR-COL-010"
    OWNER: ClassVar[str] = "PLAN-M04"

    job_id: OpaqueIdV1
    run_id: OpaqueIdV1
    admission_id: OpaqueIdV1
    commit_status: Literal["not_committed"]
    verification_receipt_state: Literal["absent"]
    checked_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not _verification_job_id(self.job_id)
            or not isinstance(self.run_id, OpaqueIdV1)
            or not isinstance(self.admission_id, OpaqueIdV1)
            or self.commit_status != "not_committed"
            or self.verification_receipt_state != "absent"
            or not _utc(self.checked_at)
        ):
            raise InvalidCollectionControlV1(
                "ollama_cloud_verification_interruption_invalid"
            )


@dataclass(frozen=True, slots=True)
class OllamaCloudVerificationJobViewV1(TechnicalValueV1):
    """Safe durable projection of one owner-verification request."""

    CONTRACT_ID: ClassVar[str] = "CTR-COL-010"
    OWNER: ClassVar[str] = "PLAN-M04"

    job_id: OpaqueIdV1
    account_id: OpaqueIdV1
    access_target_id: OpaqueIdV1
    schedule_id: OpaqueIdV1
    binding_generation: int
    state: OllamaCloudVerificationJobStateV1
    requested_at: datetime
    not_before_at: datetime
    admission_id: OpaqueIdV1 | None
    run_id: OpaqueIdV1 | None
    dispatch_certainty: OllamaCloudVerificationDispatchCertaintyV1 | None
    terminal_at: datetime | None
    outcome: OllamaCloudAdmissionOutcomeV1 | None
    reason_code: str | None
    retry_after_seconds: int | None
    record_version: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        pre_admission = self.state in {"queued", "claimed"}
        terminal = self.state == "terminal"
        if (
            not _verification_job_id(self.job_id)
            or not _cloud_access_target_id(self.access_target_id)
            or type(self.binding_generation) is not int
            or self.binding_generation < 1
            or type(self.record_version) is not int
            or self.record_version < 1
            or not _utc(self.requested_at)
            or not _utc(self.not_before_at)
            or self.not_before_at < self.requested_at
            or pre_admission
            and (
                self.admission_id is not None
                or self.run_id is not None
                or self.dispatch_certainty is not None
            )
            or self.state == "admitted"
            and (self.admission_id is None or self.dispatch_certainty is None)
            or terminal != (self.terminal_at is not None)
            or (
                self.terminal_at is not None
                and (not _utc(self.terminal_at) or self.terminal_at < self.requested_at)
            )
            or terminal
            and self.dispatch_certainty is None
            or terminal
            and (
                self.dispatch_certainty == "may_have_started"
                or self.reason_code is None
            )
            or (self.dispatch_certainty == "response_received")
            != (self.outcome is not None)
            or (
                self.reason_code is not None
                and _SAFE_CODE.fullmatch(self.reason_code) is None
            )
            or self.retry_after_seconds is not None
            and (
                self.outcome != "rate_limited"
                or type(self.retry_after_seconds) is not int
                or not 0 <= self.retry_after_seconds <= 2**63 - 1
            )
        ):
            raise InvalidCollectionControlV1("ollama_cloud_verification_job_invalid")


@dataclass(frozen=True, slots=True)
class OllamaCloudVerificationStatusV1(TechnicalValueV1):
    """One binding's latest work plus authoritative provider-global gate state."""

    CONTRACT_ID: ClassVar[str] = "CTR-COL-010"
    OWNER: ClassVar[str] = "PLAN-M04"

    account_id: OpaqueIdV1
    binding_generation: int
    job: OllamaCloudVerificationJobViewV1 | None
    gate_state: OllamaCloudVerificationGateStateV1
    retry_at: datetime | None
    queried_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        requires_retry = self.gate_state in {"not_due", "busy"}
        if (
            type(self.binding_generation) is not int
            or self.binding_generation < 1
            or not _utc(self.queried_at)
            or (
                self.job is not None
                and (
                    self.job.account_id != self.account_id
                    or self.job.binding_generation != self.binding_generation
                )
            )
            or requires_retry != (self.retry_at is not None)
            or (
                self.retry_at is not None
                and (not _utc(self.retry_at) or self.retry_at <= self.queried_at)
            )
        ):
            raise InvalidCollectionControlV1("ollama_cloud_verification_status_invalid")


@dataclass(frozen=True, slots=True)
class OllamaCloudLatestSourceSignalQueryV1(TechnicalValueV1):
    """Exact current cloud source whose latest M04 signal is requested."""

    CONTRACT_ID: ClassVar[str] = "CTR-COL-008"
    OWNER: ClassVar[str] = "PLAN-M04"

    account_id: OpaqueIdV1
    binding_generation: int
    access_target_id: OpaqueIdV1
    capability_id: str
    source_id: str
    adapter_version: str
    source_fingerprint: str
    payload_schema: str
    queried_at: datetime
    exclude_active_lease: "OllamaCloudRequestLeaseV1 | None" = None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not isinstance(self.account_id, OpaqueIdV1)
            or not _cloud_access_target_id(self.access_target_id)
            or type(self.binding_generation) is not int
            or self.binding_generation < 1
            or not all(
                _bounded(value)
                for value in (
                    self.capability_id,
                    self.source_id,
                    self.adapter_version,
                    self.payload_schema,
                )
            )
            or _SHA256.fullmatch(self.source_fingerprint) is None
            or not _utc(self.queried_at)
            or self.exclude_active_lease is not None
            and (
                not isinstance(self.exclude_active_lease, OllamaCloudRequestLeaseV1)
                or self.exclude_active_lease.account_id != self.account_id
                or self.queried_at < self.exclude_active_lease.started_at
                or self.queried_at >= self.exclude_active_lease.lease_expires_at
            )
        ):
            raise InvalidCollectionControlV1("ollama_cloud_source_signal_query_invalid")


@dataclass(frozen=True, slots=True)
class OllamaCloudLatestSourceSignalV1(TechnicalValueV1):
    """Latest exact-source outcome plus the authoritative global gate state."""

    CONTRACT_ID: ClassVar[str] = "CTR-COL-008"
    CONTRACT_VERSION: ClassVar[str] = "1.2.0"
    OWNER: ClassVar[str] = "PLAN-M04"

    account_id: OpaqueIdV1
    binding_generation: int
    access_target_id: OpaqueIdV1
    capability_id: str
    source_id: str
    adapter_version: str
    source_fingerprint: str
    payload_schema: str
    signal: OllamaCloudSourceAuthorizationSignalV1
    run_id: OpaqueIdV1 | None
    admission_id: OpaqueIdV1 | None
    run_state: CollectionRunStateV1 | None
    dispatch_certainty: OllamaCloudVerificationDispatchCertaintyV1 | None
    run_requested_at: datetime | None
    signal_observed_at: datetime | None
    gate_state: OllamaCloudVerificationGateStateV1
    retry_at: datetime | None
    queried_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        has_run = self.run_id is not None
        non_terminal = self.run_state in {
            "requested",
            "queued",
            "running",
            "committing",
        }
        terminal_signal = self.signal != "outcome_unresolved"
        requires_retry = self.gate_state in {"not_due", "busy"}
        if (
            not isinstance(self.account_id, OpaqueIdV1)
            or not _cloud_access_target_id(self.access_target_id)
            or type(self.binding_generation) is not int
            or self.binding_generation < 1
            or not all(
                _bounded(value)
                for value in (
                    self.capability_id,
                    self.source_id,
                    self.adapter_version,
                    self.payload_schema,
                )
            )
            or _SHA256.fullmatch(self.source_fingerprint) is None
            or has_run
            != (
                self.admission_id is not None
                and self.run_state is not None
                and self.dispatch_certainty is not None
                and self.run_requested_at is not None
            )
            or terminal_signal
            and (not has_run or non_terminal or self.signal_observed_at is None)
            or self.signal == "verified_success"
            and (
                self.run_state not in {"succeeded", "partial"}
                or self.dispatch_certainty != "response_received"
            )
            or self.signal
            in {
                "credential_unauthorized",
                "provider_schema_incompatible",
                "rate_limited",
            }
            and (
                self.run_state != "failed"
                or self.dispatch_certainty != "response_received"
            )
            or self.signal
            in {"authorization_unavailable", "credential_update_in_progress"}
            and (self.run_state != "failed" or self.dispatch_certainty != "not_started")
            or self.signal == "transient_failure"
            and (
                self.run_state != "failed"
                or self.dispatch_certainty
                not in {"not_started", "response_received", "may_have_started"}
            )
            or not _utc(self.queried_at)
            or (
                self.run_requested_at is not None
                and (
                    not _utc(self.run_requested_at)
                    or self.run_requested_at > self.queried_at
                )
            )
            or (
                self.signal_observed_at is not None
                and (
                    not _utc(self.signal_observed_at)
                    or self.run_requested_at is None
                    or self.signal_observed_at < self.run_requested_at
                    or self.signal_observed_at > self.queried_at
                )
            )
            or requires_retry != (self.retry_at is not None)
            or (
                self.retry_at is not None
                and (not _utc(self.retry_at) or self.retry_at <= self.queried_at)
            )
        ):
            raise InvalidCollectionControlV1("ollama_cloud_source_signal_invalid")


@dataclass(frozen=True, slots=True)
class OllamaCloudRequestLeaseV1(TechnicalValueV1):
    """Fenced permission for one exact account request start."""

    CONTRACT_ID: ClassVar[str] = "CTR-COL-008"
    OWNER: ClassVar[str] = "PLAN-M04"

    admission_id: OpaqueIdV1
    scheduler_instance_id: OpaqueIdV1
    schedule_id: OpaqueIdV1
    account_id: OpaqueIdV1
    fencing_token: int
    started_at: datetime
    lease_expires_at: datetime
    next_allowed_at: datetime
    gate_record_version: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.fencing_token) is not int
            or self.fencing_token < 1
            or type(self.gate_record_version) is not int
            or self.gate_record_version < 1
            or not all(
                _utc(value)
                for value in (
                    self.started_at,
                    self.lease_expires_at,
                    self.next_allowed_at,
                )
            )
            or self.lease_expires_at <= self.started_at
            or self.next_allowed_at < self.started_at + timedelta(seconds=60)
        ):
            raise InvalidCollectionControlV1("ollama_cloud_lease_invalid")


@dataclass(frozen=True, slots=True)
class OllamaCloudAdmissionDecisionV1(TechnicalValueV1):
    """Closed admission result; only ``acquired`` permits provider dispatch."""

    CONTRACT_ID: ClassVar[str] = "CTR-COL-008"
    OWNER: ClassVar[str] = "PLAN-M04"

    state: OllamaCloudAdmissionDecisionStateV1
    lease: OllamaCloudRequestLeaseV1 | None
    retry_at: datetime | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        has_lease = self.state == "acquired"
        needs_retry = self.state in {
            "replayed_active",
            "replayed_terminal",
            "not_due",
            "busy",
        }
        if (
            has_lease != (self.lease is not None)
            or needs_retry != (self.retry_at is not None)
            or (self.retry_at is not None and not _utc(self.retry_at))
        ):
            raise InvalidCollectionControlV1("ollama_cloud_decision_invalid")


@dataclass(frozen=True, slots=True)
class OllamaCloudRequestCompletionV1(TechnicalValueV1):
    """Sanitized result facts used to release and advance the global gate."""

    CONTRACT_ID: ClassVar[str] = "CTR-COL-008"
    OWNER: ClassVar[str] = "PLAN-M04"

    admission_id: OpaqueIdV1
    scheduler_instance_id: OpaqueIdV1
    schedule_id: OpaqueIdV1
    fencing_token: int
    started_at: datetime
    response_received_at: datetime
    outcome: OllamaCloudAdmissionOutcomeV1
    retry_after_seconds: int | None
    jitter_seconds: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.fencing_token) is not int
            or self.fencing_token < 1
            or not _utc(self.started_at)
            or not _utc(self.response_received_at)
            or self.response_received_at < self.started_at
            or (self.outcome != "rate_limited" and self.retry_after_seconds is not None)
            or (
                self.retry_after_seconds is not None
                and (
                    type(self.retry_after_seconds) is not int
                    or not 0 <= self.retry_after_seconds <= 2**63 - 1
                )
            )
            or type(self.jitter_seconds) is not int
            or not 0 <= self.jitter_seconds <= 10
        ):
            raise InvalidCollectionControlV1("ollama_cloud_completion_invalid")


@dataclass(frozen=True, slots=True)
class OllamaCloudNoResponseCompletionV2(TechnicalValueV1):
    """Terminal result known to have sent no HTTP request; no response time."""

    CONTRACT_ID: ClassVar[str] = "CTR-COL-009"
    CONTRACT_VERSION: ClassVar[str] = "1.1.0"
    OWNER: ClassVar[str] = "PLAN-M04"
    admission_id: OpaqueIdV1
    scheduler_instance_id: OpaqueIdV1
    schedule_id: OpaqueIdV1
    fencing_token: int
    started_at: datetime
    terminal_at: datetime
    reason_code: Literal[
        "pre_dispatch_failed",
        "source_not_started",
        "store_unavailable",
        "credential_update_in_progress",
    ]
    source_state: (
        Literal[
            "authorization_unavailable",
            "deadline_exceeded",
            "provider_unavailable",
            "internal_adapter_error",
            "source_not_admitted",
        ]
        | None
    ) = None
    dispatch_certainty: Literal["not_started"] = "not_started"

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.fencing_token) is not int
            or self.fencing_token < 1
            or not _utc(self.started_at)
            or not _utc(self.terminal_at)
            or self.terminal_at < self.started_at
            or self.reason_code
            not in {
                "pre_dispatch_failed",
                "source_not_started",
                "store_unavailable",
                "credential_update_in_progress",
            }
            or self.dispatch_certainty != "not_started"
            or self.source_state
            not in {
                None,
                "authorization_unavailable",
                "deadline_exceeded",
                "provider_unavailable",
                "internal_adapter_error",
                "source_not_admitted",
            }
            or (self.reason_code == "pre_dispatch_failed")
            != (self.source_state is None)
            or (
                self.reason_code
                in {"store_unavailable", "credential_update_in_progress"}
            )
            != (self.source_state == "authorization_unavailable")
        ):
            raise InvalidCollectionControlV1("ollama_cloud_no_response_invalid")


@dataclass(frozen=True, slots=True)
class OllamaCloudRateGateViewV1(TechnicalValueV1):
    """Non-secret durable global limiter state after one transition."""

    CONTRACT_ID: ClassVar[str] = "CTR-COL-008"
    OWNER: ClassVar[str] = "PLAN-M04"

    next_allowed_at: datetime
    fair_cursor_schedule_id: OpaqueIdV1 | None
    active_admission_id: OpaqueIdV1 | None
    consecutive_rate_limits: int
    fencing_token: int
    record_version: int
    updated_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not _utc(self.next_allowed_at)
            or not _utc(self.updated_at)
            or type(self.consecutive_rate_limits) is not int
            or not 0 <= self.consecutive_rate_limits <= 100
            or type(self.fencing_token) is not int
            or self.fencing_token < 0
            or type(self.record_version) is not int
            or self.record_version < 1
        ):
            raise InvalidCollectionControlV1("ollama_cloud_gate_invalid")


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
class CollectionRunAdmissionV2(TechnicalValueV1):
    """V2 run admission using a discriminated provider target reference."""

    CONTRACT_ID: ClassVar[str] = "CTR-COL-002"
    CONTRACT_VERSION: ClassVar[str] = "2.0.0"
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
    provider_target: ProviderTargetRefV1
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
            or not isinstance(self.provider_target, ProviderTargetRefV1)
            or (
                self.provider_target.target_kind == "cloud_service"
                and (
                    self.account_id is None
                    or self.profile_id is None
                    or self.resource_id is None
                )
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


CollectionRunAdmissionV1OrV2 = CollectionRunAdmissionV1 | CollectionRunAdmissionV2


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

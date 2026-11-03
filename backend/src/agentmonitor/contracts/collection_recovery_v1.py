"""Additive M04 read-only, exact-source recovery evidence contract."""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import ClassVar, Protocol

from agentmonitor.contracts.common_v1 import OpaqueIdV1, TechnicalValueV1

_CODE = re.compile(r"[A-Za-z0-9_.:@-]{1,128}\Z")
_DIGEST = re.compile(r"[a-f0-9]{64}\Z")


def _utc(value: datetime) -> bool:
    return isinstance(value, datetime) and value.utcoffset() == timedelta(0)


@dataclass(frozen=True, slots=True)
class CollectionRecoveryScopeV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-COL-012"
    OWNER: ClassVar[str] = "PLAN-M04"

    account_id: OpaqueIdV1
    access_target_id: OpaqueIdV1
    binding_generation: int
    capability_id: str
    source_id: str
    adapter_version: str
    source_fingerprint: str
    payload_schema: str
    provider_key: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.binding_generation) is not int
            or self.binding_generation < 1
            or not _DIGEST.fullmatch(self.source_fingerprint)
            or any(
                not _CODE.fullmatch(value)
                for value in (
                    self.capability_id,
                    self.source_id,
                    self.adapter_version,
                    self.payload_schema,
                    self.provider_key,
                )
            )
        ):
            raise ValueError("collection_recovery_scope_invalid")


@dataclass(frozen=True, slots=True)
class CollectionRecoveryQueryV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-COL-012"
    OWNER: ClassVar[str] = "PLAN-M04"

    provider_key: str
    from_at: datetime
    before_at: datetime
    scope: CollectionRecoveryScopeV1 | None = None
    limit: int = 200

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not _CODE.fullmatch(self.provider_key)
            or not _utc(self.from_at)
            or not _utc(self.before_at)
            or not self.from_at < self.before_at <= self.from_at + timedelta(days=1)
            or type(self.limit) is not int
            or not 1 <= self.limit <= 500
            or self.scope is not None
            and (
                not isinstance(self.scope, CollectionRecoveryScopeV1)
                or self.scope.provider_key != self.provider_key
            )
        ):
            raise ValueError("collection_recovery_query_invalid")


@dataclass(frozen=True, slots=True)
class CollectionRecoveryRunV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-COL-012"
    OWNER: ClassVar[str] = "PLAN-M04"

    run_id: OpaqueIdV1
    provider_key: str
    account_id: OpaqueIdV1 | None
    provider_target_kind: str | None
    access_target_id: OpaqueIdV1 | None
    binding_generation: int
    capability_id: str
    source_id: str
    adapter_version: str
    source_fingerprint: str
    payload_schema: str
    requested_at: datetime
    completed_at: datetime
    state: str
    dispatch_certainty: str | None
    response_outcome: str | None
    failure_code: str | None
    payload_digest: str | None
    observation_ids: tuple[OpaqueIdV1, ...]

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.binding_generation) is not int
            or self.binding_generation < 1
            or not _utc(self.requested_at)
            or not _utc(self.completed_at)
            or self.completed_at < self.requested_at
            or self.state
            not in {
                "succeeded",
                "partial",
                "failed",
                "blocked",
                "cancelled",
                "unsupported",
            }
            or self.dispatch_certainty
            not in {None, "not_started", "may_have_started", "response_received"}
            or self.response_outcome
            not in {None, "succeeded", "failed", "rate_limited"}
            or not _DIGEST.fullmatch(self.source_fingerprint)
            or self.payload_digest is not None
            and not _DIGEST.fullmatch(self.payload_digest)
            or self.failure_code is not None
            and not _CODE.fullmatch(self.failure_code)
            or len(self.observation_ids) > 200
        ):
            raise ValueError("collection_recovery_run_invalid")


@dataclass(frozen=True, slots=True)
class CollectionRecoveryPageV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-COL-012"
    OWNER: ClassVar[str] = "PLAN-M04"

    items: tuple[CollectionRecoveryRunV1, ...]
    has_more: bool


class CollectionRecoveryQueryPortV1(Protocol):
    def read_recovery_runs(
        self, query: CollectionRecoveryQueryV1
    ) -> CollectionRecoveryPageV1: ...

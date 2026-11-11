"""CTR-REG-014: billing enrollment independent of subscription identity."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Literal, Protocol

from agentmonitor.contracts.common_v1 import OpaqueIdV1, TechnicalValueV1
from agentmonitor.contracts.registry_v1 import RegistryLifecycleV1


def _scope_valid(scope_id: str | None) -> bool:
    return scope_id is None or (
        type(scope_id) is str
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", scope_id) is not None
    )


@dataclass(frozen=True, slots=True)
class BillingConnectionViewV1(TechnicalValueV1):
    """Owner metadata, not evidence of credential access or provider identity.

    resource_id is also the connection identifier; there is no second alias.
    Scope changes advance scope_generation; credential rotation must not do so.
    Monitoring is independent from account subscription monitoring.
    """

    CONTRACT_ID: ClassVar[str] = "CTR-REG-014"
    OWNER: ClassVar[str] = "PLAN-M02"
    account_id: OpaqueIdV1
    resource_id: OpaqueIdV1
    provider_key: Literal["claude", "codex", "ollama"]
    scope_id: str | None
    scope_evidence: Literal["unresolved", "owner_asserted", "provider_verified"]
    scope_generation: int
    monitoring_preference: Literal["enabled", "disabled"]
    lifecycle: Literal["pending", "active", "disconnected"]
    record_version: int
    registry_revision: int
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not _scope_valid(self.scope_id)
            or (self.scope_id is None) != (self.scope_evidence == "unresolved")
            or any(
                type(v) is not int or v < 1
                for v in (
                    self.scope_generation,
                    self.record_version,
                    self.registry_revision,
                )
            )
            or self.updated_at < self.created_at
            or self.lifecycle != "active"
            and self.monitoring_preference != "disabled"
        ):
            raise ValueError("registry_billing_connection_invalid")


@dataclass(frozen=True, slots=True)
class BillingCredentialStatusV1(TechnicalValueV1):
    """Local lifecycle metadata only; stored never proves provider access.

    Generations describe the actual active/pending records, not the aggregate's
    revocation fence. Cleanup may remain outstanding alongside either record.
    No credential identifier, location or value is published.
    """

    CONTRACT_ID: ClassVar[str] = "CTR-REG-014"
    OWNER: ClassVar[str] = "PLAN-M02"
    state: Literal["missing", "pending", "stored", "cleanup_required"]
    active_generation: int | None
    pending_generation: int | None
    cleanup_required: bool

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        expected = (
            "pending"
            if self.pending_generation is not None
            else "stored"
            if self.active_generation is not None
            else "cleanup_required"
            if self.cleanup_required
            else "missing"
        )
        if (
            self.state != expected
            or type(self.cleanup_required) is not bool
            or any(
                value is not None and (type(value) is not int or value < 1)
                for value in (self.active_generation, self.pending_generation)
            )
            or self.active_generation is not None
            and self.pending_generation is not None
            and self.pending_generation != self.active_generation + 1
        ):
            raise ValueError("registry_billing_credential_status_invalid")


@dataclass(frozen=True, slots=True)
class AccountBillingConnectionsV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-REG-014"
    OWNER: ClassVar[str] = "PLAN-M02"
    account_id: OpaqueIdV1
    provider_key: str
    account_lifecycle: RegistryLifecycleV1
    account_record_version: int
    can_add_connection: bool
    reason_code: str
    connections: tuple[BillingConnectionViewV1, ...]
    credential_status: BillingCredentialStatusV1 | None = None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.can_add_connection) is not bool
            or type(self.account_record_version) is not int
            or self.account_record_version < 1
            or len(self.connections) > 1
            or any(
                c.account_id != self.account_id or c.provider_key != self.provider_key
                for c in self.connections
            )
            or self.can_add_connection
            and (
                bool(self.connections)
                or self.account_lifecycle in {"archived", "disabled"}
            )
        ):
            raise ValueError("registry_billing_status_invalid")


@dataclass(frozen=True, slots=True)
class CreateBillingConnectionCommandV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-REG-014"
    OWNER: ClassVar[str] = "PLAN-M02"
    account_id: OpaqueIdV1
    expected_account_version: int
    principal_id: OpaqueIdV1
    command_id: OpaqueIdV1
    scope_id: str | None
    requested_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.expected_account_version) is not int
            or self.expected_account_version < 1
            or not _scope_valid(self.scope_id)
        ):
            raise ValueError("registry_billing_command_invalid")


class BillingConnectionPortV1(Protocol):
    """Registry metadata only. No call reads a secret or contacts a provider."""

    def get(self, account_id: OpaqueIdV1) -> AccountBillingConnectionsV1 | None: ...

    def create(
        self, command: CreateBillingConnectionCommandV1
    ) -> BillingConnectionViewV1: ...


@dataclass(frozen=True, slots=True)
class BillingLocalSetupV1(TechnicalValueV1):
    """Nonsecret owner command for the service host; never a browser key input."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-014"
    OWNER: ClassVar[str] = "PLAN-M02"
    host_label: str
    command: str


class BillingLocalSetupPortV1(Protocol):
    """Composition supplies installation context, independently of registry storage."""

    def describe(
        self, status: AccountBillingConnectionsV1
    ) -> BillingLocalSetupV1 | None: ...

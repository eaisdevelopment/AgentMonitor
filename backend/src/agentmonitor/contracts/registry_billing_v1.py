"""CTR-REG-014: billing enrollment independent of subscription identity."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Literal, Protocol

from agentmonitor.contracts.common_v1 import (
    OpaqueIdV1,
    QueryAvailabilityV1,
    TechnicalValueV1,
)
from agentmonitor.contracts.registry_v1 import (
    ActiveCredentialBindingRefV1,
    RegistryLifecycleV1,
)


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


BillingAccessPurposeV1 = Literal["verification", "monitoring"]


@dataclass(frozen=True, slots=True)
class BillingAccessTargetV1(TechnicalValueV1):
    """Profile-free current authority, resolved by M02 before use and commit.

    No credential, provider permission proof or subscription state is carried.
    Verification can precede enabling billing monitoring. The connection captures
    resource identity, scope generation and the independent billing lifecycle.
    """

    CONTRACT_ID: ClassVar[str] = "CTR-REG-014"
    CONTRACT_VERSION: ClassVar[str] = "1.3.0"
    OWNER: ClassVar[str] = "PLAN-M02"
    connection: BillingConnectionViewV1
    binding: ActiveCredentialBindingRefV1
    purpose: BillingAccessPurposeV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not isinstance(self.connection, BillingConnectionViewV1)
            or not isinstance(self.binding, ActiveCredentialBindingRefV1)
            or self.connection.account_id != self.binding.account_id
        ):
            raise ValueError("billing_binding_mismatch")
        if self.connection.lifecycle not in {"pending", "active"}:
            raise ValueError("billing_connection_unavailable")
        if self.purpose == "monitoring" and (
            self.connection.lifecycle != "active"
            or self.connection.monitoring_preference != "enabled"
        ):
            raise ValueError("billing_monitoring_disabled")


class BillingAccessPortV1(Protocol):
    """Safe current-target lookup only; no secret read and no provider request."""

    def resolve(
        self,
        account_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
        purpose: BillingAccessPurposeV1,
    ) -> BillingAccessTargetV1 | None: ...


@dataclass(frozen=True, slots=True)
class SetBillingMonitoringCommandV1(TechnicalValueV1):
    """Owner intent; enabling is fenced to the displayed verification generation."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-014"
    CONTRACT_VERSION: ClassVar[str] = "1.4.0"
    OWNER: ClassVar[str] = "PLAN-M02"
    account_id: OpaqueIdV1
    resource_id: OpaqueIdV1
    expected_account_version: int
    expected_connection_version: int
    expected_scope_generation: int
    expected_binding_generation: int | None
    monitoring_preference: Literal["enabled", "disabled"]
    verified_run_id: OpaqueIdV1 | None
    principal_id: OpaqueIdV1
    command_id: OpaqueIdV1
    requested_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            any(
                type(value) is not int or value < 1
                for value in (
                    self.expected_account_version,
                    self.expected_connection_version,
                    self.expected_scope_generation,
                )
            )
            or self.expected_binding_generation is not None
            and (
                type(self.expected_binding_generation) is not int
                or self.expected_binding_generation < 1
            )
            or self.monitoring_preference == "enabled"
            and (
                self.expected_binding_generation is None
                or not isinstance(self.verified_run_id, OpaqueIdV1)
            )
            or self.monitoring_preference == "disabled"
            and self.verified_run_id is not None
        ):
            raise ValueError("billing_monitoring_command_invalid")


@dataclass(frozen=True, slots=True)
class BillingMonitoringProofV1(TechnicalValueV1):
    """Internal evidence assembled from genuine M04/M05 records, never HTTP input.

    current_target is freshly resolved after comparing the immutable report's
    captured binding/scope. It is rechecked in the M02 mutation transaction.
    """

    CONTRACT_ID: ClassVar[str] = "CTR-REG-014"
    CONTRACT_VERSION: ClassVar[str] = "1.4.0"
    OWNER: ClassVar[str] = "PLAN-M02"
    current_target: BillingAccessTargetV1
    run_id: OpaqueIdV1
    report_id: OpaqueIdV1
    payload_digest: str
    verified_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not isinstance(self.current_target, BillingAccessTargetV1)
            or self.current_target.purpose != "verification"
            or not isinstance(self.run_id, OpaqueIdV1)
            or not isinstance(self.report_id, OpaqueIdV1)
            or type(self.payload_digest) is not str
            or re.fullmatch(r"[a-f0-9]{64}", self.payload_digest) is None
            or not isinstance(self.verified_at, datetime)
        ):
            raise ValueError("billing_monitoring_proof_invalid")


class BillingMonitoringRegistryPortV1(Protocol):
    """Atomic metadata mutation; the composition supplies verified lineage."""

    def replay_monitoring(
        self, command: SetBillingMonitoringCommandV1
    ) -> BillingConnectionViewV1 | None: ...

    def set_monitoring(
        self,
        command: SetBillingMonitoringCommandV1,
        proof: BillingMonitoringProofV1 | None,
    ) -> BillingConnectionViewV1: ...


@dataclass(frozen=True, slots=True)
class BillingMonitoringStatusV1(TechnicalValueV1):
    """Current server-derived eligibility; never a browser-cached access claim."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-014"
    CONTRACT_VERSION: ClassVar[str] = "1.4.0"
    OWNER: ClassVar[str] = "PLAN-M02"
    connection: BillingConnectionViewV1
    account_record_version: int
    binding_generation: int | None
    can_enable: bool
    can_disable: bool
    reason_code: str
    verified_run_id: OpaqueIdV1 | None
    verified_at: datetime | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not isinstance(self.connection, BillingConnectionViewV1)
            or type(self.account_record_version) is not int
            or self.account_record_version < 1
            or self.binding_generation is not None
            and (
                type(self.binding_generation) is not int or self.binding_generation < 1
            )
            or type(self.can_enable) is not bool
            or type(self.can_disable) is not bool
            or self.can_enable
            and self.can_disable
            or self.can_enable
            and (
                self.verified_run_id is None
                or self.binding_generation is None
                or self.connection.monitoring_preference != "disabled"
            )
            or self.can_disable
            and self.connection.monitoring_preference != "enabled"
            or (self.verified_run_id is None) != (self.verified_at is None)
            or re.fullmatch(r"[a-z][a-z0-9_]{0,95}", self.reason_code) is None
        ):
            raise ValueError("billing_monitoring_status_invalid")


class BillingMonitoringPortV1(Protocol):
    """Safe current eligibility and proof-backed owner actions through composition."""

    def get_status(
        self, account_id: OpaqueIdV1, resource_id: OpaqueIdV1
    ) -> BillingMonitoringStatusV1 | None: ...

    def set_monitoring(
        self, command: SetBillingMonitoringCommandV1
    ) -> BillingConnectionViewV1: ...


@dataclass(frozen=True, slots=True)
class FinancialResourceScopeV1(TechnicalValueV1):
    """Source identity covered by an association, never a credential value.

    Unresolved identities are binding-specific. A known stable provider scope
    has no binding dependency; rotating its credential does not rename the pool.
    Existing cloud resources keep their own IDs rather than billing duplicates.
    """

    CONTRACT_ID: ClassVar[str] = "CTR-REG-014"
    CONTRACT_VERSION: ClassVar[str] = "1.5.0"
    OWNER: ClassVar[str] = "PLAN-M02"
    account_id: OpaqueIdV1
    resource_id: OpaqueIdV1
    provider_key: Literal["claude", "codex", "ollama"]
    selector: Literal["billing", "self", "team"]
    scope_generation: int
    provider_scope_id: str | None
    scope_evidence: Literal["unresolved", "owner_asserted", "provider_verified"]
    binding_id: OpaqueIdV1 | None
    binding_generation: int | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        unresolved = self.scope_evidence == "unresolved"
        if (
            not isinstance(self.account_id, OpaqueIdV1)
            or not isinstance(self.resource_id, OpaqueIdV1)
            or self.provider_key not in {"claude", "codex", "ollama"}
            or self.selector not in {"billing", "self", "team"}
            or (self.provider_key == "ollama") != (self.selector != "billing")
            or type(self.scope_generation) is not int
            or self.scope_generation < 1
            or self.scope_evidence
            not in {"unresolved", "owner_asserted", "provider_verified"}
            or not _scope_valid(self.provider_scope_id)
            or (self.provider_scope_id is None) != unresolved
            or unresolved
            and (
                not isinstance(self.binding_id, OpaqueIdV1)
                or type(self.binding_generation) is not int
                or self.binding_generation < 1
            )
            or not unresolved
            and (self.binding_id is not None or self.binding_generation is not None)
        ):
            raise ValueError("financial_resource_scope_invalid")


@dataclass(frozen=True, slots=True)
class FinancialPoolViewV1(TechnicalValueV1):
    """Canonical pool identity and explicit primary dashboard attribution."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-014"
    CONTRACT_VERSION: ClassVar[str] = "1.5.0"
    OWNER: ClassVar[str] = "PLAN-M02"
    pool_id: OpaqueIdV1
    provider_key: Literal["claude", "codex", "ollama"]
    primary_organization_id: OpaqueIdV1 | None
    record_version: int
    registry_revision: int
    created_at: datetime
    updated_at: datetime
    display_name: str
    selector: Literal["billing", "self", "team"]

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not isinstance(self.pool_id, OpaqueIdV1)
            or self.provider_key not in {"claude", "codex", "ollama"}
            or self.primary_organization_id is not None
            and not isinstance(self.primary_organization_id, OpaqueIdV1)
            or any(
                type(value) is not int or value < 1
                for value in (self.record_version, self.registry_revision)
            )
            or self.updated_at < self.created_at
            or (self.provider_key == "ollama") != (self.selector != "billing")
            or type(self.display_name) is not str
            or not 1 <= len(self.display_name.strip()) <= 256
        ):
            raise ValueError("financial_pool_invalid")


@dataclass(frozen=True, slots=True)
class FinancialPoolMembershipV1(TechnicalValueV1):
    """Immutable association epoch; owner assertion is not verified access."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-014"
    CONTRACT_VERSION: ClassVar[str] = "1.5.0"
    OWNER: ClassVar[str] = "PLAN-M02"
    association_id: OpaqueIdV1
    scope: FinancialResourceScopeV1
    pool_id: OpaqueIdV1
    association_evidence: Literal["owner_asserted", "provider_verified"]
    valid_from: datetime
    valid_until: datetime | None
    record_version: int
    registry_revision: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not isinstance(self.association_id, OpaqueIdV1)
            or not isinstance(self.scope, FinancialResourceScopeV1)
            or not isinstance(self.pool_id, OpaqueIdV1)
            or self.association_evidence not in {"owner_asserted", "provider_verified"}
            or self.valid_until is not None
            and self.valid_until <= self.valid_from
            or any(
                type(value) is not int or value < 1
                for value in (self.record_version, self.registry_revision)
            )
        ):
            raise ValueError("financial_pool_membership_invalid")


@dataclass(frozen=True, slots=True)
class FinancialPoolSnapshotV1(TechnicalValueV1):
    """Bounded atomic metadata; missing memberships mean unresolved, not zero."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-014"
    CONTRACT_VERSION: ClassVar[str] = "1.5.0"
    OWNER: ClassVar[str] = "PLAN-M02"
    resource_ids: tuple[OpaqueIdV1, ...]
    pools: tuple[FinancialPoolViewV1, ...]
    memberships: tuple[FinancialPoolMembershipV1, ...]
    registry_revision: int
    as_of: datetime
    availability: QueryAvailabilityV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        pools = {pool.pool_id: pool for pool in self.pools}
        keys = {
            (member.scope.resource_id, member.scope.selector)
            for member in self.memberships
        }
        if (
            len(self.resource_ids) > 2000
            or len(set(self.resource_ids)) != len(self.resource_ids)
            or any(not isinstance(value, OpaqueIdV1) for value in self.resource_ids)
            or len(pools) != len(self.pools)
            or len(keys) != len(self.memberships)
            or len(self.pools) > 2000
            or len(self.memberships) > 4000
            or type(self.registry_revision) is not int
            or self.registry_revision < 0
            or self.availability.as_of != self.as_of
            or self.availability.state not in {"available", "unavailable"}
            or self.availability.state != "available"
            and bool(self.pools or self.memberships)
            or any(
                pool.registry_revision > self.registry_revision
                or pool.updated_at > self.as_of
                for pool in self.pools
            )
            or any(
                member.scope.resource_id not in self.resource_ids
                or member.pool_id not in pools
                or pools[member.pool_id].provider_key != member.scope.provider_key
                or pools[member.pool_id].selector != member.scope.selector
                or member.registry_revision > self.registry_revision
                or member.valid_from > self.as_of
                or member.valid_until is not None
                and member.valid_until <= self.as_of
                for member in self.memberships
            )
        ):
            raise ValueError("financial_pool_snapshot_invalid")


class FinancialPoolReadPortV1(Protocol):
    """Resolve only requested resources, checking their atomic registry revision."""

    def __call__(
        self,
        resource_ids: tuple[OpaqueIdV1, ...],
        *,
        expected_registry_revision: int,
        as_of: datetime,
    ) -> FinancialPoolSnapshotV1: ...


@dataclass(frozen=True, slots=True)
class AssignFinancialPoolCommandV1(TechnicalValueV1):
    """Owner association; source authority is resolved server-side, not HTTP input."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-014"
    CONTRACT_VERSION: ClassVar[str] = "1.5.0"
    OWNER: ClassVar[str] = "PLAN-M02"
    scope: FinancialResourceScopeV1
    expected_registry_revision: int
    action: Literal["create", "join", "unlink"]
    pool_id: OpaqueIdV1 | None
    primary_organization_id: OpaqueIdV1 | None
    principal_id: OpaqueIdV1
    command_id: OpaqueIdV1
    requested_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not isinstance(self.scope, FinancialResourceScopeV1)
            or type(self.expected_registry_revision) is not int
            or self.expected_registry_revision < 1
            or (self.action == "join") != isinstance(self.pool_id, OpaqueIdV1)
            or self.action != "join"
            and self.pool_id is not None
            or self.action != "create"
            and self.primary_organization_id is not None
            or self.primary_organization_id is not None
            and not isinstance(self.primary_organization_id, OpaqueIdV1)
        ):
            raise ValueError("financial_pool_command_invalid")


@dataclass(frozen=True, slots=True)
class EditFinancialPoolCommandV1(TechnicalValueV1):
    """Change attribution only; no credential, source, monitoring or report edit."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-014"
    CONTRACT_VERSION: ClassVar[str] = "1.5.0"
    OWNER: ClassVar[str] = "PLAN-M02"
    pool_id: OpaqueIdV1
    expected_record_version: int
    expected_registry_revision: int
    primary_organization_id: OpaqueIdV1 | None
    principal_id: OpaqueIdV1
    command_id: OpaqueIdV1
    requested_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not isinstance(self.pool_id, OpaqueIdV1)
            or any(
                type(value) is not int or value < 1
                for value in (
                    self.expected_record_version,
                    self.expected_registry_revision,
                )
            )
            or self.primary_organization_id is not None
            and not isinstance(self.primary_organization_id, OpaqueIdV1)
        ):
            raise ValueError("financial_pool_command_invalid")


@dataclass(frozen=True, slots=True)
class FinancialPoolConfigurationV1(TechnicalValueV1):
    """Current metadata; unresolved identity is usable only with an active binding.

    scope may be absent while credentials or the resource are unavailable.
    Old associations remain stored but are not current authority after rotation.
    """

    CONTRACT_ID: ClassVar[str] = "CTR-REG-014"
    CONTRACT_VERSION: ClassVar[str] = "1.5.0"
    OWNER: ClassVar[str] = "PLAN-M02"
    account_id: OpaqueIdV1
    resource_id: OpaqueIdV1
    selector: Literal["billing", "self", "team"]
    scope: FinancialResourceScopeV1 | None
    membership: FinancialPoolMembershipV1 | None
    pool: FinancialPoolViewV1 | None
    registry_revision: int
    reason_code: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.registry_revision) is not int
            or self.registry_revision < 1
            or (self.membership is None) != (self.pool is None)
            or self.scope is not None
            and (
                self.scope.account_id != self.account_id
                or self.scope.resource_id != self.resource_id
                or self.scope.selector != self.selector
            )
            or self.membership is not None
            and (
                self.membership.scope != self.scope
                or self.pool is None
                or self.membership.pool_id != self.pool.pool_id
                or self.pool.provider_key != self.membership.scope.provider_key
                or self.pool.selector != self.membership.scope.selector
                or self.membership.valid_until is not None
            )
            or re.fullmatch(r"[a-z][a-z0-9_]{0,95}", self.reason_code) is None
        ):
            raise ValueError("financial_pool_configuration_invalid")


@dataclass(frozen=True, slots=True)
class FinancialPoolPageV1(TechnicalValueV1):
    """Bounded same-provider choices, ordered by opaque pool ID, revision-fenced."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-014"
    CONTRACT_VERSION: ClassVar[str] = "1.5.0"
    OWNER: ClassVar[str] = "PLAN-M02"
    pools: tuple[FinancialPoolViewV1, ...]
    next_pool_id: OpaqueIdV1 | None
    registry_revision: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            len(self.pools) > 200
            or len({p.pool_id for p in self.pools}) != len(self.pools)
            or type(self.registry_revision) is not int
            or self.registry_revision < 0
            or any(p.registry_revision > self.registry_revision for p in self.pools)
            or self.next_pool_id is not None
            and (not self.pools or self.pools[-1].pool_id != self.next_pool_id)
        ):
            raise ValueError("financial_pool_page_invalid")


class FinancialPoolRegistryPortV1(FinancialPoolReadPortV1, Protocol):
    """M02-only metadata. No secret reads, provider requests or automatic setup."""

    def get_configuration(
        self,
        account_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
        selector: Literal["billing", "self", "team"],
    ) -> FinancialPoolConfigurationV1 | None: ...

    def list_pools(
        self,
        provider_key: Literal["claude", "codex", "ollama"],
        *,
        limit: int = 50,
        after: OpaqueIdV1 | None = None,
        expected_registry_revision: int | None = None,
    ) -> FinancialPoolPageV1: ...

    def assign(
        self, command: AssignFinancialPoolCommandV1
    ) -> FinancialPoolConfigurationV1: ...

    def edit(self, command: EditFinancialPoolCommandV1) -> FinancialPoolViewV1: ...

"""M02 owner-declared organization coverage, independent of credential access."""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Literal, Protocol

from agentmonitor.contracts.common_v1 import OpaqueIdV1, TechnicalValueV1

CoverageOutcomeV1 = Literal["account", "shared", "unavailable"]
CoverageUnavailableReasonV1 = Literal[
    "account_unavailable",
    "subscription_unavailable",
    "access_unavailable",
    "owner_unavailable",
]
CoverageInvalidationReasonV1 = Literal[
    "owner_revoked",
    "account_archived",
    "account_reassigned",
    "organization_archived",
    "source_organization_archived",
    "provider_withdrawn",
]
_UNAVAILABLE = frozenset(
    {
        "account_unavailable",
        "subscription_unavailable",
        "access_unavailable",
        "owner_unavailable",
    }
)
_INVALIDATION = frozenset(
    {
        "owner_revoked",
        "account_archived",
        "account_reassigned",
        "organization_archived",
        "source_organization_archived",
        "provider_withdrawn",
    }
)


def _key_valid(organization_id: OpaqueIdV1, provider_key: str) -> bool:
    return (
        isinstance(organization_id, OpaqueIdV1)
        and isinstance(provider_key, str)
        and 1 <= len(provider_key) <= 64
        and provider_key.isascii()
        and provider_key.replace("-", "").replace("_", "").isalnum()
    )


def _shape_valid(
    outcome: CoverageOutcomeV1,
    account_id: OpaqueIdV1 | None,
    unavailable_reason: CoverageUnavailableReasonV1 | None,
) -> bool:
    if outcome == "unavailable":
        return account_id is None and unavailable_reason in _UNAVAILABLE
    return (
        outcome in {"account", "shared"}
        and isinstance(account_id, OpaqueIdV1)
        and unavailable_reason is None
    )


@dataclass(frozen=True, slots=True)
class SetOrganizationProviderCoverageCommandV1(TechnicalValueV1):
    """A versioned owner assertion; authenticated identity/time are server-derived."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-013"
    OWNER: ClassVar[str] = "PLAN-M02"

    organization_id: OpaqueIdV1
    provider_key: str
    outcome: CoverageOutcomeV1
    account_id: OpaqueIdV1 | None
    expected_account_record_version: int | None
    unavailable_reason: CoverageUnavailableReasonV1 | None
    expected_version: int
    command_id: OpaqueIdV1
    principal_id: OpaqueIdV1
    requested_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        account_version_valid = (
            self.expected_account_record_version is None
            if self.account_id is None
            else type(self.expected_account_record_version) is int
            and self.expected_account_record_version >= 1
        )
        if (
            not _key_valid(self.organization_id, self.provider_key)
            or not _shape_valid(self.outcome, self.account_id, self.unavailable_reason)
            or not account_version_valid
            or type(self.expected_version) is not int
            or self.expected_version < 0
            or not isinstance(self.command_id, OpaqueIdV1)
            or not isinstance(self.principal_id, OpaqueIdV1)
            or not isinstance(self.requested_at, datetime)
        ):
            raise ValueError("registry_coverage_command_invalid")


@dataclass(frozen=True, slots=True)
class RevokeOrganizationProviderCoverageCommandV1(TechnicalValueV1):
    """Revoke a retained assertion; version zero cannot delete or reset a record."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-013"
    OWNER: ClassVar[str] = "PLAN-M02"

    organization_id: OpaqueIdV1
    provider_key: str
    expected_version: int
    command_id: OpaqueIdV1
    principal_id: OpaqueIdV1
    requested_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not _key_valid(self.organization_id, self.provider_key)
            or type(self.expected_version) is not int
            or self.expected_version < 1
            or not isinstance(self.command_id, OpaqueIdV1)
            or not isinstance(self.principal_id, OpaqueIdV1)
            or not isinstance(self.requested_at, datetime)
        ):
            raise ValueError("registry_coverage_command_invalid")


@dataclass(frozen=True, slots=True)
class OrganizationProviderCoverageV1(TechnicalValueV1):
    """Retained owner declaration; it cannot certify provider identity or balance."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-013"
    OWNER: ClassVar[str] = "PLAN-M02"

    coverage_id: OpaqueIdV1
    organization_id: OpaqueIdV1
    provider_key: str
    outcome: CoverageOutcomeV1
    account_id: OpaqueIdV1 | None
    account_organization_id: OpaqueIdV1 | None
    unavailable_reason: CoverageUnavailableReasonV1 | None
    provenance: Literal["owner_asserted"]
    confirmed_by: OpaqueIdV1
    confirmed_at: datetime
    record_version: int
    registry_revision: int
    invalidated_at: datetime | None
    invalidation_reason: CoverageInvalidationReasonV1 | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not isinstance(self.coverage_id, OpaqueIdV1)
            or not _key_valid(self.organization_id, self.provider_key)
            or not _shape_valid(self.outcome, self.account_id, self.unavailable_reason)
            or (self.outcome == "unavailable") != (self.account_organization_id is None)
            or self.account_organization_id is not None
            and not isinstance(self.account_organization_id, OpaqueIdV1)
            or self.outcome == "account"
            and self.account_organization_id != self.organization_id
            or self.outcome == "shared"
            and self.account_organization_id == self.organization_id
            or not isinstance(self.confirmed_by, OpaqueIdV1)
            or not isinstance(self.confirmed_at, datetime)
            or type(self.record_version) is not int
            or self.record_version < 1
            or type(self.registry_revision) is not int
            or self.registry_revision < 1
            or (self.invalidated_at is None) != (self.invalidation_reason is None)
            or self.invalidation_reason is not None
            and self.invalidation_reason not in _INVALIDATION
            or self.invalidated_at is not None
            and not isinstance(self.invalidated_at, datetime)
            or self.invalidated_at is not None
            and self.invalidated_at < self.confirmed_at
        ):
            raise ValueError("registry_coverage_record_invalid")


@dataclass(frozen=True, slots=True)
class OrganizationProviderCoverageSelectionV1(TechnicalValueV1):
    """An explicit bounded intended scope; absence must not shrink this selection."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-013"
    OWNER: ClassVar[str] = "PLAN-M02"

    organization_ids: tuple[OpaqueIdV1, ...]
    provider_key: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not 1 <= len(self.organization_ids) <= 200
            or len(set(self.organization_ids)) != len(self.organization_ids)
            or not all(
                _key_valid(item, self.provider_key) for item in self.organization_ids
            )
        ):
            raise ValueError("registry_coverage_selection_invalid")


@dataclass(frozen=True, slots=True)
class OrganizationProviderCoverageSnapshotV1(TechnicalValueV1):
    """One consistent registry read, including the unchanged intended selection."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-013"
    OWNER: ClassVar[str] = "PLAN-M02"

    selection: OrganizationProviderCoverageSelectionV1
    items: tuple[OrganizationProviderCoverageV1, ...]
    registry_revision: int
    completeness: Literal["complete", "unavailable"]
    as_of: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not isinstance(self.selection, OrganizationProviderCoverageSelectionV1)
            or not isinstance(self.as_of, datetime)
            or not isinstance(self.items, tuple)
            or not all(
                isinstance(item, OrganizationProviderCoverageV1) for item in self.items
            )
        ):
            raise ValueError("registry_coverage_snapshot_invalid")
        ordered_ids = tuple(
            organization_id
            for organization_id in self.selection.organization_ids
            if any(item.organization_id == organization_id for item in self.items)
        )
        if (
            tuple(item.organization_id for item in self.items) != ordered_ids
            or type(self.registry_revision) is not int
            or self.registry_revision < 0
            or len({item.organization_id for item in self.items}) != len(self.items)
            or self.completeness == "unavailable"
            and bool(self.items)
            or any(
                item.organization_id not in self.selection.organization_ids
                or item.provider_key != self.selection.provider_key
                or item.registry_revision > self.registry_revision
                or item.confirmed_at > self.as_of
                or item.invalidated_at is not None
                and item.invalidated_at > self.as_of
                for item in self.items
            )
        ):
            raise ValueError("registry_coverage_snapshot_invalid")


class OrganizationProviderCoverageReadPortV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-REG-013"
    OWNER: ClassVar[str] = "PLAN-M02"

    def read_coverage(
        self, selection: OrganizationProviderCoverageSelectionV1
    ) -> OrganizationProviderCoverageSnapshotV1: ...


class OrganizationProviderCoverageWritePortV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-REG-013"
    OWNER: ClassVar[str] = "PLAN-M02"

    def set_coverage(
        self, command: SetOrganizationProviderCoverageCommandV1
    ) -> OrganizationProviderCoverageV1: ...

    def revoke_coverage(
        self, command: RevokeOrganizationProviderCoverageCommandV1
    ) -> OrganizationProviderCoverageV1: ...

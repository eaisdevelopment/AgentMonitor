"""M02 organization use cases over the production registry repository port."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal, Protocol

from agentmonitor.contracts.common_v1 import (
    OpaqueIdV1,
    QueryAvailabilityV1,
    QueryPageV1,
    TechnicalValueV1,
)
from agentmonitor.contracts.registry_v1 import (
    OrganizationOrderingViewV1,
    OrganizationViewV1,
)
from agentmonitor.modules.registry.application.accounts import (
    RegistryQueryUnavailableV1,
)
from agentmonitor.modules.registry.domain.names import normalize_registry_name


class RegistryCommandConflictV1(ValueError):
    """Stable mutation conflict without submitted metadata."""


@dataclass(frozen=True, slots=True)
class CreateOrganizationCommandV1(TechnicalValueV1):
    command_id: OpaqueIdV1
    principal_id: OpaqueIdV1
    name: str
    description: str | None
    requested_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        normalized = normalize_registry_name(self.name)
        if normalized != self.name or (
            self.description is not None
            and (
                self.description != self.description.strip()
                or not 1 <= len(self.description) <= 1024
                or not self.description.isprintable()
            )
        ):
            raise ValueError("registry_invalid_name")


@dataclass(frozen=True, slots=True)
class EditOrganizationCommandV1:
    organization_id: OpaqueIdV1
    expected_version: int
    principal_id: OpaqueIdV1
    command_id: OpaqueIdV1
    action: Literal["rename", "archive", "restore"]
    requested_at: datetime
    name: str | None = None

    def __post_init__(self) -> None:
        if (
            type(self.expected_version) is not int
            or self.expected_version < 1
            or (self.action == "rename") != (self.name is not None)
            or (
                self.name is not None
                and normalize_registry_name(self.name) != self.name
            )
            or self.requested_at.utcoffset() != timedelta(0)
        ):
            raise ValueError("registry_edit_organization_command_invalid")


@dataclass(frozen=True, slots=True)
class ReorderOrganizationsCommandV1:
    ordered_organization_ids: tuple[OpaqueIdV1, ...]
    expected_registry_revision: int
    principal_id: OpaqueIdV1
    command_id: OpaqueIdV1
    requested_at: datetime

    def __post_init__(self) -> None:
        if (
            not 1 <= len(self.ordered_organization_ids) <= 500
            or len(set(self.ordered_organization_ids))
            != len(self.ordered_organization_ids)
            or type(self.expected_registry_revision) is not int
            or self.expected_registry_revision < 1
            or self.requested_at.utcoffset() != timedelta(0)
        ):
            raise ValueError("registry_reorder_command_invalid")


class OrganizationRepositoryPortV1(Protocol):
    def create_organization(
        self, command: CreateOrganizationCommandV1
    ) -> OrganizationViewV1: ...

    def list_organizations(
        self, page_size: int = 100, after_key: str | None = None
    ) -> tuple[OrganizationViewV1, ...]: ...

    def get_organization(
        self, organization_id: OpaqueIdV1
    ) -> OrganizationViewV1 | None: ...

    def edit_organization(
        self, command: EditOrganizationCommandV1
    ) -> OrganizationViewV1: ...

    def reorder_organizations(
        self, command: ReorderOrganizationsCommandV1
    ) -> OrganizationOrderingViewV1: ...


class CreateOrganizationV1:
    def __init__(self, repository: OrganizationRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(self, command: CreateOrganizationCommandV1) -> OrganizationViewV1:
        return self._repository.create_organization(command)


class ListOrganizationsV1:
    def __init__(self, repository: OrganizationRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(self) -> tuple[OrganizationViewV1, ...]:
        return self._repository.list_organizations()

    def page(
        self, *, as_of: datetime, limit: int, after_key: str | None = None
    ) -> QueryPageV1[OrganizationViewV1]:
        try:
            rows = self._repository.list_organizations(limit + 1, after_key)
        except ValueError:
            raise RegistryQueryUnavailableV1("registry_query_unavailable") from None
        has_more = len(rows) > limit
        items = rows[:limit]
        return QueryPageV1(
            items,
            limit,
            has_more,
            items[-1].organization_id.value if has_more else None,
            QueryAvailabilityV1("available", "registry_query_complete", as_of),
        )


class GetOrganizationV1:
    def __init__(self, repository: OrganizationRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(self, organization_id: OpaqueIdV1) -> OrganizationViewV1 | None:
        return self._repository.get_organization(organization_id)


class EditOrganizationV1:
    def __init__(self, repository: OrganizationRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(self, command: EditOrganizationCommandV1) -> OrganizationViewV1:
        return self._repository.edit_organization(command)


class ReorderOrganizationsV1:
    def __init__(self, repository: OrganizationRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(
        self, command: ReorderOrganizationsCommandV1
    ) -> OrganizationOrderingViewV1:
        return self._repository.reorder_organizations(command)

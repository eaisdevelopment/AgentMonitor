"""M02 organization use cases over the production registry repository port."""

import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from agentmonitor.contracts.common_v1 import OpaqueIdV1, TechnicalValueV1
from agentmonitor.contracts.registry_v1 import OrganizationViewV1


class RegistryCommandConflictV1(ValueError):
    """Stable mutation conflict without submitted metadata."""


def normalize_registry_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    if (
        not normalized
        or len(normalized) > 256
        or not normalized.isprintable()
        or any(unicodedata.category(character) == "Cc" for character in normalized)
    ):
        raise ValueError("registry_invalid_name")
    return normalized


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


class OrganizationRepositoryPortV1(Protocol):
    def create_organization(
        self, command: CreateOrganizationCommandV1
    ) -> OrganizationViewV1: ...

    def list_organizations(self) -> tuple[OrganizationViewV1, ...]: ...


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

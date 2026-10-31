"""Safe wire models for M02 registry query ports."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _ClosedV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AvailabilityV1(_ClosedV1):
    state: Literal["available", "partial", "unavailable", "unsupported", "unknown"]
    reason_code: str
    as_of: datetime


class PageMetaV1(_ClosedV1):
    limit: int
    next_cursor: str | None
    has_more: bool


class MaskedRegistryFieldWireV1(_ClosedV1):
    state: Literal["known_masked", "withheld", "unknown", "unsupported", "unavailable"]
    masked_value: str | None
    reason_code: str


class AccountViewV1(_ClosedV1):
    account_id: str
    provider_key: str
    friendly_name: str
    organization_id: str | None
    lifecycle: Literal["pending", "active", "disabled", "archived"]
    monitoring_preference: Literal["enabled", "disabled"]
    is_effective_monitoring_enabled: bool
    effective_monitoring_reason: str
    identity_state: Literal[
        "matched",
        "owner_confirmation_required",
        "owner_confirmed",
        "unresolved",
        "conflict",
        "wrong_account",
        "invalidated",
        "unsupported",
        "unknown",
    ]
    masked_identity: MaskedRegistryFieldWireV1
    record_version: int
    registry_revision: int
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class AccountPageV1(_ClosedV1):
    items: tuple[AccountViewV1, ...]
    page: PageMetaV1
    availability: AvailabilityV1


class RegisterAccountInputV1(_ClosedV1):
    provider_key: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    friendly_name: str = Field(min_length=1, max_length=256)
    organization_id: str | None = Field(default=None, min_length=1, max_length=64)


class RenameAccountInputV1(_ClosedV1):
    friendly_name: str = Field(min_length=1, max_length=256)


class AssignAccountOrganizationInputV1(_ClosedV1):
    organization_id: str | None = Field(default=None, min_length=1, max_length=64)


class SetAccountMonitoringInputV1(_ClosedV1):
    monitoring_preference: Literal["enabled", "disabled"]


class ArchiveAccountInputV1(_ClosedV1):
    pass


class OrganizationViewV1(_ClosedV1):
    organization_id: str
    name: str
    description: str | None
    display_order: int
    lifecycle: Literal["active", "archived"]
    active_account_count: int
    archived_account_count: int
    record_version: int
    registry_revision: int
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class OrganizationPageV1(_ClosedV1):
    items: tuple[OrganizationViewV1, ...]
    page: PageMetaV1
    availability: AvailabilityV1


class OrganizationOrderingViewV1(_ClosedV1):
    organization_ids: tuple[str, ...]
    registry_revision: int


class ReorderOrganizationsInputV1(_ClosedV1):
    ordered_organization_ids: tuple[str, ...] = Field(min_length=1, max_length=500)
    expected_registry_revision: int = Field(ge=1)


class CreateOrganizationInputV1(_ClosedV1):
    name: str = Field(min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=1024)


class RenameOrganizationInputV1(_ClosedV1):
    name: str = Field(min_length=1, max_length=256)


class ArchiveOrganizationInputV1(_ClosedV1):
    pass


class ProviderInstallationViewV1(_ClosedV1):
    provider_installation_id: str
    provider_key: str
    platform_key: str
    version: MaskedRegistryFieldWireV1
    presence_state: Literal["present", "missing", "unverified"]
    first_seen_at: datetime
    last_seen_at: datetime
    record_version: int
    registry_revision: int


class ProviderInstallationPageV1(_ClosedV1):
    items: tuple[ProviderInstallationViewV1, ...]
    page: PageMetaV1
    availability: AvailabilityV1

"""Safe wire models for M02 registry query ports."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


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

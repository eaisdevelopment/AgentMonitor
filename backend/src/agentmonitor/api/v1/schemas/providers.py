"""Safe wire models for the accepted M03 capability manifest."""

from datetime import datetime
from typing import Literal

from agentmonitor.api.v1.schemas.registry import AvailabilityV1
from agentmonitor.contracts.provider_system_v1 import ProviderConnectionStateV1
from agentmonitor.contracts.registry_v1 import CredentialConnectionStateV1
from pydantic import BaseModel, ConfigDict, Field


class _ClosedV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LocalCatalogItemViewV1(_ClosedV1):
    name: str = Field(min_length=1, max_length=256)


class OllamaLocalCatalogViewV1(_ClosedV1):
    outcome: Literal[
        "success",
        "partial",
        "provider_unavailable",
        "unverified_provider_version",
        "invalid_provider_data",
        "deadline_exceeded",
    ]
    daemon_version: str | None
    source: Literal["ollama.local.catalog.v1"]
    observed_at: datetime
    installed_state: Literal["available", "unavailable"]
    installed_reason: Literal[
        "source_available",
        "source_unavailable",
        "invalid_provider_data",
        "unverified_provider_version",
        "collection_in_progress",
        "operation_deadline_exceeded",
    ]
    installed_observed_at: datetime | None
    installed: tuple[LocalCatalogItemViewV1, ...] | None
    loaded_state: Literal["available", "unavailable"]
    loaded_reason: Literal[
        "source_available",
        "source_unavailable",
        "invalid_provider_data",
        "unverified_provider_version",
        "collection_in_progress",
        "operation_deadline_exceeded",
    ]
    loaded_observed_at: datetime | None
    loaded: tuple[LocalCatalogItemViewV1, ...] | None


class ObservedAccountIdentityViewV1(_ClosedV1):
    account_id: str
    state: Literal["verified", "unresolved"]
    email: str | None
    provider_organization: str | None
    collection_run_id: str | None
    verified_at: datetime | None
    provider_version: str | None
    source_id: Literal["claude.auth.status.v1"]
    scope: Literal["default_profile_quota"]
    running_agent_correlation: Literal["unresolved"]
    profile_protection: Literal["protected_default", "managed", "unknown"] = "unknown"


class ProviderAccountIdentityViewV1(_ClosedV1):
    """Provider-neutral identity receipt without legacy Claude markers."""

    account_id: str
    provider_key: str = Field(
        min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_-]{0,63}$"
    )
    state: Literal["verified", "unresolved"]
    email: str | None
    provider_organization: str | None
    collection_run_id: str | None
    verified_at: datetime | None
    provider_version: str | None
    identity_source_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9._-]+$",
    )
    running_agent_correlation: Literal["unresolved"]
    profile_protection: Literal["protected_default", "managed", "unknown"] = "unknown"


class ProviderConnectionViewV1(_ClosedV1):
    account_id: str
    flow_id: str | None
    state: ProviderConnectionStateV1
    can_connect: bool
    expected_email: str | None
    started_at: datetime | None
    expires_at: datetime | None
    reason_code: str


class StartProviderConnectionInputV1(_ClosedV1):
    expected_email: str = Field(
        min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    )


class CancelProviderConnectionInputV1(_ClosedV1):
    flow_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class CapabilitySourceViewV1(_ClosedV1):
    source_id: str
    source_class: Literal[
        "documented_api",
        "supported_cli",
        "approved_local_metadata",
        "experimental_private_or_browser",
    ]
    stability: Literal[
        "documented", "supported", "local_undocumented", "experimental", "unknown"
    ]
    mechanism_version: str
    credential_role: str
    side_effect_class: Literal["read_only", "managed_profile_write", "unknown"]
    evidence_reference: str
    is_experimental: bool


class ProviderCapabilityDeclarationViewV1(_ClosedV1):
    capability_id: str
    support_state: Literal[
        "supported", "experimental", "deferred", "unsupported", "unknown"
    ]
    stability: Literal[
        "documented", "supported", "local_undocumented", "experimental", "unknown"
    ]
    reason_code: str
    evidence_reference: str
    side_effect_class: Literal["read_only", "managed_profile_write", "unknown"]
    schema_minimum: str
    schema_maximum: str
    port_type: str | None
    output_schema: str | None
    platforms: tuple[str, ...]
    sources: tuple[CapabilitySourceViewV1, ...]


class ProviderCapabilityDeclarationPageV1(_ClosedV1):
    provider_key: str
    adapter_id: str
    adapter_version: str
    protocol_minimum: str
    protocol_maximum: str
    manifest_schema_version: str
    m0_mapping_id: str
    m0_mapping_version: str
    items: tuple[ProviderCapabilityDeclarationViewV1, ...]
    availability: AvailabilityV1


class OllamaCloudConnectionStatusV1(_ClosedV1):
    """Safe account connection state; no credentials or binding identifiers."""

    account_id: str
    state: CredentialConnectionStateV1
    can_verify: bool
    observed_at: datetime | None
    monitoring_state: Literal["off", "waiting", "scheduled", "unavailable", "reading"]
    monitoring_reason: str

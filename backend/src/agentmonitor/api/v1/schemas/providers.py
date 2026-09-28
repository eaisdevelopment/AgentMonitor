"""Safe wire models for the accepted M03 capability manifest."""

from datetime import datetime
from typing import Literal

from agentmonitor.api.v1.schemas.registry import AvailabilityV1
from agentmonitor.contracts.provider_system_v1 import ProviderConnectionStateV1
from pydantic import BaseModel, ConfigDict, Field


class _ClosedV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


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

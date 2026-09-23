"""Safe wire models for the accepted M03 capability manifest."""

from typing import Literal

from agentmonitor.api.v1.schemas.registry import AvailabilityV1
from pydantic import BaseModel, ConfigDict


class _ClosedV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


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

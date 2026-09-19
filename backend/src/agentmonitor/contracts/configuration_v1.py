"""Configuration descriptors and bootstrap receipt; never secret values or I/O."""

from dataclasses import dataclass
from typing import ClassVar, Literal

from agentmonitor.contracts.common_v1 import TechnicalValueV1


@dataclass(frozen=True, slots=True)
class ConfigurationDescriptorV1(TechnicalValueV1):
    external_name: str
    internal_name: str
    owner: str
    value_type: str
    unit: str | None
    validation_rule: str
    required: bool
    safe_default: str | None
    secret_class: Literal["non_secret", "agentmonitor", "provider", "development"]
    sources_low_to_high: tuple[str, ...]
    reload_behavior: str
    first_version: str
    deprecated_version: str | None
    removed_version: str | None
    consequences: tuple[str, ...]
    test_ids: tuple[str, ...]
    documentation_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConfigurationRegistryV1(TechnicalValueV1):
    """CTR-CONFIG-001 allocates descriptors, not loading or key ownership."""

    CONTRACT_ID: ClassVar[str] = "CTR-CONFIG-001"
    descriptors: tuple[ConfigurationDescriptorV1, ...]


@dataclass(frozen=True, slots=True)
class BootstrapConfigurationV1(TechnicalValueV1):
    """Validation receipt: values stay in their typed owner-specific settings.

    Secret settings are represented only by presence; the later loader owns
    protected values and cannot serialize them through this public metadata.
    """

    CONTRACT_ID: ClassVar[str] = "CTR-FND-003"
    configuration_version: str
    owners: tuple[str, ...]
    non_secret_sources: tuple[tuple[str, str], ...]
    secret_presence: tuple[tuple[str, bool], ...]

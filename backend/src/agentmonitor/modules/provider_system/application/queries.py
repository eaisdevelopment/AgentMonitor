"""Side-effect-free M03 capability-manifest query boundary."""

from dataclasses import dataclass
from datetime import datetime

from agentmonitor.contracts.common_v1 import QueryAvailabilityV1
from agentmonitor.contracts.provider_system_v1 import CapabilityManifestV1


@dataclass(frozen=True, slots=True)
class ProviderCapabilityQueryV1:
    manifest: CapabilityManifestV1
    availability: QueryAvailabilityV1


class ProviderCapabilitiesNotFoundV1(ValueError):
    def __init__(self) -> None:
        super().__init__("provider_capabilities_not_found")


class GetProviderCapabilitiesV1:
    """Return one already-registered safe manifest without invoking a provider."""

    def __init__(self, manifests: tuple[CapabilityManifestV1, ...]) -> None:
        self._manifests = {item.descriptor.provider_key: item for item in manifests}

    def __call__(self, provider_key: str) -> CapabilityManifestV1:
        try:
            return self._manifests[provider_key]
        except KeyError:
            raise ProviderCapabilitiesNotFoundV1() from None

    def view(self, provider_key: str, *, as_of: datetime) -> ProviderCapabilityQueryV1:
        return ProviderCapabilityQueryV1(
            self(provider_key),
            QueryAvailabilityV1("available", "capability_manifest_registered", as_of),
        )

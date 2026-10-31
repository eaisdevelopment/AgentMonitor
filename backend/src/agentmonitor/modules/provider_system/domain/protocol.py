"""Pure M03 manifest registration and capability negotiation policies."""

from dataclasses import dataclass
from itertools import pairwise
from typing import ClassVar, Literal
from uuid import NAMESPACE_URL, uuid5

from agentmonitor.contracts import provider_system_v1 as provider_contracts
from agentmonitor.contracts.common_v1 import TechnicalValueV1

ResolutionCodeV1 = Literal[
    "resolved",
    "protocol_incompatible",
    "capability_not_declared",
    "unsupported",
    "capability_disabled",
    "capability_schema_incompatible",
    "provider_version_unverified",
    "platform_unsupported",
    "source_policy_unapproved",
    "mapping_binding_invalid",
]


def resolve_one_exact_observation[ObservationT](
    values: tuple[ObservationT, ...],
) -> ObservationT | None:
    """Return one value only when every complete observation is identical."""
    if not values:
        return None
    first = values[0]
    if any(value != first for value in values[1:]):
        return None
    return first


@dataclass(frozen=True, slots=True)
class CapabilityResolutionV1(TechnicalValueV1):
    """One deterministic, pre-I/O capability decision."""

    CONTRACT_ID: ClassVar[str] = "CTR-PROV-001"
    OWNER: ClassVar[str] = "PLAN-M03"

    code: ResolutionCodeV1
    declaration: provider_contracts.CapabilityDeclarationV1 | None
    selected_source: provider_contracts.ProviderSourceV1 | None
    source_policy: provider_contracts.SourcePolicyV1 | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        is_resolved = self.code == "resolved"
        if is_resolved != (
            self.declaration is not None
            and self.selected_source is not None
            and self.source_policy is not None
        ):
            raise ValueError("capability_resolution_pair_invalid")


def _unresolved(code: ResolutionCodeV1) -> CapabilityResolutionV1:
    return CapabilityResolutionV1(code, None, None, None)


def _source_policy_is_approved(
    declaration: provider_contracts.CapabilityDeclarationV1,
    policy: provider_contracts.SourcePolicyV1,
) -> bool:
    declared_ids = tuple(item.source_id for item in declaration.sources)
    try:
        positions = tuple(
            declared_ids.index(source_id) for source_id in policy.source_ids
        )
    except ValueError:
        return False
    if positions != tuple(sorted(positions)):
        return False
    if len(policy.source_ids) <= 1:
        return True
    approved = {
        (
            transition.from_source_id,
            transition.to_source_id,
        )
        for transition in policy.approved_fallbacks
    }
    return all(transition in approved for transition in pairwise(policy.source_ids))


def resolve_capability(
    manifest: provider_contracts.CapabilityManifestV1,
    *,
    approved_mapping_digest: str,
    host_protocol_version: str,
    capability_id: str,
    capability_schema_version: provider_contracts.CapabilitySchemaVersionV1,
    provider_version: str,
    platform_id: str,
    source_policy: provider_contracts.SourcePolicyV1,
) -> CapabilityResolutionV1:
    """Resolve one exact typed capability and source before external I/O."""
    if manifest.m0_mapping_digest != approved_mapping_digest:
        return _unresolved("mapping_binding_invalid")
    try:
        protocol_compatible = manifest.descriptor.protocol_versions.includes(
            host_protocol_version
        )
    except ValueError:
        protocol_compatible = False
    if not protocol_compatible:
        return _unresolved("protocol_incompatible")

    declaration = next(
        (item for item in manifest.declarations if item.capability_id == capability_id),
        None,
    )
    if declaration is None:
        return _unresolved("capability_not_declared")
    if declaration.decision == "unsupported":
        return _unresolved("unsupported")
    if declaration.decision in {"deferred", "unknown"}:
        return _unresolved("capability_disabled")
    if not declaration.schema_versions.includes(capability_schema_version):
        return _unresolved("capability_schema_incompatible")
    if platform_id not in declaration.platforms:
        return _unresolved("platform_unsupported")
    if not declaration.provider_version_rule.verifies(provider_version):
        return _unresolved("provider_version_unverified")
    if declaration.decision == "experimental" and (
        source_policy.experimental_grant_ref is None
    ):
        return _unresolved("capability_disabled")
    if not _source_policy_is_approved(declaration, source_policy):
        return _unresolved("source_policy_unapproved")
    selected_source_id = source_policy.source_ids[0]
    selected_source = next(
        item for item in declaration.sources if item.source_id == selected_source_id
    )
    if selected_source.is_experimental and (
        source_policy.experimental_grant_ref is None
    ):
        return _unresolved("capability_disabled")
    return CapabilityResolutionV1(
        "resolved", declaration, selected_source, source_policy
    )


def manifest_fingerprint(manifest: provider_contracts.CapabilityManifestV1) -> str:
    """Return a reproducible local catalog fingerprint, not a signature."""
    canonical = (
        manifest.descriptor,
        manifest.manifest_schema_version,
        manifest.declarations,
        manifest.m0_mapping_id,
        manifest.m0_mapping_version,
        manifest.m0_mapping_digest,
    )
    return uuid5(NAMESPACE_URL, repr(canonical)).hex


@dataclass(frozen=True, slots=True)
class AdapterRegistrationViewV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-001"
    OWNER: ClassVar[str] = "PLAN-M03"

    provider_key: str
    adapter_id: str
    adapter_version: str
    manifest_fingerprint: str
    factory_identity: str


@dataclass(frozen=True, slots=True)
class AdapterRegistrationOutcomeV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-001"
    OWNER: ClassVar[str] = "PLAN-M03"

    code: Literal[
        "registered",
        "already_registered",
        "protocol_incompatible",
        "registration_conflict",
        "mapping_binding_invalid",
    ]
    registration: AdapterRegistrationViewV1 | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (self.registration is not None) != (
            self.code in {"registered", "already_registered"}
        ):
            raise ValueError("registration_outcome_pair_invalid")


class ProviderCatalogV1:
    """In-memory static-composition catalog; no plugin loading or provider I/O."""

    def __init__(
        self, *, host_protocol_version: str, approved_mapping_digest: str
    ) -> None:
        self._host_protocol_version = host_protocol_version
        self._approved_mapping_digest = approved_mapping_digest
        self._registrations: dict[
            tuple[str, str],
            tuple[AdapterRegistrationViewV1, provider_contracts.CapabilityManifestV1],
        ] = {}

    def register(
        self,
        manifest: provider_contracts.CapabilityManifestV1,
        *,
        factory_identity: str,
    ) -> AdapterRegistrationOutcomeV1:
        if manifest.m0_mapping_digest != self._approved_mapping_digest:
            return AdapterRegistrationOutcomeV1("mapping_binding_invalid", None)
        if not manifest.descriptor.protocol_versions.includes(
            self._host_protocol_version
        ):
            return AdapterRegistrationOutcomeV1("protocol_incompatible", None)
        fingerprint = manifest_fingerprint(manifest)
        registration = AdapterRegistrationViewV1(
            provider_key=manifest.descriptor.provider_key,
            adapter_id=manifest.descriptor.adapter_id,
            adapter_version=manifest.descriptor.adapter_version,
            manifest_fingerprint=fingerprint,
            factory_identity=factory_identity,
        )
        key = (registration.provider_key, registration.adapter_id)
        current = self._registrations.get(key)
        if current is None:
            self._registrations[key] = (registration, manifest)
            return AdapterRegistrationOutcomeV1("registered", registration)
        if current == (registration, manifest):
            return AdapterRegistrationOutcomeV1("already_registered", registration)
        return AdapterRegistrationOutcomeV1("registration_conflict", None)

    def get(
        self, provider_key: str, adapter_id: str
    ) -> AdapterRegistrationViewV1 | None:
        current = self._registrations.get((provider_key, adapter_id))
        return current[0] if current is not None else None

"""Pure M03 manifest registration and capability negotiation policies."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
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


def scheduled_source_policy_digest_v1(
    policy: provider_contracts.ScheduledSourceAdmissionPolicyV1,
) -> str:
    """Hash one closed non-secret policy; this is not a signature."""
    if not isinstance(policy, provider_contracts.ScheduledSourceAdmissionPolicyV1):
        raise provider_contracts.InvalidProviderContract(
            "scheduled_source_policy_invalid"
        )
    material = (
        "agentmonitor-scheduled-source-policy-v1",
        policy.policy_ref.value,
        policy.provider_key,
        policy.authority_id,
        policy.capability_id,
        policy.source_id,
        policy.adapter_version,
        policy.source_fingerprint,
        policy.payload_schema,
        policy.minimum_interval_seconds,
        policy.maximum_concurrency,
        policy.automatic_retry_count,
        policy.provider_request_count,
        policy.collection_policy_id,
        policy.collection_policy_version,
        policy.rate_policy_id,
        policy.rate_policy_version,
        policy.fairness_policy_id,
        policy.fairness_policy_version,
        policy.invalidation_policy_id,
        policy.invalidation_policy_version,
    )
    encoded = json.dumps(material, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def current_access_from_signal(signal: str) -> bool:
    """A current positive status requires a current successful source signal."""
    return signal == "verified_success"


def derive_scheduled_source_admission_v1(
    policy: provider_contracts.ScheduledSourceAdmissionPolicyV1,
    lineage: provider_contracts.ScheduledSourceLineageV1,
    *,
    evaluated_at: datetime,
) -> provider_contracts.ScheduledSourceAdmissionProofV1:
    """Admit one exact current binding from matched probe/run/commit lineage.

    The caller owns the current M02/M04/M05 reads. This pure decision never
    turns owner assertion into provider identity and must be rerun before every
    scheduled dispatch.
    """
    if (
        not isinstance(policy, provider_contracts.ScheduledSourceAdmissionPolicyV1)
        or not isinstance(lineage, provider_contracts.ScheduledSourceLineageV1)
        or not isinstance(evaluated_at, datetime)
        or evaluated_at.utcoffset() != timedelta(0)
    ):
        raise provider_contracts.InvalidProviderContract(
            "scheduled_source_not_admitted"
        )
    revoked = {
        "credential_unauthorized",
        "provider_schema_incompatible",
        "outcome_unresolved",
    }
    if (
        lineage.authorization_signal in revoked
        or lineage.account_id != lineage.current_account_id
        or lineage.binding_id != lineage.current_binding_id
        or lineage.binding_generation != lineage.current_binding_generation
        or lineage.access_target_id != lineage.current_access_target_id
        or lineage.provider_key != policy.provider_key
        or lineage.authority_id != policy.authority_id
        or lineage.capability_id != policy.capability_id
        or lineage.source_id != policy.source_id
        or lineage.adapter_version != policy.adapter_version
        or lineage.source_fingerprint != policy.source_fingerprint
        or lineage.payload_schema != policy.payload_schema
        or lineage.run_account_id != lineage.account_id
        or lineage.run_target_generation != lineage.binding_generation
        or lineage.run_source_id != lineage.source_id
        or lineage.run_adapter_version != lineage.adapter_version
        or lineage.run_payload_digest != lineage.payload_digest
        or lineage.commit_run_id != lineage.probe_run_id
        or lineage.commit_target_generation != lineage.binding_generation
        or lineage.commit_payload_schema != lineage.payload_schema
        or lineage.commit_payload_digest != lineage.payload_digest
        or lineage.authorization_signal_account_id != lineage.account_id
        or lineage.authorization_signal_binding_generation != lineage.binding_generation
        or lineage.authorization_signal_access_target_id != lineage.access_target_id
        or lineage.authorization_signal_source_id != lineage.source_id
        or lineage.authorization_signal_adapter_version != lineage.adapter_version
        or lineage.authorization_signal_source_fingerprint != lineage.source_fingerprint
        or lineage.authorization_signal_payload_schema != lineage.payload_schema
        or lineage.authorization_signal_run_requested_at > evaluated_at
        or (
            lineage.authorization_signal_observed_at is not None
            and lineage.authorization_signal_observed_at > evaluated_at
        )
        or lineage.authorization_signal == "verified_success"
        and (
            lineage.authorization_signal_run_state not in {"succeeded", "partial"}
            or lineage.authorization_signal_dispatch_certainty != "response_received"
        )
        or lineage.authorization_signal
        in {
            "credential_unauthorized",
            "provider_schema_incompatible",
            "rate_limited",
        }
        and (
            lineage.authorization_signal_run_state != "failed"
            or lineage.authorization_signal_dispatch_certainty != "response_received"
        )
        or lineage.authorization_signal
        in {"authorization_unavailable", "credential_update_in_progress"}
        and (
            lineage.authorization_signal_run_state != "failed"
            or lineage.authorization_signal_dispatch_certainty != "not_started"
        )
        or lineage.authorization_signal == "transient_failure"
        and (
            lineage.authorization_signal_run_state != "failed"
            or lineage.authorization_signal_dispatch_certainty
            not in {"not_started", "response_received", "may_have_started"}
        )
        or evaluated_at < lineage.commit_stored_at
    ):
        raise provider_contracts.InvalidProviderContract(
            "scheduled_source_not_admitted"
        )
    return provider_contracts.ScheduledSourceAdmissionProofV1(
        policy_ref=policy.policy_ref,
        policy_digest=scheduled_source_policy_digest_v1(policy),
        verification_id=lineage.verification_id,
        account_id=lineage.account_id,
        binding_id=lineage.binding_id,
        binding_generation=lineage.binding_generation,
        access_target_id=lineage.access_target_id,
        provider_key=lineage.provider_key,
        authority_id=lineage.authority_id,
        capability_id=lineage.capability_id,
        source_id=lineage.source_id,
        adapter_version=lineage.adapter_version,
        source_fingerprint=lineage.source_fingerprint,
        payload_schema=lineage.payload_schema,
        payload_digest=lineage.payload_digest,
        probe_run_id=lineage.probe_run_id,
        probe_admission_id=lineage.probe_admission_id,
        verified_at=lineage.verified_at,
        evaluated_at=evaluated_at,
        identity_provenance=lineage.identity_provenance,
        authorization_signal=lineage.authorization_signal,
        authorization_signal_run_id=lineage.authorization_signal_run_id,
        authorization_signal_admission_id=lineage.authorization_signal_admission_id,
        authorization_signal_run_state=lineage.authorization_signal_run_state,
        authorization_signal_dispatch_certainty=(
            lineage.authorization_signal_dispatch_certainty
        ),
        authorization_signal_run_requested_at=(
            lineage.authorization_signal_run_requested_at
        ),
        authorization_signal_observed_at=lineage.authorization_signal_observed_at,
    )


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

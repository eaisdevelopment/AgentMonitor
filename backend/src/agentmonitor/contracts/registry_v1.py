"""M02-owned provider-neutral V1 registry contracts.

Public values contain only AgentMonitor IDs, safe classifications, masked fields,
and bounded owner metadata. Provider locators and raw identity values have no
public serialization field.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import ClassVar, Literal, NoReturn, Protocol, SupportsIndex

from agentmonitor.contracts.common_v1 import (
    EventEnvelopeV1,
    OpaqueIdV1,
    TechnicalValueV1,
)
from agentmonitor.contracts.provider_system_v1 import DiscoveryOutcomeV1

RegistryLifecycleV1 = Literal["pending", "active", "disabled", "archived"]
OrganizationLifecycleV1 = Literal["active", "archived"]
IdentityDecisionStateV1 = Literal[
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
IdentityEvidenceClassV1 = Literal[
    "provider_verified",
    "owner_confirmed",
    "corroborated",
    "weak",
    "conflicting",
    "unknown",
    "unavailable",
    "unsupported",
]
RegistryFieldStateV1 = Literal[
    "known_masked", "withheld", "unknown", "unsupported", "unavailable"
]
ResourceKindV1 = Literal[
    "subscription_pool",
    "api_organization",
    "api_project",
    "workspace",
    "prepaid_credit_pool",
    "local_runtime_pool",
    "provider_specific",
    "unknown",
]
ProfilePurposeV1 = Literal["subscription", "api", "local_session", "combined"]
ProfileManagementStateV1 = Literal[
    "managed", "provider_default", "unmanaged", "unknown"
]
ProfileCompatibilityStateV1 = Literal[
    "compatible", "incompatible", "unknown", "unavailable"
]
RegistryScopeKindV1 = Literal["global", "organization", "provider", "account"]
ProviderIdentityResolutionStateV1 = Literal["resolved", "unresolved", "conflict"]
CredentialBindingLifecycleV1 = Literal[
    "pending", "active", "cleanup_pending", "cleanup_complete"
]
CredentialBindingReasonV1 = Literal[
    "owner_prepared",
    "owner_activated",
    "rotation_replaced",
    "pending_cleanup_requested",
    "owner_disconnected",
    "account_archived",
    "account_deleted",
    "local_cleanup_completed",
]
CredentialConnectionStateV1 = Literal[
    "not_configured",
    "pending",
    "access_valid_identity_unresolved",
    "access_valid_owner_confirmed",
    "unauthorized",
    "rate_limited",
    "store_locked",
    "authorization_unavailable",
    "unavailable",
]


def _valid_credential_binding_id(value: OpaqueIdV1) -> bool:
    binding_id = value.value
    return (
        len(binding_id) == 37
        and binding_id.startswith("amcb_")
        and all(character in "0123456789abcdef" for character in binding_id[5:])
    )


def _bounded(value: object, *, maximum: int = 256) -> bool:
    return (
        type(value) is str
        and value == value.strip()
        and 1 <= len(value) <= maximum
        and value.isprintable()
    )


def _positive_version(record_version: int, registry_revision: int) -> None:
    if (
        type(record_version) is not int
        or record_version < 1
        or type(registry_revision) is not int
        or registry_revision < 1
    ):
        raise ValueError("registry_version_invalid")


@dataclass(frozen=True, slots=True)
class MaskedRegistryFieldV1(TechnicalValueV1):
    """Safe public field state; a full provider value is never representable."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-002"
    OWNER: ClassVar[str] = "PLAN-M02"

    state: RegistryFieldStateV1
    masked_value: str | None
    reason_code: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (self.state == "known_masked") != (self.masked_value is not None):
            raise ValueError("registry_masked_field_pair_invalid")
        if self.masked_value is not None and not _bounded(
            self.masked_value, maximum=64
        ):
            raise ValueError("registry_masked_field_invalid")
        if not _bounded(self.reason_code, maximum=128):
            raise ValueError("registry_masked_field_reason_invalid")


@dataclass(frozen=True, slots=True)
class OrganizationViewV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-REG-001"
    OWNER: ClassVar[str] = "PLAN-M02"

    organization_id: OpaqueIdV1
    name: str
    description: str | None
    display_order: int
    lifecycle: OrganizationLifecycleV1
    active_account_count: int
    archived_account_count: int
    record_version: int
    registry_revision: int
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _positive_version(self.record_version, self.registry_revision)
        if (
            not _bounded(self.name)
            or (
                self.description is not None
                and not _bounded(self.description, maximum=1024)
            )
            or type(self.display_order) is not int
            or self.display_order < 0
            or type(self.active_account_count) is not int
            or type(self.archived_account_count) is not int
            or min(self.active_account_count, self.archived_account_count) < 0
            or (self.lifecycle == "active") != (self.archived_at is None)
        ):
            raise ValueError("registry_organization_invalid")


@dataclass(frozen=True, slots=True)
class OrganizationOrderingViewV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-REG-001"
    OWNER: ClassVar[str] = "PLAN-M02"

    organization_ids: tuple[OpaqueIdV1, ...]
    registry_revision: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not self.organization_ids
            or len(set(self.organization_ids)) != len(self.organization_ids)
            or type(self.registry_revision) is not int
            or self.registry_revision < 1
        ):
            raise ValueError("registry_organization_ordering_invalid")


@dataclass(frozen=True, slots=True)
class ProviderDefinitionViewV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-REG-004"
    OWNER: ClassVar[str] = "PLAN-M02"

    provider_key: str
    lifecycle: Literal["active", "disabled"]
    manifest_reference: str
    record_version: int
    registry_revision: int


@dataclass(frozen=True, slots=True)
class ProviderInstallationViewV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-REG-004"
    OWNER: ClassVar[str] = "PLAN-M02"

    provider_installation_id: OpaqueIdV1
    provider_key: str
    platform_key: str
    version: MaskedRegistryFieldV1
    presence_state: Literal["present", "missing", "unverified"]
    first_seen_at: datetime
    last_seen_at: datetime
    record_version: int
    registry_revision: int


@dataclass(frozen=True, slots=True)
class IdentityCorrelationDecisionV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-REG-006"
    OWNER: ClassVar[str] = "PLAN-M02"

    decision_id: OpaqueIdV1
    state: IdentityDecisionStateV1
    evidence_classes: tuple[IdentityEvidenceClassV1, ...]
    evidence_references: tuple[str, ...]
    candidate_id: OpaqueIdV1 | None
    account_id: OpaqueIdV1 | None
    profile_id: OpaqueIdV1 | None
    is_owner_confirmed: bool
    owner_principal_id: OpaqueIdV1 | None
    owner_confirmed_at: datetime | None
    reason_code: str
    record_version: int
    registry_revision: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _positive_version(self.record_version, self.registry_revision)
        owner_fields = (
            self.owner_principal_id is not None and self.owner_confirmed_at is not None
        )
        owner_confirmation_preserves_source = (
            "owner_confirmed" in self.evidence_classes
            and any(
                evidence_class != "owner_confirmed"
                for evidence_class in self.evidence_classes
            )
        )
        if (
            type(self.is_owner_confirmed) is not bool
            or self.is_owner_confirmed != owner_fields
            or (self.state == "owner_confirmed") != self.is_owner_confirmed
            or self.is_owner_confirmed != owner_confirmation_preserves_source
            or not self.evidence_classes
            or len(set(self.evidence_classes)) != len(self.evidence_classes)
            or not all(_bounded(item, maximum=128) for item in self.evidence_references)
            or not _bounded(self.reason_code, maximum=128)
        ):
            raise ValueError("registry_identity_decision_invalid")


@dataclass(frozen=True, slots=True)
class AccountViewV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-REG-002"
    OWNER: ClassVar[str] = "PLAN-M02"

    account_id: OpaqueIdV1
    provider_key: str
    friendly_name: str
    organization_id: OpaqueIdV1 | None
    lifecycle: RegistryLifecycleV1
    monitoring_preference: Literal["enabled", "disabled"]
    is_effective_monitoring_enabled: bool
    effective_monitoring_reason: str
    identity_state: IdentityDecisionStateV1
    masked_identity: MaskedRegistryFieldV1
    record_version: int
    registry_revision: int
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _positive_version(self.record_version, self.registry_revision)
        if (
            not _bounded(self.provider_key, maximum=64)
            or not _bounded(self.friendly_name)
            or type(self.is_effective_monitoring_enabled) is not bool
            or not _bounded(self.effective_monitoring_reason, maximum=128)
            or (self.lifecycle == "archived") != (self.archived_at is not None)
            or self.is_effective_monitoring_enabled
            and (
                self.lifecycle != "active"
                or self.monitoring_preference != "enabled"
                or self.identity_state not in {"matched", "owner_confirmed"}
            )
        ):
            raise ValueError("registry_account_invalid")


@dataclass(frozen=True, slots=True)
class CredentialBindingRecordV1(TechnicalValueV1):
    """Internal non-secret lifecycle record for one managed credential item.

    ``binding_id`` is a closed-shape application handle, not owner input. The
    application must generate it internally; this contract is not an API view.
    """

    CONTRACT_ID: ClassVar[str] = "CTR-REG-011"
    OWNER: ClassVar[str] = "PLAN-M02"

    account_id: OpaqueIdV1
    binding_id: OpaqueIdV1
    lifecycle: CredentialBindingLifecycleV1
    generation: int
    association_provenance: Literal["owner_asserted"]
    reason_code: CredentialBindingReasonV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not _valid_credential_binding_id(self.binding_id):
            raise ValueError("registry_credential_binding_id_invalid")
        if type(self.generation) is not int or self.generation < 1:
            raise ValueError("registry_credential_binding_generation_invalid")


@dataclass(frozen=True, slots=True)
class CredentialBindingAggregateV1(TechnicalValueV1):
    """One account's serialized binding state and current collection fence."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-011"
    OWNER: ClassVar[str] = "PLAN-M02"

    account_id: OpaqueIdV1
    record_version: int
    binding_generation: int
    bindings: tuple[CredentialBindingRecordV1, ...]

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.record_version) is not int
            or self.record_version < 0
            or type(self.binding_generation) is not int
            or self.binding_generation < 0
        ):
            raise ValueError("registry_credential_binding_version_invalid")
        if any(item.account_id != self.account_id for item in self.bindings):
            raise ValueError("registry_credential_binding_account_mismatch")
        binding_ids = tuple(item.binding_id for item in self.bindings)
        if len(set(binding_ids)) != len(binding_ids):
            raise ValueError("registry_credential_binding_duplicate")
        active = tuple(item for item in self.bindings if item.lifecycle == "active")
        pending = tuple(item for item in self.bindings if item.lifecycle == "pending")
        if len(active) > 1 or len(pending) > 1:
            raise ValueError("registry_credential_binding_conflict")
        if active and active[0].generation != self.binding_generation:
            raise ValueError("registry_credential_binding_generation_invalid")
        if pending and pending[0].generation != self.binding_generation + 1:
            raise ValueError("registry_credential_binding_generation_invalid")
        if any(item.generation > self.binding_generation + 1 for item in self.bindings):
            raise ValueError("registry_credential_binding_generation_invalid")
        if self.record_version == 0 and (self.binding_generation != 0 or self.bindings):
            raise ValueError("registry_credential_binding_version_invalid")


@dataclass(frozen=True, slots=True)
class ActiveCredentialBindingRefV1(TechnicalValueV1):
    """Internal non-secret exact generation captured before one provider read."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-011"
    OWNER: ClassVar[str] = "PLAN-M02"

    account_id: OpaqueIdV1
    binding_id: OpaqueIdV1
    generation: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not _valid_credential_binding_id(self.binding_id):
            raise ValueError("registry_credential_binding_id_invalid")
        if type(self.generation) is not int or self.generation < 1:
            raise ValueError("registry_credential_binding_generation_invalid")


def _valid_access_target_id(value: OpaqueIdV1) -> bool:
    target_id = value.value
    return (
        len(target_id) == 37
        and target_id.startswith("amat_")
        and all(character in "0123456789abcdef" for character in target_id[5:])
    )


@dataclass(frozen=True, slots=True)
class ProviderTargetRefV1(TechnicalValueV1):
    """Discriminated M02 target identity; never aliases cloud to installation."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-012"
    OWNER: ClassVar[str] = "PLAN-M02"

    target_kind: Literal["provider_installation", "cloud_service"]
    target_id: OpaqueIdV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not isinstance(self.target_id, OpaqueIdV1) or (
            self.target_kind == "cloud_service"
            and not _valid_access_target_id(self.target_id)
        ):
            raise ValueError("registry_provider_target_invalid")


@dataclass(frozen=True, slots=True)
class ProviderAccessTargetV1(TechnicalValueV1):
    """Code-owned official cloud service target, distinct from a local install."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-012"
    OWNER: ClassVar[str] = "PLAN-M02"

    access_target_id: OpaqueIdV1
    provider_key: str
    target_kind: Literal["cloud_service"]
    authority_id: str
    manifest_fingerprint: str
    lifecycle: Literal["active", "disabled"]
    record_version: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not _valid_access_target_id(self.access_target_id)
            or not _bounded(self.provider_key, maximum=64)
            or not _bounded(self.authority_id, maximum=128)
            or len(self.manifest_fingerprint) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.manifest_fingerprint
            )
            or type(self.record_version) is not int
            or self.record_version < 1
        ):
            raise ValueError("registry_provider_access_target_invalid")


@dataclass(frozen=True, slots=True)
class CloudMonitoringTargetV1(TechnicalValueV1):
    """Owner-confirmed cloud graph independent of a local installation."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-012"
    OWNER: ClassVar[str] = "PLAN-M02"

    profile_id: OpaqueIdV1
    resource_id: OpaqueIdV1
    account_id: OpaqueIdV1
    access_target_id: OpaqueIdV1
    binding: ActiveCredentialBindingRefV1
    lifecycle: Literal["active", "disabled", "archived"]
    identity_state: Literal["owner_confirmed"]
    owner_principal_id: OpaqueIdV1
    owner_asserted_at: datetime
    record_version: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            self.binding.account_id != self.account_id
            or not _valid_access_target_id(self.access_target_id)
            or self.owner_asserted_at.utcoffset() != timedelta(0)
            or type(self.record_version) is not int
            or self.record_version < 1
        ):
            raise ValueError("registry_cloud_monitoring_target_invalid")


@dataclass(frozen=True, slots=True)
class AssertCredentialAccountOwnershipCommandV1(TechnicalValueV1):
    """Owner assertion for one pending account and exact credential generation."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-012"
    OWNER: ClassVar[str] = "PLAN-M02"

    command_id: OpaqueIdV1
    principal_id: OpaqueIdV1
    account_id: OpaqueIdV1
    access_target_id: OpaqueIdV1
    expected_account_record_version: int
    binding: ActiveCredentialBindingRefV1
    requested_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            self.binding.account_id != self.account_id
            or not _valid_access_target_id(self.access_target_id)
            or type(self.expected_account_record_version) is not int
            or self.expected_account_record_version < 1
        ):
            raise ValueError("registry_credential_owner_assertion_invalid")


@dataclass(frozen=True, slots=True)
class InitiateOllamaCloudVerificationCommandV1(TechnicalValueV1):
    """Signed-in owner request; server resolves all private binding references."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-012"
    OWNER: ClassVar[str] = "PLAN-M02"

    idempotency_key: OpaqueIdV1
    principal_id: OpaqueIdV1
    account_id: OpaqueIdV1
    expected_account_record_version: int
    requested_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.expected_account_record_version) is not int
            or self.expected_account_record_version < 1
        ):
            raise ValueError("registry_credential_verification_command_invalid")


@dataclass(frozen=True, slots=True)
class CredentialBindingVerificationReceiptV1(TechnicalValueV1):
    """Successful balance-access receipt for one exact binding generation."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-012"
    OWNER: ClassVar[str] = "PLAN-M02"

    verification_id: OpaqueIdV1
    binding: ActiveCredentialBindingRefV1
    access_target_id: OpaqueIdV1
    run_id: OpaqueIdV1
    admission_id: OpaqueIdV1
    source_id: Literal["ollama.cloud.balance.v1"]
    adapter_version: str
    manifest_fingerprint: str
    payload_digest: str
    verified_at: datetime
    record_version: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        identifier = self.verification_id.value
        if (
            len(identifier) != 37
            or not identifier.startswith("amvr_")
            or any(character not in "0123456789abcdef" for character in identifier[5:])
            or not _valid_access_target_id(self.access_target_id)
            or not _bounded(self.adapter_version, maximum=64)
            or len(self.manifest_fingerprint) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.manifest_fingerprint
            )
            or len(self.payload_digest) != 64
            or any(
                character not in "0123456789abcdef" for character in self.payload_digest
            )
            or self.verified_at.utcoffset() != timedelta(0)
            or self.record_version != 1
        ):
            raise ValueError("registry_credential_verification_invalid")


@dataclass(frozen=True, slots=True)
class CredentialConnectionStatusV1(TechnicalValueV1):
    """Safe server-derived cloud connection status; no secret/keyring detail."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-012"
    OWNER: ClassVar[str] = "PLAN-M02"

    account_id: OpaqueIdV1
    state: CredentialConnectionStateV1
    can_verify: bool
    binding_generation: int | None
    observed_at: datetime | None
    reason_code: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.can_verify) is not bool
            or self.can_verify
            and self.state
            not in {
                "pending",
                "unauthorized",
                "store_locked",
                "authorization_unavailable",
            }
            or self.state == "not_configured"
            and self.binding_generation is not None
            or self.state not in {"not_configured", "unavailable"}
            and self.binding_generation is None
            or (
                self.binding_generation is not None
                and (
                    type(self.binding_generation) is not int
                    or self.binding_generation < 1
                )
            )
            or not _bounded(self.reason_code, maximum=128)
        ):
            raise ValueError("registry_credential_connection_status_invalid")


@dataclass(frozen=True, slots=True)
class MonitoringProfileViewV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-REG-003"
    OWNER: ClassVar[str] = "PLAN-M02"

    profile_id: OpaqueIdV1
    account_id: OpaqueIdV1
    provider_installation_id: OpaqueIdV1
    purpose: ProfilePurposeV1
    lifecycle: RegistryLifecycleV1
    management_state: ProfileManagementStateV1
    compatibility_state: ProfileCompatibilityStateV1
    is_protected_default: bool
    locator_state: Literal["configured", "withheld", "unavailable"]
    identity_state: Literal[
        "unknown",
        "owner_confirmed",
        "provider_verified",
        "conflict",
        "wrong_account",
        "invalidated",
        "unavailable",
    ]
    last_verified_at: datetime | None
    resource_ids: tuple[OpaqueIdV1, ...]
    record_version: int
    registry_revision: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _positive_version(self.record_version, self.registry_revision)
        if (
            type(self.is_protected_default) is not bool
            or self.is_protected_default
            != (self.management_state == "provider_default")
            or len(set(self.resource_ids)) != len(self.resource_ids)
        ):
            raise ValueError("registry_profile_invalid")


@dataclass(frozen=True, slots=True)
class AccountResourceViewV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-REG-005"
    OWNER: ClassVar[str] = "PLAN-M02"

    resource_id: OpaqueIdV1
    account_id: OpaqueIdV1
    kind: ResourceKindV1
    parent_resource_id: OpaqueIdV1 | None
    label: MaskedRegistryFieldV1
    lifecycle: Literal["active", "retired", "archived"]
    linked_profile_ids: tuple[OpaqueIdV1, ...]
    record_version: int
    registry_revision: int
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _positive_version(self.record_version, self.registry_revision)
        if self.parent_resource_id == self.resource_id or len(
            set(self.linked_profile_ids)
        ) != len(self.linked_profile_ids):
            raise ValueError("registry_resource_invalid")


@dataclass(frozen=True, slots=True)
class DiscoveryCandidateViewV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-REG-006"
    OWNER: ClassVar[str] = "PLAN-M02"

    candidate_id: OpaqueIdV1
    provider_key: str
    provider_installation_id: OpaqueIdV1
    candidate_kind: Literal["account"]
    association_state: IdentityDecisionStateV1
    evidence_classes: tuple[IdentityEvidenceClassV1, ...]
    evidence_set_digest: str
    masked_label: MaskedRegistryFieldV1
    owner_action_required: bool
    first_seen_at: datetime
    last_seen_at: datetime
    record_version: int
    registry_revision: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _positive_version(self.record_version, self.registry_revision)
        if (
            len(self.evidence_set_digest) != 64
            or any(
                value not in "0123456789abcdef" for value in self.evidence_set_digest
            )
            or not self.evidence_classes
            or type(self.owner_action_required) is not bool
            or (self.association_state == "owner_confirmation_required")
            != self.owner_action_required
        ):
            raise ValueError("registry_discovery_candidate_invalid")


@dataclass(frozen=True, slots=True)
class RegistryChangedV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-REG-007"
    OWNER: ClassVar[str] = "PLAN-M02"

    envelope: EventEnvelopeV1
    change_kind: str
    subject_type: str
    aggregate_version: int
    registry_revision: int
    reason_code: str


@dataclass(frozen=True, slots=True)
class ReauthenticationRequestWorkflowV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-REG-008"
    OWNER: ClassVar[str] = "PLAN-M02"

    workflow_id: OpaqueIdV1
    account_id: OpaqueIdV1
    profile_id: OpaqueIdV1
    state: Literal[
        "requested",
        "awaiting_owner_action",
        "verifying",
        "succeeded",
        "wrong_account_detected",
        "failed",
        "cancelled",
        "expired",
    ]
    generation: int
    is_eligible: bool
    reason_code: str
    started_at: datetime
    updated_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True, slots=True)
class AuthenticationHealthChangedV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-REG-010"
    OWNER: ClassVar[str] = "PLAN-M02"

    account_id: OpaqueIdV1
    profile_id: OpaqueIdV1
    provider_key: str
    previous_state: str
    current_state: str
    source_generation: int
    identity_state: Literal["matched", "mismatched", "unresolved"]
    observed_at: datetime
    recorded_at: datetime
    evidence_references: tuple[str, ...]


class PrivateProfileLocatorRefV1:
    """Private persistence handle; never serialize, log, or expose in a view."""

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        if not _bounded(value, maximum=512):
            raise ValueError("registry_profile_locator_invalid")
        self._value = value

    def __repr__(self) -> str:
        return "<PrivateProfileLocatorRefV1 redacted>"

    __str__ = __repr__

    def __getstate__(self) -> NoReturn:
        raise TypeError("registry_profile_locator_not_serializable")

    def __reduce_ex__(self, protocol: SupportsIndex) -> NoReturn:
        raise TypeError("registry_profile_locator_not_serializable")

    def reveal_for_persistence(self) -> str:
        return self._value


@dataclass(frozen=True, slots=True)
class DiscoveryReconciliationViewV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-REG-006"
    OWNER: ClassVar[str] = "PLAN-M02"

    installations: tuple[ProviderInstallationViewV1, ...]
    candidates: tuple[DiscoveryCandidateViewV1, ...]
    registry_revision: int


@dataclass(frozen=True, slots=True)
class ConfirmIdentityAssociationCommandV1(TechnicalValueV1):
    """Auditable owner command bound to one exact candidate evidence version."""

    command_id: OpaqueIdV1
    principal_id: OpaqueIdV1
    candidate_id: OpaqueIdV1
    expected_candidate_record_version: int
    friendly_name: str
    organization_id: OpaqueIdV1 | None
    evidence_set_digest: str
    requested_at: datetime

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not _bounded(self.friendly_name)
            or self.friendly_name != self.friendly_name.strip()
            or type(self.expected_candidate_record_version) is not int
            or self.expected_candidate_record_version < 1
            or len(self.evidence_set_digest) != 64
            or any(
                value not in "0123456789abcdef" for value in self.evidence_set_digest
            )
        ):
            raise ValueError("registry_identity_confirmation_invalid")


@dataclass(frozen=True, slots=True)
class ConfirmProviderIdentityFingerprintCommandV1(TechnicalValueV1):
    """Explicit owner command binding one exact approved identity observation."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-006"
    OWNER: ClassVar[str] = "PLAN-M02"

    idempotency_key: OpaqueIdV1
    principal_id: OpaqueIdV1
    account_id: OpaqueIdV1
    expected_account_record_version: int
    provider_key: str
    identity_scheme: str
    identity_scope: str
    identity_scheme_version: int
    subject_fingerprint: str
    source_id: str
    source_version: str
    parser_version: str
    evidence_reference: OpaqueIdV1
    expected_evidence_digest: str
    requested_at: datetime
    activate_pending_account: bool = False

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        safe_tokens = (
            self.provider_key,
            self.identity_scheme,
            self.identity_scope,
            self.source_id,
            self.source_version,
            self.parser_version,
        )
        if (
            type(self.activate_pending_account) is not bool
            or any(
                not _bounded(value, maximum=64)
                or not value.isascii()
                or any(
                    character not in "abcdefghijklmnopqrstuvwxyz0123456789._-"
                    for character in value
                )
                for value in safe_tokens
            )
            or type(self.expected_account_record_version) is not int
            or self.expected_account_record_version < 1
            or type(self.identity_scheme_version) is not int
            or self.identity_scheme_version < 1
            or len(self.subject_fingerprint) != 64
            or any(
                value not in "0123456789abcdef" for value in self.subject_fingerprint
            )
            or not _bounded(self.evidence_reference.value, maximum=128)
            or not self.evidence_reference.value.isascii()
            or any(
                character not in "abcdefghijklmnopqrstuvwxyz0123456789._-"
                for character in self.evidence_reference.value
            )
            or len(self.expected_evidence_digest) != 64
            or any(
                value not in "0123456789abcdef"
                for value in self.expected_evidence_digest
            )
        ):
            raise ValueError("registry_provider_identity_confirmation_invalid")


@dataclass(frozen=True, slots=True)
class ResolveProviderIdentityFingerprintQueryV1(TechnicalValueV1):
    """Read-only lookup key; the fingerprint is never returned or logged."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-006"
    OWNER: ClassVar[str] = "PLAN-M02"

    provider_key: str
    identity_scheme: str
    identity_scope: str
    identity_scheme_version: int
    subject_fingerprint: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        safe_keys = (self.provider_key, self.identity_scheme, self.identity_scope)
        if (
            any(
                not _bounded(value, maximum=64)
                or not value.isascii()
                or any(
                    character not in "abcdefghijklmnopqrstuvwxyz0123456789._-"
                    for character in value
                )
                for value in safe_keys
            )
            or type(self.identity_scheme_version) is not int
            or self.identity_scheme_version < 1
            or len(self.subject_fingerprint) != 64
            or any(
                value not in "0123456789abcdef" for value in self.subject_fingerprint
            )
        ):
            raise ValueError("registry_provider_identity_query_invalid")


@dataclass(frozen=True, slots=True)
class ProviderIdentityResolutionV1(TechnicalValueV1):
    """Exact active account resolution without echoing provider identity."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-006"
    OWNER: ClassVar[str] = "PLAN-M02"

    state: ProviderIdentityResolutionStateV1
    account_id: OpaqueIdV1 | None
    account_record_version: int | None
    reason_code: str
    registry_revision: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        resolved = self.state == "resolved"
        if (
            resolved != (self.account_id is not None)
            or resolved != (self.account_record_version is not None)
            or self.account_record_version is not None
            and self.account_record_version < 1
            or not _bounded(self.reason_code, maximum=128)
            or type(self.registry_revision) is not int
            or self.registry_revision < 0
        ):
            raise ValueError("registry_provider_identity_resolution_invalid")


@dataclass(frozen=True, slots=True)
class RegistryScopeSnapshotV1(TechnicalValueV1):
    """Deterministic registry-only membership at one committed revision."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-009"
    OWNER: ClassVar[str] = "PLAN-M02"

    scope_kind: RegistryScopeKindV1
    scope_id: OpaqueIdV1 | None
    organization_ids: tuple[OpaqueIdV1, ...]
    account_ids: tuple[OpaqueIdV1, ...]
    resource_ids: tuple[OpaqueIdV1, ...]
    completeness_state: Literal["complete", "unavailable"]
    registry_revision: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        values = (
            self.organization_ids,
            self.account_ids,
            self.resource_ids,
        )
        if (
            (self.scope_kind == "global") != (self.scope_id is None)
            or type(self.registry_revision) is not int
            or self.registry_revision < 0
            or any(len(set(items)) != len(items) for items in values)
        ):
            raise ValueError("registry_scope_snapshot_invalid")


@dataclass(frozen=True, slots=True)
class RegistryCloudResourceMembershipV2(TechnicalValueV1):
    """One real cloud resource membership without an asserted pool relationship."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-009"
    CONTRACT_VERSION: ClassVar[str] = "2.0.0"
    OWNER: ClassVar[str] = "PLAN-M02"

    resource_id: OpaqueIdV1
    account_id: OpaqueIdV1
    provider_key: str
    provider_target: ProviderTargetRefV1
    relationship_state: Literal["unresolved"]
    registry_revision: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not isinstance(self.resource_id, OpaqueIdV1)
            or not isinstance(self.account_id, OpaqueIdV1)
            or not _bounded(self.provider_key, maximum=64)
            or not isinstance(self.provider_target, ProviderTargetRefV1)
            or self.provider_target.target_kind != "cloud_service"
            or self.relationship_state != "unresolved"
            or type(self.registry_revision) is not int
            or self.registry_revision < 1
        ):
            raise ValueError("registry_cloud_resource_membership_invalid")


@dataclass(frozen=True, slots=True)
class RegistryScopeSnapshotV2(TechnicalValueV1):
    """One atomic registry scope including real local and cloud resources."""

    CONTRACT_ID: ClassVar[str] = "CTR-REG-009"
    CONTRACT_VERSION: ClassVar[str] = "2.0.0"
    OWNER: ClassVar[str] = "PLAN-M02"

    scope_kind: RegistryScopeKindV1
    scope_id: OpaqueIdV1 | None
    organization_ids: tuple[OpaqueIdV1, ...]
    account_ids: tuple[OpaqueIdV1, ...]
    local_resource_ids: tuple[OpaqueIdV1, ...]
    cloud_resources: tuple[RegistryCloudResourceMembershipV2, ...]
    completeness_state: Literal["complete", "unavailable"]
    registry_revision: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        cloud_resource_ids = tuple(item.resource_id for item in self.cloud_resources)
        cloud_accounts = tuple(item.account_id for item in self.cloud_resources)
        values = (
            self.organization_ids,
            self.account_ids,
            self.local_resource_ids,
            cloud_resource_ids,
        )
        if (
            (self.scope_kind == "global") != (self.scope_id is None)
            or type(self.registry_revision) is not int
            or self.registry_revision < 0
            or any(len(set(items)) != len(items) for items in values)
            or set(self.local_resource_ids).intersection(cloud_resource_ids)
            or any(item not in self.account_ids for item in cloud_accounts)
            or any(
                item.registry_revision != self.registry_revision
                for item in self.cloud_resources
            )
            or self.scope_kind == "provider"
            and any(
                item.provider_key != self.scope_id.value
                for item in self.cloud_resources
                if self.scope_id is not None
            )
            or self.scope_kind == "account"
            and self.account_ids not in {(), (self.scope_id,)}
            or self.scope_kind == "organization"
            and self.organization_ids not in {(), (self.scope_id,)}
            or len(self.account_ids) > 200
            or len(self.local_resource_ids) + len(self.cloud_resources) > 2000
        ):
            raise ValueError("registry_scope_snapshot_invalid")

    @property
    def resource_ids(self) -> tuple[OpaqueIdV1, ...]:
        return tuple(
            sorted(
                (
                    *self.local_resource_ids,
                    *(item.resource_id for item in self.cloud_resources),
                ),
                key=lambda item: item.value,
            )
        )


class CapacityScopeMembershipQueryV2(Protocol):
    """M02-owned atomic V2 capacity-scope membership read port."""

    def __call__(
        self, scope_kind: RegistryScopeKindV1, scope_id: OpaqueIdV1 | None = None
    ) -> RegistryScopeSnapshotV2: ...


class ReconcileProviderDiscoveryV1(Protocol):
    def __call__(
        self, outcome: DiscoveryOutcomeV1, *, reconciled_at: datetime
    ) -> DiscoveryReconciliationViewV1: ...


class ListDiscoveryCandidatesV1(Protocol):
    def __call__(
        self, provider_key: str | None = None
    ) -> tuple[DiscoveryCandidateViewV1, ...]: ...


class ConfirmIdentityAssociationV1(Protocol):
    def __call__(
        self, command: ConfirmIdentityAssociationCommandV1
    ) -> AccountViewV1: ...


class ConfirmProviderIdentityFingerprintV1(Protocol):
    def __call__(
        self, command: ConfirmProviderIdentityFingerprintCommandV1
    ) -> ProviderIdentityResolutionV1: ...


class ResolveProviderIdentityFingerprintV1(Protocol):
    def __call__(
        self, query: ResolveProviderIdentityFingerprintQueryV1
    ) -> ProviderIdentityResolutionV1: ...


class RegisterAccountV1(Protocol):
    def __call__(
        self, command: ConfirmIdentityAssociationCommandV1
    ) -> AccountViewV1: ...


class ListAccountsV1(Protocol):
    def __call__(
        self, provider_key: str | None = None
    ) -> tuple[AccountViewV1, ...]: ...


class ListProviderInstallationsV1(Protocol):
    """Read-only safe installation projection; locators are not representable."""

    def __call__(
        self, provider_key: str | None = None
    ) -> tuple[ProviderInstallationViewV1, ...]: ...


class ListMonitoringProfilesV1(Protocol):
    def __call__(
        self, account_id: OpaqueIdV1
    ) -> tuple[MonitoringProfileViewV1, ...]: ...


class ListAccountResourcesV1(Protocol):
    def __call__(self, account_id: OpaqueIdV1) -> tuple[AccountResourceViewV1, ...]: ...


class AlertScopeAndSubjectQueryV1(Protocol):
    """CTR-REG-009 read-only registry membership query."""

    def __call__(
        self, scope_kind: RegistryScopeKindV1, scope_id: OpaqueIdV1 | None = None
    ) -> RegistryScopeSnapshotV1: ...


@dataclass(frozen=True, slots=True)
class AlertSubjectScopeV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-REG-009"
    OWNER: ClassVar[str] = "PLAN-M02"
    account_id: OpaqueIdV1
    provider_key: str
    organization_id: OpaqueIdV1 | None
    eligible: bool
    registry_revision: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not _bounded(self.provider_key, maximum=64)
            or type(self.eligible) is not bool
        ):
            raise ValueError("registry_alert_subject_invalid")
        if type(self.registry_revision) is not int or self.registry_revision < 1:
            raise ValueError("registry_version_invalid")


class ResolveAlertSubjectScopeV1(Protocol):
    CONTRACT_ID: ClassVar[str] = "CTR-REG-009"
    OWNER: ClassVar[str] = "PLAN-M02"

    def __call__(self, account_id: OpaqueIdV1) -> AlertSubjectScopeV1 | None: ...

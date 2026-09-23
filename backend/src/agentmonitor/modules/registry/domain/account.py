"""Pure provider-neutral registry identity, profile, and resource policies."""

from dataclasses import dataclass
from typing import Literal

from agentmonitor.contracts.common_v1 import OpaqueIdV1, TechnicalValueV1
from agentmonitor.contracts.registry_v1 import (
    AccountResourceViewV1,
    AccountViewV1,
    IdentityDecisionStateV1,
    IdentityEvidenceClassV1,
    MonitoringProfileViewV1,
    OrganizationViewV1,
    RegistryScopeKindV1,
    RegistryScopeSnapshotV1,
)


class RegistryPolicyErrorV1(ValueError):
    """Stable M02 policy refusal without external values."""


@dataclass(frozen=True, slots=True)
class IdentityEvidenceV1(TechnicalValueV1):
    candidate_id: OpaqueIdV1
    evidence_class: IdentityEvidenceClassV1
    evidence_references: tuple[str, ...]
    is_unique: bool
    has_conflict: bool

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not self.evidence_references
            or len(set(self.evidence_references)) != len(self.evidence_references)
            or type(self.is_unique) is not bool
            or type(self.has_conflict) is not bool
        ):
            raise RegistryPolicyErrorV1("registry_identity_evidence_invalid")


@dataclass(frozen=True, slots=True)
class IdentityPolicyDecisionV1(TechnicalValueV1):
    state: IdentityDecisionStateV1
    may_associate_automatically: bool
    reason_code: str


@dataclass(frozen=True, slots=True)
class AccountIdentityContinuityV1(TechnicalValueV1):
    account_id: OpaqueIdV1
    provider_key: str


@dataclass(frozen=True, slots=True)
class AccountMonitoringDecisionV1(TechnicalValueV1):
    is_enabled: bool
    reason_code: str
    monitoring_preference: Literal["enabled", "disabled"]


@dataclass(frozen=True, slots=True)
class AccountArchiveDecisionV1(TechnicalValueV1):
    lifecycle: Literal["archived"]
    monitoring_preference: Literal["enabled", "disabled"]
    linked_profile_ids: tuple[OpaqueIdV1, ...]
    linked_resource_ids: tuple[OpaqueIdV1, ...]
    is_effective_monitoring_enabled: Literal[False]


@dataclass(frozen=True, slots=True)
class DiscoveryReconciliationDecisionV1(TechnicalValueV1):
    state: Literal["reconciled", "unresolved", "rejected"]
    preserve_confirmed_relationships: bool
    reason_code: str


@dataclass(frozen=True, slots=True)
class CandidateEvidenceTransitionV1(TechnicalValueV1):
    state: IdentityDecisionStateV1
    invalidate_account_eligibility: bool
    preserve_associated_account: bool
    reason_code: str


@dataclass(frozen=True, slots=True)
class ReauthenticationContinuityDecisionV1(TechnicalValueV1):
    account_id: OpaqueIdV1
    profile_id: OpaqueIdV1
    identity_state: Literal["provider_verified", "wrong_account", "unresolved"]
    preserve_relationships: bool


@dataclass(frozen=True, slots=True)
class SafeRegistryEventProjectionV1(TechnicalValueV1):
    subject_type: str
    subject_id: OpaqueIdV1
    aggregate_version: int
    registry_revision: int
    change_kind: str


def _is_sha256_digest(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def ensure_candidate_confirmation_is_current(
    *,
    expected_record_version: int,
    current_record_version: int,
    expected_evidence_set_digest: str,
    current_evidence_set_digest: str,
) -> None:
    """Reject an owner decision made against stale or changed evidence."""
    if (
        type(expected_record_version) is not int
        or expected_record_version < 1
        or type(current_record_version) is not int
        or current_record_version < 1
        or not _is_sha256_digest(expected_evidence_set_digest)
        or not _is_sha256_digest(current_evidence_set_digest)
    ):
        raise RegistryPolicyErrorV1("registry_candidate_confirmation_invalid")
    if expected_record_version != current_record_version:
        raise RegistryPolicyErrorV1("registry_candidate_version_conflict")
    if expected_evidence_set_digest != current_evidence_set_digest:
        raise RegistryPolicyErrorV1("registry_candidate_evidence_conflict")


def decide_command_replay(
    stored_request_fingerprint: str | None, requested_fingerprint: str
) -> Literal["execute", "replay"]:
    """Classify a receipt lookup without weakening fingerprint equality."""
    if not _is_sha256_digest(requested_fingerprint) or (
        stored_request_fingerprint is not None
        and not _is_sha256_digest(stored_request_fingerprint)
    ):
        raise RegistryPolicyErrorV1("registry_idempotency_fingerprint_invalid")
    if stored_request_fingerprint is None:
        return "execute"
    if stored_request_fingerprint == requested_fingerprint:
        return "replay"
    raise RegistryPolicyErrorV1("registry_idempotency_conflict")


def decide_identity_correlation(
    evidence: IdentityEvidenceV1,
) -> IdentityPolicyDecisionV1:
    """Choose a safe association state without provider-specific branching."""
    if evidence.has_conflict or evidence.evidence_class == "conflicting":
        return IdentityPolicyDecisionV1("conflict", False, "identity_conflict")
    if evidence.evidence_class == "provider_verified" and evidence.is_unique:
        return IdentityPolicyDecisionV1("matched", True, "unique_provider_identity")
    if evidence.evidence_class in {"provider_verified", "corroborated", "weak"}:
        return IdentityPolicyDecisionV1(
            "owner_confirmation_required", False, "owner_confirmation_required"
        )
    if evidence.evidence_class == "unsupported":
        return IdentityPolicyDecisionV1("unsupported", False, "identity_unsupported")
    return IdentityPolicyDecisionV1("unresolved", False, "identity_unresolved")


def account_identity_after_metadata_change(
    account: AccountViewV1,
) -> AccountIdentityContinuityV1:
    """Project the immutable identity independently of name/group metadata."""
    return AccountIdentityContinuityV1(account.account_id, account.provider_key)


def decide_account_monitoring(
    *,
    lifecycle: str,
    monitoring_preference: str,
    identity_state: IdentityDecisionStateV1,
) -> AccountMonitoringDecisionV1:
    """Derive effective monitoring without changing the persisted preference."""
    if monitoring_preference == "enabled":
        preference: Literal["enabled", "disabled"] = "enabled"
    elif monitoring_preference == "disabled":
        preference = "disabled"
    else:
        raise RegistryPolicyErrorV1("registry_monitoring_preference_invalid")
    if lifecycle == "archived":
        return AccountMonitoringDecisionV1(False, "archived", preference)
    if lifecycle != "active":
        return AccountMonitoringDecisionV1(False, "account_not_active", preference)
    if monitoring_preference != "enabled":
        return AccountMonitoringDecisionV1(False, "monitoring_disabled", preference)
    if identity_state not in {"matched", "owner_confirmed"}:
        return AccountMonitoringDecisionV1(False, "identity_not_eligible", preference)
    return AccountMonitoringDecisionV1(True, "eligible", preference)


def decide_account_archive(
    *,
    monitoring_preference: str,
    linked_profile_ids: tuple[OpaqueIdV1, ...],
    linked_resource_ids: tuple[OpaqueIdV1, ...],
) -> AccountArchiveDecisionV1:
    """Archive an account without erasing its monitoring intent or graph links."""
    if monitoring_preference == "enabled":
        preference: Literal["enabled", "disabled"] = "enabled"
    elif monitoring_preference == "disabled":
        preference = "disabled"
    else:
        raise RegistryPolicyErrorV1("registry_monitoring_preference_invalid")
    if len(set(linked_profile_ids)) != len(linked_profile_ids) or len(
        set(linked_resource_ids)
    ) != len(linked_resource_ids):
        raise RegistryPolicyErrorV1("registry_invalid_relationship")
    return AccountArchiveDecisionV1(
        lifecycle="archived",
        monitoring_preference=preference,
        linked_profile_ids=linked_profile_ids,
        linked_resource_ids=linked_resource_ids,
        is_effective_monitoring_enabled=False,
    )


def decide_discovery_reconciliation(
    *,
    outcome_state: str,
    contract_valid: bool,
    provider_version_verified: bool,
) -> DiscoveryReconciliationDecisionV1:
    """Classify discovery input without replacing confirmed relationships."""
    if type(contract_valid) is not bool or type(provider_version_verified) is not bool:
        raise RegistryPolicyErrorV1("registry_discovery_outcome_invalid")
    if not contract_valid or outcome_state == "malformed":
        return DiscoveryReconciliationDecisionV1(
            "rejected", True, "discovery_contract_invalid"
        )
    if outcome_state != "success" or not provider_version_verified:
        return DiscoveryReconciliationDecisionV1(
            "unresolved", True, "discovery_evidence_unverified"
        )
    return DiscoveryReconciliationDecisionV1(
        "reconciled", True, "discovery_evidence_verified"
    )


def may_deduplicate_resource(
    *, has_approved_stable_identity: bool, labels_match: bool
) -> bool:
    """Labels never establish resource identity, even when they happen to match."""
    if type(has_approved_stable_identity) is not bool or type(labels_match) is not bool:
        raise RegistryPolicyErrorV1("registry_resource_identity_invalid")
    return has_approved_stable_identity


def decide_candidate_evidence_transition(
    *,
    current_state: IdentityDecisionStateV1,
    current_evidence_set_digest: str,
    proposed_evidence_set_digest: str,
) -> CandidateEvidenceTransitionV1:
    """Changed confirmed evidence becomes conflict without discarding its link."""
    if not _is_sha256_digest(current_evidence_set_digest) or not _is_sha256_digest(
        proposed_evidence_set_digest
    ):
        raise RegistryPolicyErrorV1("registry_candidate_evidence_invalid")
    changed = current_evidence_set_digest != proposed_evidence_set_digest
    if current_state == "owner_confirmed" and changed:
        return CandidateEvidenceTransitionV1(
            "conflict", True, True, "confirmed_evidence_changed"
        )
    if current_state == "conflict":
        return CandidateEvidenceTransitionV1(
            "conflict", True, True, "identity_conflict"
        )
    return CandidateEvidenceTransitionV1(current_state, False, True, "evidence_current")


def owner_confirmation_evidence_classes(
    original_evidence_class: IdentityEvidenceClassV1,
) -> tuple[IdentityEvidenceClassV1, ...]:
    """Preserve source evidence separately from the owner's confirmation action."""
    if original_evidence_class == "owner_confirmed":
        raise RegistryPolicyErrorV1("registry_identity_evidence_invalid")
    return (original_evidence_class, "owner_confirmed")


def decide_reauthentication_continuity(
    *,
    account_id: OpaqueIdV1,
    profile_id: OpaqueIdV1,
    identity_comparison: Literal["matched", "mismatched", "unresolved"],
) -> ReauthenticationContinuityDecisionV1:
    """Re-auth results change verification state, never durable registry IDs."""
    state: Literal["provider_verified", "wrong_account", "unresolved"]
    if identity_comparison == "matched":
        state = "provider_verified"
    elif identity_comparison == "mismatched":
        state = "wrong_account"
    else:
        state = "unresolved"
    return ReauthenticationContinuityDecisionV1(account_id, profile_id, state, True)


def safe_registry_event_projection(
    *,
    subject_type: str,
    subject_id: OpaqueIdV1,
    aggregate_version: int,
    registry_revision: int,
    change_kind: str,
) -> SafeRegistryEventProjectionV1:
    """Build the closed safe payload projection used by the M02 outbox."""
    if aggregate_version < 1 or registry_revision < 1:
        raise RegistryPolicyErrorV1("registry_version_invalid")
    return SafeRegistryEventProjectionV1(
        subject_type,
        subject_id,
        aggregate_version,
        registry_revision,
        change_kind,
    )


def project_registry_scope(
    *,
    scope_kind: RegistryScopeKindV1,
    scope_id: OpaqueIdV1 | None,
    organizations: tuple[OrganizationViewV1, ...],
    accounts: tuple[AccountViewV1, ...],
    resources: tuple[AccountResourceViewV1, ...],
    registry_revision: int,
) -> RegistryScopeSnapshotV1:
    """Project one deterministic current registry membership snapshot."""
    if (scope_kind == "global") != (scope_id is None):
        raise RegistryPolicyErrorV1("registry_scope_invalid")
    scope_value = scope_id.value if scope_id is not None else None
    active_organizations = {
        item.organization_id: item
        for item in organizations
        if item.lifecycle == "active"
    }
    active_accounts = tuple(item for item in accounts if item.lifecycle != "archived")
    if scope_kind == "organization":
        active_accounts = tuple(
            item for item in active_accounts if item.organization_id == scope_id
        )
    elif scope_kind == "provider":
        active_accounts = tuple(
            item for item in active_accounts if item.provider_key == scope_value
        )
    elif scope_kind == "account":
        active_accounts = tuple(
            item for item in active_accounts if item.account_id == scope_id
        )
    account_ids = {item.account_id for item in active_accounts}
    active_resources = tuple(
        item
        for item in resources
        if item.lifecycle == "active" and item.account_id in account_ids
    )
    if scope_kind == "global":
        organization_ids = tuple(active_organizations)
    else:
        organization_ids = tuple(
            {
                item.organization_id
                for item in active_accounts
                if item.organization_id in active_organizations
            }
        )
    return RegistryScopeSnapshotV1(
        scope_kind=scope_kind,
        scope_id=scope_id,
        organization_ids=tuple(sorted(organization_ids, key=lambda item: item.value)),
        account_ids=tuple(sorted(account_ids, key=lambda item: item.value)),
        resource_ids=tuple(
            sorted(
                {item.resource_id for item in active_resources},
                key=lambda item: item.value,
            )
        ),
        completeness_state="complete",
        registry_revision=registry_revision,
    )


def ensure_profile_authentication_eligible(
    profile: MonitoringProfileViewV1,
) -> Literal["eligible"]:
    """Fail before a private locator can be resolved or an adapter invoked."""
    if profile.is_protected_default:
        raise RegistryPolicyErrorV1("registry_profile_protected")
    if (
        profile.lifecycle != "active"
        or profile.management_state != "managed"
        or profile.compatibility_state != "compatible"
        or profile.locator_state != "configured"
        or profile.identity_state not in {"owner_confirmed", "provider_verified"}
    ):
        raise RegistryPolicyErrorV1("registry_profile_not_eligible")
    return "eligible"


def validate_resource_parent(
    *,
    resource_id: OpaqueIdV1,
    account_id: OpaqueIdV1,
    parent: AccountResourceViewV1 | None,
) -> None:
    """Validate one parent edge; repositories additionally prevent deep cycles."""
    if parent is not None and (
        parent.resource_id == resource_id or parent.account_id != account_id
    ):
        raise RegistryPolicyErrorV1("registry_invalid_relationship")


def validate_resource_ancestry(
    *,
    resource_id: OpaqueIdV1,
    account_id: OpaqueIdV1,
    ancestors: tuple[AccountResourceViewV1, ...],
) -> None:
    """Reject cross-account ancestry and a cycle at any depth."""
    if any(
        item.account_id != account_id or item.resource_id == resource_id
        for item in ancestors
    ):
        raise RegistryPolicyErrorV1("registry_invalid_relationship")

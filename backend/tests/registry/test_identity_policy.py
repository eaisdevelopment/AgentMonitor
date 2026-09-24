"""ST-REG-001 pure registry identity, privacy, and graph policies."""

from dataclasses import fields, replace
from datetime import UTC, datetime
from inspect import signature
from typing import Literal

import pytest
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    AccountResourceViewV1,
    AccountViewV1,
    DiscoveryCandidateViewV1,
    IdentityCorrelationDecisionV1,
    MaskedRegistryFieldV1,
    MonitoringProfileViewV1,
    OrganizationViewV1,
)
from agentmonitor.contracts.registry_v1 import (
    ConfirmIdentityAssociationV1 as PublishedConfirmIdentityAssociationV1,
)
from agentmonitor.contracts.registry_v1 import (
    ReconcileProviderDiscoveryV1 as PublishedReconcileProviderDiscoveryV1,
)
from agentmonitor.contracts.registry_v1 import (
    RegisterAccountV1 as PublishedRegisterAccountV1,
)
from agentmonitor.modules.registry.application.accounts import (
    ConfirmIdentityAssociationV1 as ConcreteConfirmIdentityAssociationV1,
)
from agentmonitor.modules.registry.application.accounts import (
    RegisterAccountV1 as ConcreteRegisterAccountV1,
)
from agentmonitor.modules.registry.application.discovery import (
    ReconcileProviderDiscoveryV1 as ConcreteReconcileProviderDiscoveryV1,
)
from agentmonitor.modules.registry.domain import account as account_policy
from agentmonitor.modules.registry.domain.account import (
    IdentityEvidenceV1,
    RegistryPolicyErrorV1,
    account_identity_after_metadata_change,
    decide_account_monitoring,
    decide_candidate_evidence_transition,
    decide_command_replay,
    decide_identity_correlation,
    decide_provider_identity_confirmation,
    decide_reauthentication_continuity,
    ensure_candidate_confirmation_is_current,
    ensure_profile_authentication_eligible,
    may_deduplicate_resource,
    owner_confirmation_evidence_classes,
    project_registry_scope,
    safe_registry_event_projection,
    validate_resource_ancestry,
    validate_resource_parent,
)

NOW = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)


def _account(
    account_id: str,
    *,
    provider_key: str = "provider-a",
    organization_id: str | None = "organization-1",
    lifecycle: str = "active",
) -> AccountViewV1:
    archived_at = NOW if lifecycle == "archived" else None
    return AccountViewV1(
        account_id=OpaqueIdV1(account_id),
        provider_key=provider_key,
        friendly_name=f"Account {account_id}",
        organization_id=(
            OpaqueIdV1(organization_id) if organization_id is not None else None
        ),
        lifecycle=lifecycle,  # type: ignore[arg-type]
        monitoring_preference="enabled",
        is_effective_monitoring_enabled=lifecycle == "active",
        effective_monitoring_reason=(
            "eligible" if lifecycle == "active" else "archived"
        ),
        identity_state="owner_confirmed",
        masked_identity=MaskedRegistryFieldV1(
            "withheld", None, "identity_privacy_minimized"
        ),
        record_version=1,
        registry_revision=4,
        created_at=NOW,
        updated_at=NOW,
        archived_at=archived_at,
    )


def _resource(resource_id: str, account_id: str) -> AccountResourceViewV1:
    return AccountResourceViewV1(
        resource_id=OpaqueIdV1(resource_id),
        account_id=OpaqueIdV1(account_id),
        kind="subscription_pool",
        parent_resource_id=None,
        label=MaskedRegistryFieldV1("withheld", None, "privacy_minimized"),
        lifecycle="active",
        linked_profile_ids=(),
        record_version=1,
        registry_revision=4,
        created_at=NOW,
        updated_at=NOW,
    )


def _eligible_profile() -> MonitoringProfileViewV1:
    return MonitoringProfileViewV1(
        profile_id=OpaqueIdV1("profile-1"),
        account_id=OpaqueIdV1("account-1"),
        provider_installation_id=OpaqueIdV1("installation-1"),
        purpose="subscription",
        lifecycle="active",
        management_state="managed",
        compatibility_state="compatible",
        is_protected_default=False,
        locator_state="configured",
        identity_state="owner_confirmed",
        last_verified_at=NOW,
        resource_ids=(OpaqueIdV1("resource-1"),),
        record_version=1,
        registry_revision=1,
    )


def test_scope_projection_is_deterministic_and_excludes_wrong_scope_subjects() -> None:
    """M02-PURE-006: exact scope deduplicates and excludes nonmembers."""
    organization = OrganizationViewV1(
        organization_id=OpaqueIdV1("organization-1"),
        name="Organization One",
        description=None,
        display_order=0,
        lifecycle="active",
        active_account_count=1,
        archived_account_count=1,
        record_version=1,
        registry_revision=4,
        created_at=NOW,
        updated_at=NOW,
        archived_at=None,
    )
    current = _account("account-2")
    archived = _account("account-1", lifecycle="archived")
    wrong_scope = _account("account-3", organization_id="organization-2")
    current_resource = _resource("resource-2", "account-2")

    snapshot = project_registry_scope(
        scope_kind="organization",
        scope_id=organization.organization_id,
        organizations=(organization,),
        accounts=(current, current, archived, wrong_scope),
        resources=(
            current_resource,
            current_resource,
            _resource("resource-1", "account-1"),
            _resource("resource-3", "account-3"),
        ),
        registry_revision=4,
    )

    assert snapshot.organization_ids == (organization.organization_id,)
    assert snapshot.account_ids == (current.account_id,)
    assert snapshot.resource_ids == (OpaqueIdV1("resource-2"),)
    assert snapshot.registry_revision == 4


def test_account_identity_is_independent_of_mutable_metadata() -> None:
    """M02-PURE-007: rename/group changes preserve internal account identity."""
    account = _account("account-1", provider_key="provider-a")
    changed = replace(
        account,
        friendly_name="Renamed Account",
        organization_id=OpaqueIdV1("organization-2"),
        record_version=2,
    )

    identity = account_identity_after_metadata_change(changed)

    assert identity.account_id == OpaqueIdV1("account-1")
    assert identity.provider_key == "provider-a"
    assert account.friendly_name != identity.provider_key


def test_provider_external_and_internal_identity_values_remain_distinct() -> None:
    """Supplemental: provider evidence and internal IDs remain distinct values."""
    account = _account("account-1", provider_key="provider-a")
    evidence = IdentityEvidenceV1(
        candidate_id=OpaqueIdV1("candidate-1"),
        evidence_class="corroborated",
        evidence_references=("safe-provider-evidence-1",),
        is_unique=False,
        has_conflict=False,
    )

    assert account.account_id != evidence.candidate_id
    assert account.provider_key != evidence.evidence_references[0]
    assert account.friendly_name not in evidence.evidence_references


def test_safe_event_projection_has_no_mutable_or_provider_evidence_field() -> None:
    """M02-PURE-025: event/log projection is a closed safe allowlist."""
    projection = safe_registry_event_projection(
        subject_type="account",
        subject_id=OpaqueIdV1("account-1"),
        aggregate_version=2,
        registry_revision=4,
        change_kind="organization_assigned",
    )

    assert {item.name for item in fields(projection)} == {
        "subject_type",
        "subject_id",
        "aggregate_version",
        "registry_revision",
        "change_kind",
    }
    assert not {
        "friendly_name",
        "provider_identity",
        "profile_locator_ref",
        "evidence_reference",
    } & {item.name for item in fields(projection)}


def test_monitoring_eligibility_preserves_preference_but_fails_closed() -> None:
    """M02-PURE-010: conflict disables effective state but retains preference."""
    assert decide_account_monitoring(
        lifecycle="active",
        monitoring_preference="enabled",
        identity_state="owner_confirmed",
    ).is_enabled
    conflict = decide_account_monitoring(
        lifecycle="active",
        monitoring_preference="enabled",
        identity_state="conflict",
    )
    assert conflict.reason_code == "identity_not_eligible"
    assert not conflict.is_enabled
    assert conflict.monitoring_preference == "enabled"


def test_archive_preserves_monitoring_intent_and_links_while_disabling() -> None:
    """M02-PURE-011: archive preserves links/intent and disables monitoring."""
    decision = account_policy.decide_account_archive(
        monitoring_preference="enabled",
        linked_profile_ids=(OpaqueIdV1("profile-1"),),
        linked_resource_ids=(OpaqueIdV1("resource-1"),),
    )

    assert decision.lifecycle == "archived"
    assert decision.monitoring_preference == "enabled"
    assert decision.linked_profile_ids == (OpaqueIdV1("profile-1"),)
    assert decision.linked_resource_ids == (OpaqueIdV1("resource-1"),)
    assert not decision.is_effective_monitoring_enabled


def test_registry_relationship_types_keep_distinct_opaque_ids() -> None:
    """Supplemental: current public relationship DTOs use distinct IDs/types."""
    account = _account("account-1")
    resource = _resource("resource-1", "account-1")
    profile = _eligible_profile()
    evidence = IdentityEvidenceV1(
        candidate_id=OpaqueIdV1("candidate-1"),
        evidence_class="corroborated",
        evidence_references=("safe-provider-evidence-1",),
        is_unique=False,
        has_conflict=False,
    )

    assert account.account_id == resource.account_id
    assert account.account_id == profile.account_id
    assert resource.resource_id != account.account_id
    assert profile.profile_id != resource.resource_id
    assert evidence.candidate_id not in {account.account_id, profile.profile_id}
    assert len({type(account), type(profile), type(resource), type(evidence)}) == 4


def test_resource_deduplication_never_uses_a_matching_label() -> None:
    """M02-PURE-014: only an approved stable identity permits deduplication."""
    assert not may_deduplicate_resource(
        has_approved_stable_identity=False, labels_match=True
    )
    assert may_deduplicate_resource(
        has_approved_stable_identity=True, labels_match=False
    )


def test_changed_confirmed_evidence_preserves_link_but_invalidates_eligibility() -> (
    None
):
    """M02-PURE-018: changed evidence becomes a retained conflict."""
    transition = decide_candidate_evidence_transition(
        current_state="owner_confirmed",
        current_evidence_set_digest="a" * 64,
        proposed_evidence_set_digest="b" * 64,
    )

    assert transition.state == "conflict"
    assert transition.invalidate_account_eligibility
    assert transition.preserve_associated_account


@pytest.mark.parametrize(
    ("outcome_state", "contract_valid", "provider_version_verified", "state"),
    [
        ("partial", True, True, "unresolved"),
        ("success", False, True, "rejected"),
        ("success", True, False, "unresolved"),
    ],
)
def test_untrusted_discovery_preserves_confirmed_relationships(
    outcome_state: str,
    contract_valid: bool,
    provider_version_verified: bool,
    state: str,
) -> None:
    """M02-PURE-016: partial/malformed/unverified discovery fails closed."""
    decision = account_policy.decide_discovery_reconciliation(
        outcome_state=outcome_state,
        contract_valid=contract_valid,
        provider_version_verified=provider_version_verified,
    )

    assert decision.state == state
    assert decision.preserve_confirmed_relationships


def test_owner_confirmation_preserves_original_evidence_class() -> None:
    """M02-PURE-019: confirmation retains actor/time/evidence distinction."""
    assert owner_confirmation_evidence_classes("corroborated") == (
        "corroborated",
        "owner_confirmed",
    )
    decision = IdentityCorrelationDecisionV1(
        decision_id=OpaqueIdV1("decision-1"),
        state="owner_confirmed",
        evidence_classes=("corroborated", "owner_confirmed"),
        evidence_references=("safe-provider-evidence-1",),
        candidate_id=OpaqueIdV1("candidate-1"),
        account_id=OpaqueIdV1("account-1"),
        profile_id=None,
        is_owner_confirmed=True,
        owner_principal_id=OpaqueIdV1("principal-1"),
        owner_confirmed_at=NOW,
        reason_code="owner_confirmed",
        record_version=1,
        registry_revision=1,
    )
    assert decision.owner_principal_id == OpaqueIdV1("principal-1")
    assert decision.owner_confirmed_at == NOW
    with pytest.raises(ValueError, match="registry_identity_decision_invalid"):
        replace(decision, evidence_classes=("owner_confirmed",))


@pytest.mark.parametrize(
    "missing_owner_field",
    [
        "owner_principal_id",
        "owner_confirmed_at",
    ],
)
def test_owner_confirmation_requires_both_actor_and_timestamp(
    missing_owner_field: Literal["owner_principal_id", "owner_confirmed_at"],
) -> None:
    """M02-PURE-019: incomplete owner attribution is invalid."""
    decision = IdentityCorrelationDecisionV1(
        decision_id=OpaqueIdV1("decision-1"),
        state="owner_confirmed",
        evidence_classes=("corroborated", "owner_confirmed"),
        evidence_references=("safe-provider-evidence-1",),
        candidate_id=OpaqueIdV1("candidate-1"),
        account_id=OpaqueIdV1("account-1"),
        profile_id=None,
        is_owner_confirmed=True,
        owner_principal_id=OpaqueIdV1("principal-1"),
        owner_confirmed_at=NOW,
        reason_code="owner_confirmed",
        record_version=1,
        registry_revision=1,
    )

    with pytest.raises(ValueError, match="registry_identity_decision_invalid"):
        if missing_owner_field == "owner_principal_id":
            replace(decision, owner_principal_id=None)
        else:
            replace(decision, owner_confirmed_at=None)


def test_invalidated_identity_cannot_silently_reactivate_monitoring() -> None:
    """M02-PURE-020: invalidation remains ineligible without new review."""
    decision = decide_account_monitoring(
        lifecycle="active",
        monitoring_preference="enabled",
        identity_state="invalidated",
    )
    retained_conflict = decide_candidate_evidence_transition(
        current_state="conflict",
        current_evidence_set_digest="a" * 64,
        proposed_evidence_set_digest="a" * 64,
    )

    assert not decision.is_enabled
    assert decision.reason_code == "identity_not_eligible"
    assert retained_conflict.state == "conflict"
    assert retained_conflict.invalidate_account_eligibility


def test_reauthentication_never_changes_account_or_profile_identity() -> None:
    """M02-PURE-023: mismatch preserves IDs and records wrong-account state."""
    decision = decide_reauthentication_continuity(
        account_id=OpaqueIdV1("account-1"),
        profile_id=OpaqueIdV1("profile-1"),
        identity_comparison="mismatched",
    )

    assert decision.account_id == OpaqueIdV1("account-1")
    assert decision.profile_id == OpaqueIdV1("profile-1")
    assert decision.identity_state == "wrong_account"
    assert decision.preserve_relationships


def test_matching_reauthentication_preserves_identity_and_history() -> None:
    """M02-PURE-023: a match preserves IDs/relationships and verifies identity."""
    decision = decide_reauthentication_continuity(
        account_id=OpaqueIdV1("account-1"),
        profile_id=OpaqueIdV1("profile-1"),
        identity_comparison="matched",
    )

    assert decision.account_id == OpaqueIdV1("account-1")
    assert decision.profile_id == OpaqueIdV1("profile-1")
    assert decision.identity_state == "provider_verified"
    assert decision.preserve_relationships


def test_non_strong_identity_requires_owner_confirmation() -> None:
    """M02-PURE-015/017: ambiguous evidence never auto-associates."""
    decision = decide_identity_correlation(
        IdentityEvidenceV1(
            candidate_id=OpaqueIdV1("candidate-1"),
            evidence_class="corroborated",
            evidence_references=("M0-M3-CLAUDE-SCOPED-ENTRY-001",),
            is_unique=False,
            has_conflict=False,
        )
    )

    assert decision.state == "owner_confirmation_required"
    assert not decision.may_associate_automatically


def test_only_unique_provider_verified_identity_may_match_automatically() -> None:
    """M02-PURE-015: automatic matching needs approved strong uniqueness."""
    decision = decide_identity_correlation(
        IdentityEvidenceV1(
            candidate_id=OpaqueIdV1("candidate-1"),
            evidence_class="provider_verified",
            evidence_references=("M0-M3-CLAUDE-SCOPED-ENTRY-001",),
            is_unique=True,
            has_conflict=False,
        )
    )

    assert decision.state == "matched"
    assert decision.may_associate_automatically


def test_nonunique_provider_verified_identity_still_requires_confirmation() -> None:
    """M02-PURE-015: provider verification alone cannot overcome ambiguity."""
    decision = decide_identity_correlation(
        IdentityEvidenceV1(
            candidate_id=OpaqueIdV1("candidate-1"),
            evidence_class="provider_verified",
            evidence_references=("M0-M3-CLAUDE-SCOPED-ENTRY-001",),
            is_unique=False,
            has_conflict=False,
        )
    )

    assert decision.state == "owner_confirmation_required"
    assert not decision.may_associate_automatically
    assert decision.reason_code == "owner_confirmation_required"


def test_conflicting_identity_never_overwrites_association() -> None:
    """M02-PURE-018: conflict wins over evidence strength."""
    decision = decide_identity_correlation(
        IdentityEvidenceV1(
            candidate_id=OpaqueIdV1("candidate-1"),
            evidence_class="provider_verified",
            evidence_references=("M0-M3-CLAUDE-SCOPED-ENTRY-001",),
            is_unique=True,
            has_conflict=True,
        )
    )

    assert decision.state == "conflict"
    assert not decision.may_associate_automatically


def test_candidate_confirmation_requires_current_version_and_exact_evidence() -> None:
    """M02-PURE-019: owner confirms exactly the candidate evidence reviewed."""
    digest = "a" * 64

    ensure_candidate_confirmation_is_current(
        expected_record_version=3,
        current_record_version=3,
        expected_evidence_set_digest=digest,
        current_evidence_set_digest=digest,
    )
    with pytest.raises(
        RegistryPolicyErrorV1, match="registry_candidate_version_conflict"
    ):
        ensure_candidate_confirmation_is_current(
            expected_record_version=2,
            current_record_version=3,
            expected_evidence_set_digest=digest,
            current_evidence_set_digest=digest,
        )
    with pytest.raises(
        RegistryPolicyErrorV1, match="registry_candidate_evidence_conflict"
    ):
        ensure_candidate_confirmation_is_current(
            expected_record_version=3,
            current_record_version=3,
            expected_evidence_set_digest="b" * 64,
            current_evidence_set_digest=digest,
        )


def test_command_receipt_replays_only_the_exact_safe_request() -> None:
    """Supplemental: command receipt reuse cannot change graph intent."""
    assert decide_command_replay(None, "a" * 64) == "execute"
    assert decide_command_replay("a" * 64, "a" * 64) == "replay"
    with pytest.raises(RegistryPolicyErrorV1, match="registry_idempotency_conflict"):
        decide_command_replay("a" * 64, "b" * 64)


def test_explicit_provider_identity_confirmation_refreshes_matching_evidence() -> None:
    """M02-PURE-030: a fresh owner command replaces stale evidence, not identity."""
    assert (
        decide_provider_identity_confirmation(
            resolution_state="unresolved",
            current_account_matches=False,
            existing_claim=False,
        )
        == "create"
    )
    assert (
        decide_provider_identity_confirmation(
            resolution_state="resolved",
            current_account_matches=True,
            existing_claim=True,
        )
        == "refresh"
    )
    invalid_cases: tuple[
        tuple[Literal["unresolved", "resolved", "conflict"], bool, bool], ...
    ] = (
        ("conflict", False, True),
        ("resolved", False, True),
        ("resolved", True, False),
        ("unresolved", False, True),
    )
    for state, account_matches, existing_claim in invalid_cases:
        with pytest.raises(RegistryPolicyErrorV1, match="registry_identity_conflict"):
            decide_provider_identity_confirmation(
                resolution_state=state,
                current_account_matches=account_matches,
                existing_claim=existing_claim,
            )


def test_candidate_owner_action_flag_must_match_current_state() -> None:
    """M02-PURE-017: public action state cannot contradict correlation state."""
    with pytest.raises(ValueError, match="registry_discovery_candidate_invalid"):
        DiscoveryCandidateViewV1(
            candidate_id=OpaqueIdV1("candidate-1"),
            provider_key="claude",
            provider_installation_id=OpaqueIdV1("installation-1"),
            candidate_kind="account",
            association_state="owner_confirmed",
            evidence_classes=("owner_confirmed",),
            evidence_set_digest="a" * 64,
            masked_label=MaskedRegistryFieldV1(
                "withheld", None, "identity_privacy_minimized"
            ),
            owner_action_required=True,
            first_seen_at=NOW,
            last_seen_at=NOW,
            record_version=2,
            registry_revision=2,
        )


def test_protected_default_profile_is_rejected_before_locator_resolution() -> None:
    """M02-PURE-021: protected profiles cannot enter authentication flows."""
    profile = MonitoringProfileViewV1(
        profile_id=OpaqueIdV1("profile-1"),
        account_id=OpaqueIdV1("account-1"),
        provider_installation_id=OpaqueIdV1("installation-1"),
        purpose="subscription",
        lifecycle="active",
        management_state="provider_default",
        compatibility_state="unknown",
        is_protected_default=True,
        locator_state="withheld",
        identity_state="owner_confirmed",
        last_verified_at=NOW,
        resource_ids=(OpaqueIdV1("resource-1"),),
        record_version=1,
        registry_revision=1,
    )

    with pytest.raises(RegistryPolicyErrorV1, match="registry_profile_protected"):
        ensure_profile_authentication_eligible(profile)


@pytest.mark.parametrize(
    "changes",
    [
        {"lifecycle": "archived"},
        {"management_state": "unmanaged"},
        {"management_state": "unknown"},
        {"compatibility_state": "incompatible"},
        {"compatibility_state": "unknown"},
        {"compatibility_state": "unavailable"},
        {"locator_state": "unavailable"},
        {"identity_state": "unknown"},
        {"identity_state": "conflict"},
        {"identity_state": "wrong_account"},
        {"identity_state": "unavailable"},
    ],
)
def test_only_active_managed_verified_compatible_profile_is_eligible(
    changes: dict[str, str],
) -> None:
    """M02-PURE-022: every unknown/archived/unmanaged/unverified path rejects."""
    eligible = _eligible_profile()
    assert ensure_profile_authentication_eligible(eligible) == "eligible"

    ineligible = replace(eligible, **changes)  # type: ignore[arg-type]
    with pytest.raises(RegistryPolicyErrorV1, match="registry_profile_not_eligible"):
        ensure_profile_authentication_eligible(ineligible)


def test_published_mutation_ports_match_concrete_call_signatures() -> None:
    """Supplemental: three concrete mutations match their published ports."""
    assert signature(ConcreteReconcileProviderDiscoveryV1.__call__) == signature(
        PublishedReconcileProviderDiscoveryV1.__call__
    )
    assert signature(ConcreteConfirmIdentityAssociationV1.__call__) == signature(
        PublishedConfirmIdentityAssociationV1.__call__
    )
    assert signature(ConcreteRegisterAccountV1.__call__) == signature(
        PublishedRegisterAccountV1.__call__
    )


def test_public_views_have_no_locator_or_raw_identity_field() -> None:
    """Supplemental: selected public DTOs exclude obvious prohibited fields."""
    profile_fields = {field.name for field in fields(MonitoringProfileViewV1)}
    masked_fields = {field.name for field in fields(MaskedRegistryFieldV1)}

    assert "profile_locator_ref" not in profile_fields
    assert "locator" not in profile_fields
    assert "raw_identity" not in masked_fields
    assert masked_fields == {"state", "masked_value", "reason_code"}


def test_resource_parent_must_share_account_and_cannot_self_reference() -> None:
    """M02-PURE-013: the normalized resource graph is account-local and acyclic."""
    parent = AccountResourceViewV1(
        resource_id=OpaqueIdV1("resource-parent"),
        account_id=OpaqueIdV1("account-1"),
        kind="subscription_pool",
        parent_resource_id=None,
        label=MaskedRegistryFieldV1("withheld", None, "privacy_minimized"),
        lifecycle="active",
        linked_profile_ids=(),
        record_version=1,
        registry_revision=1,
        created_at=NOW,
        updated_at=NOW,
    )

    validate_resource_parent(
        resource_id=OpaqueIdV1("resource-child"),
        account_id=OpaqueIdV1("account-1"),
        parent=parent,
    )
    with pytest.raises(RegistryPolicyErrorV1, match="registry_invalid_relationship"):
        validate_resource_parent(
            resource_id=OpaqueIdV1("resource-parent"),
            account_id=OpaqueIdV1("account-1"),
            parent=parent,
        )

    with pytest.raises(RegistryPolicyErrorV1, match="registry_invalid_relationship"):
        validate_resource_ancestry(
            resource_id=OpaqueIdV1("resource-child"),
            account_id=OpaqueIdV1("account-1"),
            ancestors=(
                parent,
                _resource("resource-child", "account-1"),
            ),
        )
    with pytest.raises(RegistryPolicyErrorV1, match="registry_invalid_relationship"):
        validate_resource_parent(
            resource_id=OpaqueIdV1("resource-child"),
            account_id=OpaqueIdV1("account-2"),
            parent=parent,
        )

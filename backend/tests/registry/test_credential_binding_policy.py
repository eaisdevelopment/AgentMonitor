"""M6 cloud M02 pure credential-binding lifecycle policy."""

from dataclasses import fields
from typing import Literal, cast

import pytest

from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    CredentialBindingAggregateV1,
    CredentialBindingRecordV1,
)
from agentmonitor.modules.registry.domain.account import RegistryPolicyErrorV1
from agentmonitor.modules.registry.domain.credential_binding import (
    DisconnectReasonV1,
    activate_prepared_credential_binding,
    complete_credential_binding_cleanup,
    disconnect_active_credential_binding,
    ensure_credential_binding_commit_current,
    mark_pending_credential_binding_cleanup,
    new_credential_binding_aggregate,
    prepare_credential_binding,
    resolve_active_credential_binding,
)

ACCOUNT_ID = OpaqueIdV1("account-1")
FIRST_BINDING_ID = OpaqueIdV1(f"amcb_{'1' * 32}")
SECOND_BINDING_ID = OpaqueIdV1(f"amcb_{'2' * 32}")


def _active_first_binding() -> CredentialBindingAggregateV1:
    initial = new_credential_binding_aggregate(ACCOUNT_ID)
    pending = prepare_credential_binding(
        initial,
        binding_id=FIRST_BINDING_ID,
        expected_record_version=0,
    )
    return activate_prepared_credential_binding(
        pending,
        binding_id=FIRST_BINDING_ID,
        expected_record_version=1,
    )


def test_binding_contract_is_non_secret_and_owner_asserted() -> None:
    """M6-T004: the internal contract exposes only safe binding metadata."""
    aggregate = _active_first_binding()
    binding = aggregate.bindings[0]

    assert {field.name for field in fields(binding)} == {
        "account_id",
        "binding_id",
        "lifecycle",
        "generation",
        "association_provenance",
        "reason_code",
    }
    assert binding.association_provenance == "owner_asserted"
    with pytest.raises(ValueError, match="unsupported-field-state"):
        CredentialBindingRecordV1(
            account_id=ACCOUNT_ID,
            binding_id=SECOND_BINDING_ID,
            lifecycle="pending",
            generation=2,
            association_provenance=cast(Literal["owner_asserted"], "provider_verified"),
            reason_code="owner_prepared",
        )
    with pytest.raises(ValueError, match="registry_credential_binding_id_invalid"):
        CredentialBindingRecordV1(
            account_id=ACCOUNT_ID,
            binding_id=OpaqueIdV1("owner-supplied-arbitrary-value"),
            lifecycle="pending",
            generation=2,
            association_provenance="owner_asserted",
            reason_code="owner_prepared",
        )


def test_initial_prepare_and_activation_publish_one_current_generation() -> None:
    """M6-T004/T005: pending becomes the sole active binding explicitly."""
    initial = new_credential_binding_aggregate(ACCOUNT_ID)

    pending = prepare_credential_binding(
        initial,
        binding_id=FIRST_BINDING_ID,
        expected_record_version=0,
    )

    assert pending.record_version == 1
    assert pending.binding_generation == 0
    assert pending.bindings[0].lifecycle == "pending"
    assert pending.bindings[0].generation == 1
    assert resolve_active_credential_binding(pending) is None

    active = activate_prepared_credential_binding(
        pending,
        binding_id=FIRST_BINDING_ID,
        expected_record_version=1,
    )
    reference = resolve_active_credential_binding(active)

    assert active.record_version == 2
    assert active.binding_generation == 1
    assert reference is not None
    assert reference.account_id == ACCOUNT_ID
    assert reference.binding_id == FIRST_BINDING_ID
    assert reference.generation == 1
    assert ensure_credential_binding_commit_current(active, reference) == "current"


def test_failed_rotation_preserves_old_active_binding_and_exposes_cleanup() -> None:
    """M6-T005: a failed new store cannot replace the known-good binding."""
    active = _active_first_binding()
    original_reference = resolve_active_credential_binding(active)
    assert original_reference is not None

    rotating = prepare_credential_binding(
        active,
        binding_id=SECOND_BINDING_ID,
        expected_record_version=2,
    )

    assert rotating.binding_generation == 1
    assert resolve_active_credential_binding(rotating) == original_reference
    assert {item.lifecycle for item in rotating.bindings} == {"active", "pending"}

    cleanup = mark_pending_credential_binding_cleanup(
        rotating,
        binding_id=SECOND_BINDING_ID,
        expected_record_version=3,
    )

    assert cleanup.record_version == 4
    assert cleanup.binding_generation == 1
    assert resolve_active_credential_binding(cleanup) == original_reference
    assert {item.binding_id: item.lifecycle for item in cleanup.bindings} == {
        FIRST_BINDING_ID: "active",
        SECOND_BINDING_ID: "cleanup_pending",
    }
    assert ensure_credential_binding_commit_current(cleanup, original_reference) == (
        "current"
    )


def test_successful_rotation_fences_old_generation_and_schedules_cleanup() -> None:
    """M6-T005/T010: rotation publishes new authority before old cleanup."""
    active = _active_first_binding()
    old_reference = resolve_active_credential_binding(active)
    assert old_reference is not None
    rotating = prepare_credential_binding(
        active,
        binding_id=SECOND_BINDING_ID,
        expected_record_version=2,
    )

    rotated = activate_prepared_credential_binding(
        rotating,
        binding_id=SECOND_BINDING_ID,
        expected_record_version=3,
    )
    new_reference = resolve_active_credential_binding(rotated)

    assert rotated.record_version == 4
    assert rotated.binding_generation == 2
    assert new_reference is not None
    assert new_reference.binding_id == SECOND_BINDING_ID
    assert new_reference.generation == 2
    assert {item.binding_id: item.lifecycle for item in rotated.bindings} == {
        FIRST_BINDING_ID: "cleanup_pending",
        SECOND_BINDING_ID: "active",
    }
    with pytest.raises(
        RegistryPolicyErrorV1,
        match="registry_credential_binding_stale",
    ):
        ensure_credential_binding_commit_current(rotated, old_reference)
    assert ensure_credential_binding_commit_current(rotated, new_reference) == "current"


@pytest.mark.parametrize("reason_code", ["owner_disconnected", "account_archived"])
def test_disconnect_disables_scheduling_and_fences_in_flight_poll(
    reason_code: DisconnectReasonV1,
) -> None:
    """M6-T010: disconnect/archive atomically invalidates collection authority."""
    active = _active_first_binding()
    reference = resolve_active_credential_binding(active)
    assert reference is not None

    disconnected = disconnect_active_credential_binding(
        active,
        expected_record_version=2,
        reason_code=reason_code,
    )

    assert disconnected.record_version == 3
    assert disconnected.binding_generation == 2
    assert disconnected.bindings[0].lifecycle == "cleanup_pending"
    assert resolve_active_credential_binding(disconnected) is None
    with pytest.raises(
        RegistryPolicyErrorV1,
        match="registry_credential_binding_stale",
    ):
        ensure_credential_binding_commit_current(disconnected, reference)


def test_disconnect_during_rotation_cleans_all_nonterminal_bindings() -> None:
    """M6-T005/T010: disconnect cannot leave a pending rotation behind."""
    active = _active_first_binding()
    rotating = prepare_credential_binding(
        active,
        binding_id=SECOND_BINDING_ID,
        expected_record_version=2,
    )

    disconnected = disconnect_active_credential_binding(
        rotating,
        expected_record_version=3,
        reason_code="owner_disconnected",
    )

    assert disconnected.record_version == 4
    assert disconnected.binding_generation == 2
    assert {item.lifecycle for item in disconnected.bindings} == {"cleanup_pending"}
    assert resolve_active_credential_binding(disconnected) is None


def test_disconnect_pending_only_enrollment_is_safe_and_idempotent() -> None:
    """M6-T004/T010: an unactivated enrollment remains owner-cleanable."""
    initial = new_credential_binding_aggregate(ACCOUNT_ID)
    pending = prepare_credential_binding(
        initial,
        binding_id=FIRST_BINDING_ID,
        expected_record_version=0,
    )

    disconnected = disconnect_active_credential_binding(
        pending,
        expected_record_version=1,
        reason_code="owner_disconnected",
    )

    assert disconnected.record_version == 2
    assert disconnected.binding_generation == 1
    assert disconnected.bindings[0].lifecycle == "cleanup_pending"
    replay = disconnect_active_credential_binding(
        disconnected,
        expected_record_version=2,
        reason_code="owner_disconnected",
    )
    assert replay == disconnected


def test_cleanup_completion_is_explicit_and_failed_clear_stays_pending() -> None:
    """M6-T010: only a confirmed local clear completes registry cleanup."""
    active = _active_first_binding()
    pending_cleanup = disconnect_active_credential_binding(
        active,
        expected_record_version=2,
        reason_code="owner_disconnected",
    )

    # A locked/unavailable/failed clear performs no transition.
    assert pending_cleanup.bindings[0].lifecycle == "cleanup_pending"

    completed = complete_credential_binding_cleanup(
        pending_cleanup,
        binding_id=FIRST_BINDING_ID,
        expected_record_version=3,
    )

    assert completed.record_version == 4
    assert completed.binding_generation == 2
    assert completed.bindings[0].lifecycle == "cleanup_complete"
    assert completed.bindings[0].reason_code == "local_cleanup_completed"
    replay = complete_credential_binding_cleanup(
        completed,
        binding_id=FIRST_BINDING_ID,
        expected_record_version=4,
    )
    assert replay == completed
    with pytest.raises(
        RegistryPolicyErrorV1,
        match="registry_credential_binding_state_invalid",
    ):
        complete_credential_binding_cleanup(
            active,
            binding_id=FIRST_BINDING_ID,
            expected_record_version=2,
        )


def test_stale_or_conflicting_per_account_mutation_is_rejected() -> None:
    """M6-T005: per-account optimistic serialization rejects stale commands."""
    active = _active_first_binding()

    with pytest.raises(
        RegistryPolicyErrorV1,
        match="registry_credential_binding_version_conflict",
    ):
        prepare_credential_binding(
            active,
            binding_id=SECOND_BINDING_ID,
            expected_record_version=1,
        )

    rotating = prepare_credential_binding(
        active,
        binding_id=SECOND_BINDING_ID,
        expected_record_version=2,
    )
    with pytest.raises(
        RegistryPolicyErrorV1,
        match="registry_credential_binding_conflict",
    ):
        prepare_credential_binding(
            rotating,
            binding_id=OpaqueIdV1(f"amcb_{'3' * 32}"),
            expected_record_version=3,
        )


def test_binding_aggregate_rejects_mixed_accounts_and_duplicate_ids() -> None:
    """M6-T004: one aggregate cannot share a binding across account records."""
    first = CredentialBindingRecordV1(
        account_id=ACCOUNT_ID,
        binding_id=FIRST_BINDING_ID,
        lifecycle="active",
        generation=1,
        association_provenance="owner_asserted",
        reason_code="owner_activated",
    )
    other_account = CredentialBindingRecordV1(
        account_id=OpaqueIdV1("account-2"),
        binding_id=SECOND_BINDING_ID,
        lifecycle="cleanup_pending",
        generation=1,
        association_provenance="owner_asserted",
        reason_code="owner_disconnected",
    )

    with pytest.raises(
        ValueError, match="registry_credential_binding_account_mismatch"
    ):
        CredentialBindingAggregateV1(
            account_id=ACCOUNT_ID,
            record_version=1,
            binding_generation=1,
            bindings=(first, other_account),
        )
    with pytest.raises(ValueError, match="registry_credential_binding_duplicate"):
        CredentialBindingAggregateV1(
            account_id=ACCOUNT_ID,
            record_version=1,
            binding_generation=1,
            bindings=(first, first),
        )


def test_archived_account_cannot_expose_active_binding() -> None:
    from agentmonitor.modules.registry.domain.credential_binding import (
        ensure_binding_visible_for_account,
    )

    active = _active_first_binding()
    ensure_binding_visible_for_account(active, account_lifecycle="active")
    with pytest.raises(
        RegistryPolicyErrorV1, match="registry_credential_binding_archived"
    ):
        ensure_binding_visible_for_account(active, account_lifecycle="archived")
    cleaned = disconnect_active_credential_binding(
        active,
        expected_record_version=active.record_version,
        reason_code="account_archived",
    )
    ensure_binding_visible_for_account(cleaned, account_lifecycle="archived")

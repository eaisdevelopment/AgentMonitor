"""Pure owner-association transitions; constructed inputs perform no I/O."""

from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.runtime_observation_v1 import ProcessIdentityV1
from agentmonitor.modules.runtime_observation.application.owner_associations import (
    transition_owner_association,
)
from agentmonitor.modules.runtime_observation.application.ports import (
    OwnerAssociationErrorV1,
    owner_association_key,
)

IDENTITY = ProcessIdentityV1("linux.proc.process.v1", "boot_scope_one", 123, 456)
ACCOUNT = OpaqueIdV1("account_one")
ACTOR = OpaqueIdV1("owner_one")
NOW = datetime(2026, 9, 29, tzinfo=UTC)


def test_process_selector_distinguishes_pid_reuse_and_boot() -> None:
    original = owner_association_key(IDENTITY)
    assert len(original) == 64
    assert original != owner_association_key(
        ProcessIdentityV1("linux.proc.process.v1", "boot_scope_one", 123, 457)
    )
    assert original != owner_association_key(
        ProcessIdentityV1("linux.proc.process.v1", "boot_scope_two", 123, 456)
    )


def test_confirm_replay_clear_and_tombstone_revision() -> None:
    confirmed = transition_owner_association(
        IDENTITY, "claude", ACCOUNT, None, 0, ACTOR, NOW
    )
    assert confirmed.account_id == ACCOUNT
    assert confirmed.record_version == 1
    replay = transition_owner_association(
        IDENTITY, "claude", ACCOUNT, confirmed, 0, ACTOR, NOW + timedelta(seconds=1)
    )
    assert replay == confirmed
    cleared = transition_owner_association(
        IDENTITY, "claude", None, confirmed, 1, ACTOR, NOW + timedelta(seconds=2)
    )
    assert cleared.account_id is None
    assert cleared.record_version == 2
    with pytest.raises(OwnerAssociationErrorV1, match="precondition_failed"):
        transition_owner_association(
            IDENTITY, "claude", ACCOUNT, cleared, 0, ACTOR, NOW
        )


def test_a_stale_different_account_cannot_overwrite_confirmation() -> None:
    confirmed = transition_owner_association(
        IDENTITY, "claude", ACCOUNT, None, 0, ACTOR, NOW
    )
    with pytest.raises(OwnerAssociationErrorV1, match="precondition_failed"):
        transition_owner_association(
            IDENTITY, "claude", OpaqueIdV1("account_two"), confirmed, 0, ACTOR, NOW
        )


def test_selector_changes_when_the_process_image_changes() -> None:
    assert owner_association_key(IDENTITY, "a" * 64) != owner_association_key(
        IDENTITY, "b" * 64
    )


def test_clearing_an_empty_slot_advances_its_version() -> None:
    cleared = transition_owner_association(
        IDENTITY, "claude", None, None, 0, ACTOR, NOW
    )
    assert cleared.account_id is None
    assert cleared.record_version == 1


def test_a_confirmation_record_cannot_be_used_for_another_process() -> None:
    confirmed = transition_owner_association(
        IDENTITY, "claude", ACCOUNT, None, 0, ACTOR, NOW
    )
    other = ProcessIdentityV1("linux.proc.process.v1", "boot_scope_one", 123, 457)
    with pytest.raises(OwnerAssociationErrorV1, match="process_identity_conflict"):
        transition_owner_association(other, "claude", ACCOUNT, confirmed, 1, ACTOR, NOW)

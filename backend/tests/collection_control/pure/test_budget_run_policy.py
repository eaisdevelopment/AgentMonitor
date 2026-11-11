"""Constructed billing targets and lease snapshots have no I/O behavior."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.adapters.persistence.collection_control.sqlite.budget import (
    BudgetCollectionError,
    BudgetLeaseSnapshot,
    decode_billing_target,
    encode_billing_target,
    require_budget_lease_current,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import (
    BillingAccessTargetV1,
    BillingConnectionViewV1,
)
from agentmonitor.contracts.registry_v1 import ActiveCredentialBindingRefV1

NOW = datetime(2026, 11, 11, tzinfo=UTC)


def pure_target() -> BillingAccessTargetV1:
    account = OpaqueIdV1("pure-account")
    return BillingAccessTargetV1(
        BillingConnectionViewV1(
            account,
            OpaqueIdV1("pure-resource"),
            "claude",
            None,
            "unresolved",
            2,
            "disabled",
            "pending",
            3,
            4,
            NOW,
            NOW,
        ),
        ActiveCredentialBindingRefV1(account, OpaqueIdV1("amcb_" + "a" * 32), 7),
        "verification",
    )


def test_target_roundtrip_preserves_exact_generations_without_profile_or_secret() -> (
    None
):
    target = pure_target()
    encoded = encode_billing_target(target)
    assert decode_billing_target(encoded) == target
    assert "profile" not in encoded
    assert "api_key" not in encoded
    assert "2026-11-11T00:00:00.000000Z" in encoded
    assert (
        encode_billing_target(
            replace(target, binding=replace(target.binding, generation=8))
        )
        != encoded
    )


@pytest.mark.parametrize(
    "mutation", ["unknown", "duplicate", "noncanonical", "enum", "oversize"]
)
def test_target_decoder_is_closed_and_bounded(mutation: str) -> None:
    encoded = encode_billing_target(pure_target())
    if mutation == "unknown":
        encoded = encoded[:-1] + ',"raw_provider_body":"forbidden"}'
    elif mutation == "duplicate":
        encoded = encoded[:-1] + ',"purpose":"verification"}'
    elif mutation == "noncanonical":
        encoded += " "
    elif mutation == "enum":
        encoded = encoded.replace('"verification"', '"unknown"')
    else:
        encoded = " " * 8193
    with pytest.raises(BudgetCollectionError):
        decode_billing_target(encoded)


def _lease() -> BudgetLeaseSnapshot:
    return BudgetLeaseSnapshot(
        "committing",
        2,
        2,
        3,
        3,
        OpaqueIdV1("pure-scheduler"),
        "running",
        None,
        None,
        NOW,
        NOW + timedelta(seconds=30),
    )


def test_current_lease_and_recovery_owner_are_both_explicit() -> None:
    lease = _lease()
    require_budget_lease_current(
        lease, scheduler_instance_id=lease.owner_instance_id, fencing_token=3, as_of=NOW
    )
    require_budget_lease_current(
        replace(lease, scheduler_state="reconciling"),
        scheduler_instance_id=lease.owner_instance_id,
        fencing_token=3,
        as_of=NOW,
    )


@pytest.mark.parametrize(
    "case",
    [
        "owner",
        "fence",
        "expired",
        "schedule_generation",
        "run_fence",
        "stopping",
        "completed",
        "future_heartbeat",
        "wrong_state",
    ],
)
def test_lease_cannot_authorize_obsolete_work(case: str) -> None:
    lease = _lease()
    owner, token = lease.owner_instance_id, 3
    if case == "owner":
        owner = OpaqueIdV1("other-owner")
    elif case == "fence":
        token = 4
    elif case == "expired":
        lease = replace(lease, expires_at=NOW)
    elif case == "schedule_generation":
        lease = replace(lease, schedule_generation=3)
    elif case == "run_fence":
        lease = replace(lease, run_fence=4)
    elif case == "stopping":
        lease = replace(lease, stopping_at=NOW)
    elif case == "completed":
        lease = replace(lease, completed_at=NOW)
    elif case == "future_heartbeat":
        lease = replace(lease, heartbeat_at=NOW + timedelta(seconds=1))
    else:
        lease = replace(lease, run_state="running")
    with pytest.raises(BudgetCollectionError, match="budget_run_fencing_conflict"):
        require_budget_lease_current(
            lease, scheduler_instance_id=owner, fencing_token=token, as_of=NOW
        )


def test_dispatch_checks_the_expected_queued_state_explicitly() -> None:
    lease = replace(_lease(), run_state="queued")
    require_budget_lease_current(
        lease,
        scheduler_instance_id=lease.owner_instance_id,
        fencing_token=3,
        as_of=NOW,
        expected_state="queued",
    )


def test_expired_lease_permits_only_same_owner_negative_terminal_cleanup() -> None:
    lease = replace(_lease(), run_state="running", expires_at=NOW)
    require_budget_lease_current(
        lease,
        scheduler_instance_id=lease.owner_instance_id,
        fencing_token=3,
        as_of=NOW,
        expected_state="running",
        transition_state="failed",
    )
    for state in ("committing", "succeeded", "partial"):
        with pytest.raises(BudgetCollectionError):
            require_budget_lease_current(
                lease,
                scheduler_instance_id=lease.owner_instance_id,
                fencing_token=3,
                as_of=NOW,
                expected_state="running",
                transition_state=state,
            )
    with pytest.raises(BudgetCollectionError):
        require_budget_lease_current(
            lease,
            scheduler_instance_id=OpaqueIdV1("new-owner"),
            fencing_token=3,
            as_of=NOW,
            expected_state="running",
            transition_state="failed",
        )

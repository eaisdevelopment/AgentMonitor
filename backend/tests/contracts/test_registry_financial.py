"""Pure financial identity contracts: no constructed facts cross I/O."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from agentmonitor.contracts import registry_billing_v1 as module
from agentmonitor.contracts.common_v1 import OpaqueIdV1, QueryAvailabilityV1

NOW = datetime(2026, 11, 12, tzinfo=UTC)


def unresolved() -> module.FinancialResourceScopeV1:
    return module.FinancialResourceScopeV1(
        account_id=OpaqueIdV1("account"),
        resource_id=OpaqueIdV1("resource"),
        provider_key="ollama",
        selector="self",
        scope_generation=1,
        provider_scope_id=None,
        scope_evidence="unresolved",
        binding_id=OpaqueIdV1("binding"),
        binding_generation=1,
    )


def test_unresolved_pool_identity_is_bound_to_the_exact_credential_lineage() -> None:
    scope = unresolved()
    assert scope.binding_generation == 1
    for change in (
        {"binding_id": None},
        {"binding_generation": None},
        {"binding_generation": True},
        {"scope_generation": 0},
        {"provider_scope_id": "known"},
        {"selector": "billing"},
    ):
        with pytest.raises(ValueError, match="financial_resource_scope_invalid"):
            replace(scope, **change)


def test_known_source_scope_is_distinct_from_owner_pool_association() -> None:
    known = replace(
        unresolved(),
        provider_key="claude",
        selector="billing",
        provider_scope_id="org-1",
        scope_evidence="owner_asserted",
        binding_id=None,
        binding_generation=None,
    )
    assert known.provider_scope_id == "org-1"
    with pytest.raises(ValueError, match="financial_resource_scope_invalid"):
        replace(known, binding_id=OpaqueIdV1("binding"), binding_generation=2)
    with pytest.raises(ValueError, match="financial_resource_scope_invalid"):
        replace(known, provider_scope_id=None)


def test_snapshot_rejects_missing_pool_cross_provider_and_duplicate_membership() -> (
    None
):
    scope = unresolved()
    pool = module.FinancialPoolViewV1(
        OpaqueIdV1("pool"), "ollama", None, 1, 1, NOW, NOW, "Owner pool", "self"
    )
    membership = module.FinancialPoolMembershipV1(
        OpaqueIdV1("association"),
        scope,
        pool.pool_id,
        "owner_asserted",
        NOW,
        None,
        1,
        1,
    )
    snapshot = module.FinancialPoolSnapshotV1(
        (scope.resource_id,),
        (pool,),
        (membership,),
        2,
        NOW,
        QueryAvailabilityV1("available", "financial_pool_snapshot_complete", NOW),
    )
    # Per-record revision may precede the atomic snapshot revision.
    assert snapshot.registry_revision == 2
    for change in (
        {"pools": ()},
        {"memberships": (membership, membership)},
        {"pools": (replace(pool, provider_key="codex", selector="billing"),)},
        {"pools": (replace(pool, selector="team"),)},
        {"resource_ids": ()},
        {"registry_revision": 0},
    ):
        with pytest.raises(ValueError, match="financial_pool_snapshot_invalid"):
            replace(snapshot, **change)
    with pytest.raises(ValueError, match="financial_pool_snapshot_invalid"):
        replace(
            snapshot,
            availability=QueryAvailabilityV1("unavailable", "registry_changed", NOW),
        )


def test_pool_owner_commands_require_exact_revision_and_unambiguous_intent() -> None:
    command = module.AssignFinancialPoolCommandV1(
        unresolved(),
        2,
        "create",
        None,
        None,
        OpaqueIdV1("owner"),
        OpaqueIdV1("command"),
        NOW,
    )
    for changes in (
        {"expected_registry_revision": 0},
        {"action": "join"},
        {"action": "unlink", "pool_id": OpaqueIdV1("pool")},
        {
            "action": "join",
            "pool_id": OpaqueIdV1("pool"),
            "primary_organization_id": OpaqueIdV1("group"),
        },
    ):
        with pytest.raises(ValueError, match="financial_pool_command_invalid"):
            replace(command, **changes)
    assert replace(command, action="join", pool_id=OpaqueIdV1("pool"))
    assert replace(command, action="unlink")


def test_pool_choices_identify_self_and_team_without_guessing() -> None:
    pool = module.FinancialPoolViewV1(
        OpaqueIdV1("pool"), "ollama", None, 1, 1, NOW, NOW, "Owner pool", "self"
    )
    assert pool.selector == "self"
    assert replace(pool, selector="team").selector == "team"
    with pytest.raises(ValueError, match="financial_pool_invalid"):
        replace(pool, selector="billing")

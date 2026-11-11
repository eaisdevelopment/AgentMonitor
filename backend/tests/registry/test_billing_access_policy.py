"""Pure billing authority: subscription login never grants or blocks API access."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import (
    BillingAccessPurposeV1,
    BillingAccessTargetV1,
    BillingConnectionViewV1,
)
from agentmonitor.contracts.registry_v1 import ActiveCredentialBindingRefV1
from agentmonitor.modules.registry.domain import billing_connection as policy


def connection() -> BillingConnectionViewV1:
    return BillingConnectionViewV1(
        account_id=OpaqueIdV1("account"),
        resource_id=OpaqueIdV1("resource"),
        provider_key="claude",
        scope_id=None,
        scope_evidence="unresolved",
        scope_generation=1,
        monitoring_preference="disabled",
        lifecycle="pending",
        record_version=1,
        registry_revision=1,
        created_at=datetime(2026, 11, 11, tzinfo=UTC),
        updated_at=datetime(2026, 11, 11, tzinfo=UTC),
    )


def binding() -> ActiveCredentialBindingRefV1:
    return ActiveCredentialBindingRefV1(
        OpaqueIdV1("account"), OpaqueIdV1("amcb_" + "a" * 32), 1
    )


def target(
    c: BillingConnectionViewV1 | None = None,
    b: ActiveCredentialBindingRefV1 | None = None,
    *,
    account_lifecycle: str = "pending",
    resource_lifecycle: str = "active",
    purpose: BillingAccessPurposeV1 = "verification",
) -> BillingAccessTargetV1:
    return policy.billing_access_target(
        connection() if c is None else c,
        binding() if b is None else b,
        account_lifecycle=account_lifecycle,
        resource_lifecycle=resource_lifecycle,
        purpose=purpose,
    )


def test_first_check_requires_neither_subscription_identity_nor_monitoring() -> None:
    current = target()
    assert current.connection == connection()
    assert current.binding == binding()
    assert current.purpose == "verification"
    policy.ensure_billing_access_current(current, current)


@pytest.mark.parametrize("state", ["archived", "disabled"])
def test_account_revocation_blocks_even_first_check(state: str) -> None:
    with pytest.raises(ValueError, match="billing_account_unavailable"):
        target(account_lifecycle=state)


@pytest.mark.parametrize("state", ["archived", "disabled", "pending"])
def test_nonactive_resource_blocks_access(state: str) -> None:
    with pytest.raises(ValueError, match="billing_resource_unavailable"):
        target(resource_lifecycle=state)


def test_pending_and_disabled_billing_cannot_collect_periodically() -> None:
    for current in (connection(), replace(connection(), lifecycle="active")):
        with pytest.raises(ValueError, match="billing_monitoring_disabled"):
            target(current, purpose="monitoring")
    active = replace(connection(), lifecycle="active", monitoring_preference="enabled")
    assert target(active, purpose="monitoring").connection == active


def test_disconnected_and_wrong_binding_are_rejected() -> None:
    with pytest.raises(ValueError, match="billing_connection_unavailable"):
        target(replace(connection(), lifecycle="disconnected"))
    with pytest.raises(ValueError, match="billing_binding_mismatch"):
        target(b=replace(binding(), account_id=OpaqueIdV1("other")))


@pytest.mark.parametrize(
    "change", ["binding", "generation", "scope", "resource", "version", "purpose"]
)
def test_changed_authority_cannot_commit_an_old_report(change: str) -> None:
    old = target()
    if change == "binding":
        new = target(b=replace(binding(), binding_id=OpaqueIdV1("amcb_" + "b" * 32)))
    elif change == "generation":
        new = target(b=replace(binding(), generation=2))
    elif change == "scope":
        new = target(
            replace(
                connection(),
                scope_generation=2,
                scope_id="org",
                scope_evidence="owner_asserted",
            )
        )
    elif change == "resource":
        new = target(replace(connection(), resource_id=OpaqueIdV1("new-resource")))
    elif change == "version":
        new = target(replace(connection(), record_version=2))
    else:
        new = target(
            replace(connection(), lifecycle="active", monitoring_preference="enabled"),
            purpose="monitoring",
        )
    with pytest.raises(ValueError, match="billing_access_changed"):
        policy.ensure_billing_access_current(new, old)

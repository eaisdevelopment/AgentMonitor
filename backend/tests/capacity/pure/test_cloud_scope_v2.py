"""Pure V2 scope coverage for real cloud-target membership contracts."""

from dataclasses import fields
from datetime import UTC, datetime

import pytest
from agentmonitor.contracts.capacity_v1 import (
    AccountCapacityViewV2,
    CapacityAggregateQueryV2,
    CapacitySubjectV2,
    InvalidCapacityContractV1,
    QuotaWindowViewV2,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    AccountViewV1,
    MaskedRegistryFieldV1,
    ProviderTargetRefV1,
    RegistryCloudResourceMembershipV2,
    RegistryScopeSnapshotV2,
)
from agentmonitor.modules.capacity.domain.aggregation import aggregate_capacity_v2
from agentmonitor.modules.capacity.domain.health import (
    default_capacity_health_policy_v1,
)

from backend.tests.capacity.pure.test_alert_conditions import _window

NOW = datetime(2026, 11, 2, 20, 0, tzinfo=UTC)
TARGET = ProviderTargetRefV1(
    target_kind="cloud_service",
    target_id=OpaqueIdV1("amat_" + "a" * 32),
)


def _account(name: str) -> AccountViewV1:
    return AccountViewV1(
        account_id=OpaqueIdV1(name),
        provider_key="ollama",
        friendly_name=name,
        organization_id=OpaqueIdV1("organization"),
        lifecycle="active",
        monitoring_preference="enabled",
        is_effective_monitoring_enabled=True,
        effective_monitoring_reason="enabled",
        identity_state="owner_confirmed",
        masked_identity=MaskedRegistryFieldV1(
            "withheld", None, "identity_privacy_minimized"
        ),
        record_version=1,
        registry_revision=7,
        created_at=NOW,
        updated_at=NOW,
        archived_at=None,
    )


def _membership(
    account: AccountViewV1, suffix: str
) -> RegistryCloudResourceMembershipV2:
    return RegistryCloudResourceMembershipV2(
        resource_id=OpaqueIdV1("cloud-resource-" + suffix),
        account_id=account.account_id,
        provider_key="ollama",
        provider_target=TARGET,
        relationship_state="unresolved",
        registry_revision=7,
    )


def _query() -> CapacityAggregateQueryV2:
    accounts = (_account("account-a"), _account("account-b"))
    memberships = (
        _membership(accounts[0], "a"),
        _membership(accounts[1], "b"),
    )
    snapshot = RegistryScopeSnapshotV2(
        scope_kind="organization",
        scope_id=OpaqueIdV1("organization"),
        organization_ids=(OpaqueIdV1("organization"),),
        account_ids=tuple(item.account_id for item in accounts),
        local_resource_ids=(),
        cloud_resources=memberships,
        completeness_state="complete",
        registry_revision=7,
    )
    return CapacityAggregateQueryV2(
        scope_snapshot=snapshot,
        accounts=accounts,
        local_resources=(),
        as_of=NOW,
        policy=default_capacity_health_policy_v1(),
    )


def _capacity(
    membership: RegistryCloudResourceMembershipV2,
    suffix: str,
    *,
    target: ProviderTargetRefV1 = TARGET,
) -> AccountCapacityViewV2:
    original = _window()
    subject = CapacitySubjectV2(
        provider_key="ollama",
        provider_target=target,
        account_id=membership.account_id,
        resource_id=membership.resource_id,
    )
    values = {item.name: getattr(original, item.name) for item in fields(original)}
    values.update(
        subject=subject,
        window_id=OpaqueIdV1("window-" + suffix),
        current_observation_id=OpaqueIdV1("observation-" + suffix),
        collection_run_id=OpaqueIdV1("run-" + suffix),
        registry_revision=7,
    )
    window = QuotaWindowViewV2(**values)
    return AccountCapacityViewV2(subject=subject, windows=(window,), health=None)


def test_unresolved_cloud_membership_is_covered_without_a_shared_pool_total() -> None:
    query = _query()
    first, second = query.scope_snapshot.cloud_resources
    result = aggregate_capacity_v2(
        query,
        (_capacity(first, "a"), _capacity(second, "b")),
    )

    assert result.covered_account_count == 2
    assert result.completeness == "partial"
    assert "pool_relationship_unknown" in result.reason_codes
    assert all(
        resource.relationship_state == "unresolved"
        for account in result.accounts
        for resource in account.cloud_resources
    )
    assert result.window_groups
    assert all(
        group.relationship_state == "unresolved" for group in result.window_groups
    )
    assert all(group.numeric_values == () for group in result.window_groups)


def test_missing_cloud_observation_remains_visible_as_missing_coverage() -> None:
    query = _query()
    result = aggregate_capacity_v2(
        query,
        (_capacity(query.scope_snapshot.cloud_resources[0], "a"),),
    )

    assert result.covered_account_count == 1
    assert result.missing_account_count == 1
    assert (
        result.missing_accounts[0].cloud_resources[0].relationship_state == "unresolved"
    )
    assert "capacity_scope_incomplete" in result.reason_codes


def test_cloud_capacity_target_must_match_the_exact_registry_membership() -> None:
    query = _query()
    mismatched = ProviderTargetRefV1(
        target_kind="cloud_service",
        target_id=OpaqueIdV1("amat_" + "b" * 32),
    )
    with pytest.raises(
        InvalidCapacityContractV1,
        match="capacity_aggregate_subject_outside_scope",
    ):
        aggregate_capacity_v2(
            query,
            (
                _capacity(
                    query.scope_snapshot.cloud_resources[0],
                    "a",
                    target=mismatched,
                ),
            ),
        )


def test_retained_nonmember_projection_does_not_hide_the_active_scope() -> None:
    query = _query()
    first, second = query.scope_snapshot.cloud_resources
    retained = RegistryCloudResourceMembershipV2(
        resource_id=OpaqueIdV1("retired-cloud-resource"),
        account_id=first.account_id,
        provider_key=first.provider_key,
        provider_target=first.provider_target,
        relationship_state="unresolved",
        registry_revision=query.scope_snapshot.registry_revision,
    )

    result = aggregate_capacity_v2(
        query,
        (
            _capacity(first, "a"),
            _capacity(second, "b"),
            _capacity(retained, "retired"),
        ),
    )

    assert result.covered_account_count == 2
    assert all(
        window.subject.resource_id != retained.resource_id
        for account in result.accounts
        for window in account.windows
    )
    assert retained.resource_id not in {
        resource_id
        for group in result.window_groups
        for resource_id in group.resource_ids
    }


def test_projection_for_an_account_outside_scope_remains_rejected() -> None:
    query = _query()
    outside = _membership(_account("account-outside"), "outside")

    with pytest.raises(
        InvalidCapacityContractV1,
        match="capacity_aggregate_subject_outside_scope",
    ):
        aggregate_capacity_v2(query, (_capacity(outside, "outside"),))


def test_cloud_membership_revision_is_fenced_by_the_scope_snapshot() -> None:
    query = _query()
    first = query.scope_snapshot.cloud_resources[0]
    with pytest.raises(ValueError, match="registry_scope_snapshot_invalid"):
        RegistryScopeSnapshotV2(
            scope_kind=query.scope_snapshot.scope_kind,
            scope_id=query.scope_snapshot.scope_id,
            organization_ids=query.scope_snapshot.organization_ids,
            account_ids=query.scope_snapshot.account_ids,
            local_resource_ids=(),
            cloud_resources=(
                RegistryCloudResourceMembershipV2(
                    resource_id=first.resource_id,
                    account_id=first.account_id,
                    provider_key=first.provider_key,
                    provider_target=first.provider_target,
                    relationship_state="unresolved",
                    registry_revision=8,
                ),
            ),
            completeness_state="complete",
            registry_revision=7,
        )

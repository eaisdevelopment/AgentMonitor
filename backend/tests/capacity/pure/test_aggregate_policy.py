"""M4-CAP-P01..05: deterministic registry scope and capacity policy facts."""

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from agentmonitor.contracts import capacity_v1 as contracts
from agentmonitor.contracts.common_quantity_v1 import ExactQuantityV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    AccountResourceViewV1,
    AccountViewV1,
    MaskedRegistryFieldV1,
    RegistryScopeSnapshotV1,
)
from agentmonitor.modules.capacity.application import queries

from backend.tests.capacity.pure.test_alert_conditions import _window

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _query() -> Any:
    query_type = getattr(contracts, "CapacityAggregateQueryV1", None)
    assert query_type is not None, "approved capacity aggregate contract is absent"
    policy = getattr(queries, "default_capacity_health_policy_v1", None)
    assert callable(policy), "approved M05 classification policy is not wired"
    masked = MaskedRegistryFieldV1("withheld", None, "domain_example")
    accounts = tuple(
        AccountViewV1(
            account_id=OpaqueIdV1(key),
            provider_key="domain_provider",
            friendly_name=key,
            organization_id=OpaqueIdV1("organization"),
            lifecycle="active",
            monitoring_preference="enabled" if enabled else "disabled",
            is_effective_monitoring_enabled=enabled,
            effective_monitoring_reason="enabled" if enabled else "monitoring_disabled",
            identity_state="owner_confirmed",
            masked_identity=masked,
            record_version=1,
            registry_revision=4,
            created_at=NOW,
            updated_at=NOW,
            archived_at=None,
        )
        for key, enabled in (("domain_a", True), ("domain_b", False))
    )
    resource = AccountResourceViewV1(
        resource_id=OpaqueIdV1("resource"),
        account_id=accounts[0].account_id,
        kind="subscription_pool",
        parent_resource_id=None,
        label=masked,
        lifecycle="active",
        linked_profile_ids=(),
        record_version=1,
        registry_revision=4,
        created_at=NOW,
        updated_at=NOW,
    )
    scope = RegistryScopeSnapshotV1(
        "organization",
        OpaqueIdV1("organization"),
        (OpaqueIdV1("organization"),),
        tuple(a.account_id for a in accounts),
        (resource.resource_id,),
        "complete",
        4,
    )
    return query_type(scope, accounts, (resource,), NOW, policy())


def _aggregate(query: Any = None, capacities: tuple[Any, ...] = ()) -> Any:
    calculate = getattr(queries, "aggregate_capacity_v1", None)
    assert callable(calculate), "approved pure fleet capacity behavior is absent"
    return calculate(_query() if query is None else query, capacities)


def test_no_reading_is_missing_and_disabled_account_is_excluded() -> None:
    result = _aggregate()
    assert tuple(i.value for i in result.eligible_account_ids) == ("domain_a",)
    assert result.covered_account_ids == ()
    assert tuple(i.account_id.value for i in result.missing_accounts) == ("domain_a",)
    assert tuple(i.account_id.value for i in result.excluded_accounts) == ("domain_b",)
    assert result.worst_health == "unknown"
    assert result.completeness == "unknown"
    assert result.registered_account_count == 2
    assert result.missing_account_count == 1
    assert result.excluded_account_count == 1
    assert result.window_groups == ()


def test_revision_race_rejects_mixed_registry_facts() -> None:
    query = _query()
    with pytest.raises(ValueError, match="registry_scope_changed"):
        replace(
            query,
            accounts=(
                replace(query.accounts[0], registry_revision=5),
                query.accounts[1],
            ),
        )


def test_duplicate_scope_members_cannot_double_count() -> None:
    query = _query()
    with pytest.raises(ValueError, match="capacity_aggregate_membership_invalid"):
        replace(query, accounts=query.accounts + (query.accounts[0],))


def test_fixed_m05_classification_defaults_are_independent_of_alert_rules() -> None:
    policy_factory = getattr(queries, "default_capacity_health_policy_v1", None)
    assert callable(policy_factory), "M05 classification policy is unconfigured"
    policy = policy_factory()
    assert policy.constrained_remaining_ratio.as_decimal() == Decimal("0.30")
    assert policy.critical_remaining_ratio.as_decimal() == Decimal("0.15")
    assert policy.policy_id == "capacity-health-default-v1"


def test_fresh_native_constraint_is_covered_without_an_invented_pool_total() -> None:
    query = _query()
    original = _window()
    subject = replace(original.subject, account_id=query.accounts[0].account_id)
    window = replace(original, subject=subject)
    result = _aggregate(
        query, (contracts.AccountCapacityViewV1(subject, (window,), None),)
    )
    assert result.covered_account_count == 1
    assert result.worst_health == "critical"
    assert result.completeness == "complete"
    assert result.window_groups[0].relationship_state == "unknown"
    assert result.window_groups[0].numeric_values == ()


def test_partial_fresh_scope_cannot_claim_available_or_complete() -> None:
    query = _query()
    original = _window()
    subject = replace(original.subject, account_id=query.accounts[0].account_id)
    ratio = replace(
        original.remaining_ratio,
        value=ExactQuantityV1.from_decimal(Decimal("0.8"), unit="ratio"),
    )
    window = replace(
        original, subject=subject, remaining_ratio=ratio, completeness="partial"
    )
    result = _aggregate(
        query, (contracts.AccountCapacityViewV1(subject, (window,), None),)
    )
    assert result.covered_account_count == 0
    assert result.missing_account_count == 1
    assert result.accounts[0].health.state == "unknown"
    assert result.accounts[0].health.completeness == "partial"
    assert result.completeness != "complete"


def test_stale_constraints_remain_missing_with_original_observation_lineage() -> None:
    query = _query()
    original = _window()
    subject = replace(original.subject, account_id=query.accounts[0].account_id)
    window = replace(original, subject=subject, freshness="stale")
    result = _aggregate(
        query, (contracts.AccountCapacityViewV1(subject, (window,), None),)
    )
    assert result.covered_account_count == 0
    assert result.missing_accounts[0].coverage == "missing"
    assert result.worst_health == "unknown"
    assert result.input_observation_ids == (window.current_observation_id,)

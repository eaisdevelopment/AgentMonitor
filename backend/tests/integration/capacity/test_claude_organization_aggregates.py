"""ST-FLEET-002: real organization capacity and retained per-account history."""

from datetime import UTC, datetime, timedelta

from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.contracts.capacity_v1 import (
    CapacityAggregateQueryV1,
    CapacityHistoryQueryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.capacity.application.queries import (
    GetCapacityAggregateV1,
    ListCapacityHistoryV1,
    default_capacity_health_policy_v1,
)
from agentmonitor.modules.registry.application.accounts import (
    AlertScopeAndSubjectQueryV1,
    ListAccountResourcesV1,
    ListAccountsV1,
)

from backend.tests.integration.collection_control.fleet_support import (
    selected_owner_fleet,
)


def test_actual_organization_aggregates_reconcile_membership_and_history() -> None:
    selected = selected_owner_fleet()
    registry = SqliteRegistryRepositoryV1(selected.reference)
    capacity = SqliteCapacityRepositoryV1(selected.reference)
    scope_query = AlertScopeAndSubjectQueryV1(registry)
    as_of = datetime.now(UTC)
    assert all(item.disposition == "verified" for item in selected.outcomes), (
        "m4_owner_unavailable_blocks_full_fleet"
    )
    for organization_id in {item.organization_id for item in selected.outcomes}:
        expected = {
            item.account_id
            for item in selected.outcomes
            if item.organization_id == organization_id
        }
        scope = scope_query("organization", OpaqueIdV1(organization_id))
        assert scope.completeness_state == "complete", "m4_registry_scope_partial"
        assert {item.value for item in scope.account_ids} == expected, (
            "m4_organization_membership_mismatch"
        )
        accounts = tuple(
            item
            for item in ListAccountsV1(registry)()
            if item.account_id in scope.account_ids
        )
        resources = tuple(
            resource
            for account in accounts
            for resource in ListAccountResourcesV1(registry)(account.account_id)
            if resource.resource_id in scope.resource_ids
        )
        aggregate = GetCapacityAggregateV1(capacity, scope_query)(
            CapacityAggregateQueryV1(
                scope,
                accounts,
                resources,
                as_of,
                default_capacity_health_policy_v1(),
            )
        )
        assert aggregate.registry_revision == scope.registry_revision
        assert aggregate.registered_account_count == len(expected)
        assert {item.account_id.value for item in aggregate.accounts} == expected
        assert aggregate.eligible_account_count == len(expected)
        assert set(aggregate.eligible_account_ids) == (
            set(aggregate.covered_account_ids)
            | {item.account_id for item in aggregate.missing_accounts}
        )
        assert all(not group.numeric_values for group in aggregate.window_groups), (
            "m4_incompatible_native_windows_were_summed"
        )
        for account in accounts:
            coverage = next(
                item
                for item in aggregate.accounts
                if item.account_id == account.account_id
            )
            windows = capacity.list_account_quota_windows(account.account_id, as_of)
            assert windows, "m4_account_quota_absent"
            assert {item.window_id for item in coverage.windows} == {
                item.window_id for item in windows
            }
            assert coverage.coverage in {"covered", "partial"}
            assert coverage.coverage == "covered" or coverage.reason_codes
            history = ListCapacityHistoryV1(capacity)(
                CapacityHistoryQueryV1(
                    account.account_id,
                    None,
                    None,
                    "remaining_ratio",
                    "poll_snapshot",
                    as_of - timedelta(days=365),
                    as_of,
                    as_of,
                    200,
                    None,
                    None,
                    None,
                )
            )
            assert history.items and history.availability.state == "available", (
                "m4_real_account_history_missing"
            )
            assert all(
                point.subject.account_id == account.account_id
                and point.collection_run_id
                and point.provenance.source_id
                for point in history.items
            )

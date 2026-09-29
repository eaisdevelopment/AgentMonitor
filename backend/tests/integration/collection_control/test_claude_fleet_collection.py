"""ST-FLEET-002: six owner-selected Claude accounts, genuine committed lineage."""

from datetime import UTC, datetime

from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)

from backend.tests.integration.collection_control.fleet_support import (
    selected_owner_fleet,
)


def test_owner_selected_six_account_collection_has_current_committed_lineage() -> None:
    selected = selected_owner_fleet()
    registry = SqliteRegistryRepositoryV1(selected.reference)
    capacity = SqliteCapacityRepositoryV1(selected.reference)
    collection = SqliteCollectionRepositoryV1(selected.reference)
    as_of = datetime.now(UTC)
    accounts = {row.account_id.value: row for row in registry.list_accounts("claude")}
    organizations = {
        row.organization_id.value
        for row in registry.list_organizations()
        if row.lifecycle == "active"
    }
    assert all(row.disposition == "verified" for row in selected.outcomes), (
        "m4_owner_unavailable_blocks_full_fleet"
    )
    for outcome in selected.outcomes:
        assert outcome.account_id in accounts, "m4_owner_account_not_registered"
        account = accounts[outcome.account_id]
        assert outcome.organization_id in organizations, "m4_owner_organization_missing"
        assert account.organization_id is not None, "m4_account_ungrouped"
        assert account.organization_id.value == outcome.organization_id, (
            "m4_owner_membership_mismatch"
        )
        assert account.lifecycle == "active", "m4_account_not_active"
        assert account.is_effective_monitoring_enabled, "m4_monitoring_not_enabled"
        assert account.identity_state in {"matched", "owner_confirmed"}, (
            "m4_registry_identity_unresolved"
        )
        windows = capacity.list_account_quota_windows(account.account_id, as_of)
        assert windows, "m4_real_quota_reading_missing"
        for window in windows:
            assert window.subject.account_id == account.account_id
            assert window.freshness == "fresh", "m4_current_quota_reading_required"
            assert window.provenance.source_id and window.provenance.provider_version
            assert window.collected_at <= as_of
            run = collection.get_run(window.collection_run_id)
            assert run is not None and run.account_id == account.account_id
            assert run.resource_id == window.subject.resource_id
            assert run.state in {"succeeded", "partial"}
            assert window.current_observation_id in run.observation_ids

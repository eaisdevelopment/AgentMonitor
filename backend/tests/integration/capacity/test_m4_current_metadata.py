"""M4-CAP-L02: read genuine selected owner data through production ports."""

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.contracts import capacity_v1 as contracts
from agentmonitor.modules.capacity.application import queries
from agentmonitor.modules.registry.application.accounts import (
    AlertScopeAndSubjectQueryV1,
    ListAccountResourcesV1,
    ListAccountsV1,
)


def test_real_current_windows_preserve_native_metadata() -> None:
    root_value = os.environ.get("AGENTMONITOR_TEST_DATA_ROOT")
    if root_value is None:
        pytest.skip("NOT RUN: select actual owner AgentMonitor data root")
    root = Path(root_value)
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    capacity = SqliteCapacityRepositoryV1(reference)
    accounts = ListAccountsV1(SqliteRegistryRepositoryV1(reference))("claude")
    observed = 0
    for account in accounts:
        for item in capacity.list_account_capacities(
            account.account_id, datetime.now(UTC)
        ):
            for window in item.windows:
                observed += 1
                assert getattr(window, "semantic_role", None), (
                    "stored native semantic role is hidden"
                )
                assert getattr(window, "definition_version", None), (
                    "stored definition version is hidden"
                )
                assert getattr(window, "registry_revision", None), (
                    "stored membership revision is hidden"
                )
                assert getattr(window, "projection_version", None), (
                    "stored projection generation is hidden"
                )
                assert window.reset_at is None or window.reset_precision != "unknown"
    if not observed:
        pytest.skip(
            "BLOCKED: actual selected database contains no native quota readings"
        )


def test_real_current_alert_facts_have_projection_generation_and_native_truth() -> None:
    root_value = os.environ.get("AGENTMONITOR_TEST_DATA_ROOT")
    if root_value is None:
        pytest.skip("NOT RUN: select actual owner AgentMonitor data root")
    root = Path(root_value)
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    capacity = SqliteCapacityRepositoryV1(reference)
    accounts = ListAccountsV1(SqliteRegistryRepositoryV1(reference))("claude")
    as_of = datetime.now(UTC)
    observed = 0
    for account in accounts:
        windows = capacity.list_account_quota_windows(account.account_id, as_of)
        if not windows:
            continue
        observed += len(windows)
        entry = getattr(queries, "ListCapacityAlertConditionsV1", None)
        assert callable(entry), "genuine current projections lack bounded alert query"
        query_type = getattr(contracts, "CapacityAlertConditionQueryV1", None)
        assert query_type is not None, "current alert query contract is unpublished"
        pages = []
        cursor = None
        while True:
            page = entry(capacity)(
                query_type(account.account_id, None, None, as_of, 1, cursor)
            )
            assert page.limit == 1
            assert len(page.items) <= 1
            pages.extend(page.items)
            if not page.has_more:
                break
            assert page.next_key != cursor
            cursor = page.next_key
        by_id = {window.window_id: window for window in windows}
        assert len(pages) == len(by_id)
        for fact in pages:
            window = by_id[fact.window_id]
            assert fact.generation == window.projection_version
            assert fact.observation_ids == (window.current_observation_id,)
            assert fact.observed_at == window.observed_at
            assert fact.recorded_at == window.stored_at
            if fact.availability == "current":
                assert window.freshness == "fresh"
                assert window.completeness == "complete"
                allowance = queries.GetQuotaAllowanceV1()(window)
                assert allowance is not None
                assert allowance.remaining_percentage.availability.state == "available"
                assert fact.remaining_basis_points is not None
                assert allowance.remaining_percentage.value is not None
                assert fact.remaining_basis_points.as_decimal() == (
                    allowance.remaining_percentage.value.as_decimal() * 100
                )
                assert fact.precision == allowance.remaining_percentage.precision
                assert fact.confidence == allowance.remaining_percentage.confidence
            else:
                assert fact.remaining_basis_points is None
                assert fact.exhausted is None
    if not observed:
        pytest.skip("BLOCKED: selected database has no genuine quota projections")


def test_real_fresh_native_percent_has_explained_remaining_condition() -> None:
    root_value = os.environ.get("AGENTMONITOR_TEST_DATA_ROOT")
    if root_value is None:
        pytest.skip("NOT RUN: select actual owner AgentMonitor data root")
    root = Path(root_value)
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    capacity = SqliteCapacityRepositoryV1(reference)
    as_of = datetime.now(UTC)
    observed = 0
    for account in ListAccountsV1(SqliteRegistryRepositoryV1(reference))("claude"):
        for window in capacity.list_account_quota_windows(account.account_id, as_of):
            if (
                window.freshness != "fresh"
                or window.completeness != "complete"
                or window.used.availability.state != "available"
                or window.used.value is None
                or window.used.value.unit != "percent"
                or window.remaining_ratio.availability.state == "available"
            ):
                continue
            observed += 1
            fact = queries.ListCapacityAlertConditionsV1(capacity)(
                contracts.CapacityAlertConditionQueryV1(
                    account.account_id, None, window.window_id, as_of
                )
            ).items[0]
            assert fact.availability == "current", (
                "fresh genuine native percent cannot yet produce remaining alert fact"
            )
            allowance = queries.GetQuotaAllowanceV1()(window)
            assert allowance is not None
            assert fact.remaining_basis_points is not None
            assert allowance.remaining_percentage.value is not None
            assert allowance.calculation == "100_minus_used_percent"
            assert fact.remaining_basis_points.as_decimal() == (
                allowance.remaining_percentage.value.as_decimal() * 100
            )
            assert fact.denominator_kind == "used_percent_complement"
            assert fact.precision == window.used.precision
            assert fact.confidence == window.used.confidence
    if not observed:
        pytest.skip("BLOCKED: actual source has no fresh native percent observations")


def test_real_registry_scope_aggregate_and_forecasts_preserve_no_value_states() -> None:
    root_value = os.environ.get("AGENTMONITOR_TEST_DATA_ROOT")
    if root_value is None:
        pytest.skip("NOT RUN: select actual owner AgentMonitor data root")
    root = Path(root_value)
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    registry = SqliteRegistryRepositoryV1(reference)
    capacity = SqliteCapacityRepositoryV1(reference)
    scope_query = AlertScopeAndSubjectQueryV1(registry)
    scope = scope_query("global")
    accounts = tuple(
        account
        for account in ListAccountsV1(registry)()
        if account.account_id in scope.account_ids
    )
    resources = tuple(
        resource
        for account in accounts
        for resource in ListAccountResourcesV1(registry)(account.account_id)
        if resource.resource_id in scope.resource_ids
    )
    as_of = datetime.now(UTC)
    aggregate = queries.GetCapacityAggregateV1(capacity, scope_query)(
        contracts.CapacityAggregateQueryV1(
            scope,
            accounts,
            resources,
            as_of,
            queries.default_capacity_health_policy_v1(),
        )
    )
    assert aggregate.registry_revision == scope.registry_revision
    assert aggregate.registered_account_count == len(accounts)
    assert set(aggregate.eligible_account_ids).isdisjoint(
        row.account_id for row in aggregate.excluded_accounts
    )
    assert set(aggregate.eligible_account_ids) == (
        set(aggregate.covered_account_ids)
        | {row.account_id for row in aggregate.missing_accounts}
    )
    assert all(group.numeric_values == () for group in aggregate.window_groups)
    explanations = 0
    for account in accounts:
        page = queries.ListCapacityForecastsV1(capacity)(
            contracts.CapacityForecastQueryV1(account.account_id, None, None, as_of)
        )
        for forecast in page.items:
            explanations += 1
            assert forecast.input_observation_ids
            assert forecast.input_set_digest
            if forecast.state != "available":
                assert forecast.burn_rate is None
                assert forecast.earliest_exhaustion_at is None
                assert forecast.latest_exhaustion_at is None
                assert forecast.reason_codes
            else:
                assert forecast.burn_rate is not None
                assert forecast.burn_rate.sample_count >= 3
    if not explanations:
        pytest.skip("BLOCKED: actual database has no forecast input history")


def test_real_existing_outbox_has_typed_bounded_replay() -> None:
    root_value = os.environ.get("AGENTMONITOR_TEST_DATA_ROOT")
    if root_value is None:
        pytest.skip("NOT RUN: select actual owner AgentMonitor data root")
    root = Path(root_value)
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    capacity = SqliteCapacityRepositoryV1(reference)
    as_of = datetime.now(UTC)
    receipts = []
    for account in ListAccountsV1(SqliteRegistryRepositoryV1(reference))("claude"):
        for window in capacity.list_account_quota_windows(account.account_id, as_of):
            status = capacity.get_commit_status(
                window.collection_run_id, window.provenance.capability_id
            )
            if status.receipt is not None:
                receipts.append(status.receipt)
    if not receipts:
        pytest.skip("BLOCKED: actual database has no genuine committed events")
    entry = getattr(queries, "ReadCapacityEventsV1", None)
    assert callable(entry), "genuine persisted outbox lacks typed bounded read port"
    first = entry(capacity)("m4-capacity-read-verification", None, as_of, 1)
    assert len(first.events) == 1
    assert first.next_cursor
    second = entry(capacity)(
        "m4-capacity-read-verification", first.next_cursor, as_of, 1
    )
    assert all(
        e.envelope.event_id != first.events[0].envelope.event_id for e in second.events
    )
    again = entry(capacity)("m4-capacity-read-verification", None, as_of, 1)
    assert again == first
    for event in first.events + second.events:
        assert event.payload.projection_count >= 1
        assert event.payload.state in {"succeeded", "partial"}
        assert event.payload_digest == queries.capacity_event_payload_digest_v1(
            event.payload
        )
        assert event.envelope.producer_version
        assert event.stream_sequence >= 1
        assert event.envelope.recorded_at >= event.envelope.occurred_at

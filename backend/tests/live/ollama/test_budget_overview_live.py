"""Compare compact Overview with genuine reports/funds through public read ports."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
    SqliteBillingConnectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
    SqliteCredentialBindingsV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.composition.budget_funds import StoredAccountBudgetFundsV1
from agentmonitor.contracts.budget_query_v1 import BudgetOverviewQueryV1
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1, BudgetReportSelectionV1
from agentmonitor.contracts.collection_control_v1 import BudgetCollectionRunViewV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import ActiveCredentialBindingRefV1
from agentmonitor.modules.capacity.application.budget_queries import (
    GetAccountBudgetCurrentV1,
)
from agentmonitor.modules.capacity.application.queries import ListQuotaWindowsV1
from agentmonitor.modules.capacity.domain.budget_account_spend import reported_spend
from agentmonitor.modules.capacity.domain.budget_money import remaining_percentage
from agentmonitor.modules.registry.application.accounts import (
    CapacityScopeMembershipQueryV2,
    GetAccountV1,
    ListAccountResourcesV1,
    ListAccountsV1,
)
from agentmonitor.modules.registry.domain.credential_binding import (
    resolve_active_credential_binding,
)

from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)


def test_genuine_overview_preserves_report_funds_and_full_filtered_summaries(
    tmp_path: Path,
) -> None:
    from agentmonitor.modules.capacity.application.budget_overview import (
        ListBudgetOverviewV1,
    )

    reference = _private_real_copy(tmp_path)
    registry = SqliteRegistryRepositoryV1(reference)
    runs = SqliteCollectionRepositoryV1(reference)
    reports = SqliteBudgetReportRepositoryV1(reference)
    bindings = SqliteCredentialBindingsV1(reference)
    now = datetime.now(UTC)
    genuine_runs = tuple(
        run
        for run in runs.list_runs("ollama", None, now, 500)
        if isinstance(run, BudgetCollectionRunViewV1)
        and run.source_id == "ollama.cloud.usage.v1"
        and run.state == "succeeded"
        and run.report_id is not None
        and run.account_id is not None
    )
    assert genuine_runs, "genuine_stored_usage_report_required"
    run = genuine_runs[0]
    assert run.account_id is not None and run.report_id is not None
    stored = reports.get_report(run.account_id, run.report_id)
    assert stored is not None

    def active_binding(account: OpaqueIdV1) -> ActiveCredentialBindingRefV1 | None:
        return resolve_active_credential_binding(bindings.read(account))

    current = GetAccountBudgetCurrentV1(
        SqliteBillingConnectionRepositoryV1(reference),
        reports,
        runs,
        StoredAccountBudgetFundsV1(
            CapacityScopeMembershipQueryV2(registry),
            ListQuotaWindowsV1(SqliteCapacityRepositoryV1(reference)),
            active_binding=active_binding,
            get_run=runs.get_run,
        ),
        active_binding=active_binding,
        cloud_target=SqliteCloudCredentialRegistryV1(reference).read_monitoring_target,
    )
    overview = ListBudgetOverviewV1(
        ListAccountsV1(registry), current, ListAccountResourcesV1(registry)
    )
    query = BudgetOverviewQueryV1(
        stored.report.requested_period, now, provider_key="ollama", limit=200
    )
    result = overview(query)
    assert result.page.availability.state == "available", (
        result.page.availability.reason_code
    )
    assert not result.page.has_more, "live_inventory_exceeds_this_bounded_comparison"
    assert result.period == stored.report.requested_period
    assert result.as_of == now
    detail = current(run.account_id, period=query.period, as_of=now)
    assert detail is not None
    assert detail.funds is not None and detail.funds.components
    local_resources = ListAccountResourcesV1(registry)(run.account_id)
    assert detail.cloud_resources, "genuine_cloud_graph_required"
    assert not any(
        item.kind == "subscription_pool" and item.lifecycle == "active"
        for item in local_resources
    ), "genuine_cloud_only_resource_required"
    assert run.account_id not in result.subscription_account_ids
    cloud_rows = tuple(
        row
        for row in result.page.items
        if row.account.account_id == run.account_id and row.resource_kind == "cloud"
    )
    assert len(cloud_rows) == 1
    row = cloud_rows[0]
    cloud = next(
        item
        for item in detail.cloud_resources
        if item.target.resource_id == row.resource_id
    )
    selected = {
        report.report_id: report
        for selection in cloud.reports
        if (report := selection.current or selection.latest_attempt) is not None
    }
    spend = {item.report_id: item for item in cloud.reported_spend}
    assert {context.report_id for context in row.contexts} == set(selected)
    assert stored.report_id in selected
    for context in row.contexts:
        source_report = selected[context.report_id].report
        assert context.spend == spend[context.report_id].total
        assert context.spend_reason == spend[context.report_id].reason_code
        assert context.source_id == source_report.source_id
        assert context.source_category == source_report.source_category
        assert context.cost_basis == source_report.cost_basis
        assert context.currency == source_report.currency
        assert context.source_data_through == source_report.source_data_through
        assert context.collected_at == source_report.collected_at
        if not source_report.cost_buckets and not source_report.empty_means_zero:
            assert context.spend is None
    source_funds = {
        item.component_id: item
        for item in detail.funds.components
        if item.subject.resource_id == row.resource_id
    }
    assert {item.component_id for item in row.funds} == set(source_funds)
    for fund in row.funds:
        source = source_funds[fund.component_id]
        assert fund.remaining == source.remaining
        assert fund.limit == source.limit
        assert fund.observation_id == source.observation_id
        assert fund.collected_at == source.collected_at
        assert fund.observed_at == source.observed_at
        assert fund.is_constraining == source.is_constraining
        ratio = remaining_percentage(
            source.remaining.value, source.limit.value, compatible=True
        )
        assert fund.percentage_text == (ratio.percentage_text if ratio else None)
        assert fund.is_low == (ratio.is_low_remaining if ratio else None)
    # Real Ollama scopes remain unresolved; they cannot create a subtotal.
    assert all(context.scope_evidence == "unresolved" for context in row.contexts)
    assert result.summaries == ()
    assert result.summary_reason == "unresolved_overlap"
    assert any(item.reason_code == "unresolved_overlap" for item in result.exclusions)

    paged = overview(replace(query, limit=1))
    collected = list(paged.page.items)
    while paged.page.has_more:
        assert paged.page.next_key is not None
        paged = overview(replace(query, limit=1, after_key=paged.page.next_key))
        assert paged.summaries == result.summaries
        assert paged.exclusions == result.exclusions
        assert paged.inventory_count == result.inventory_count
        collected.extend(paged.page.items)
        assert len(collected) <= len(result.page.items)
    assert tuple(item.row_id for item in collected) == tuple(
        item.row_id for item in result.page.items
    )
    no_groups = overview(replace(query, organization_ids=(), include_ungrouped=False))
    assert no_groups.page.items == ()
    assert no_groups.inventory_count == 0


def test_genuine_selected_report_is_exact_and_rejects_other_contexts(
    tmp_path: Path,
) -> None:
    from agentmonitor.modules.capacity.application.budget_selected import (
        GetSelectedBudgetReportV1,
    )

    reference = _private_real_copy(tmp_path)
    reports = SqliteBudgetReportRepositoryV1(reference)
    runs = SqliteCollectionRepositoryV1(reference)
    now = datetime.now(UTC)
    genuine_runs = tuple(
        run
        for run in runs.list_runs("ollama", None, now, 500)
        if isinstance(run, BudgetCollectionRunViewV1)
        and run.source_id == "ollama.cloud.usage.v1"
        and run.state == "succeeded"
        and run.report_id is not None
        and run.account_id is not None
    )
    assert genuine_runs, "genuine_stored_usage_report_required"
    run = genuine_runs[0]
    assert run.account_id is not None and run.report_id is not None
    stored = reports.get_report(run.account_id, run.report_id)
    assert stored is not None
    account_id, resource_id = (
        stored.report.subject.account_id,
        stored.report.subject.resource_id,
    )
    assert account_id is not None and resource_id is not None
    query = GetSelectedBudgetReportV1(
        GetAccountV1(SqliteRegistryRepositoryV1(reference)), reports
    )
    period = stored.report.requested_period
    selected = query(
        account_id, resource_id, stored.report_id, period=period, as_of=now
    )
    assert selected is not None
    assert selected.report == stored
    assert selected.reported_spend == reported_spend(
        BudgetReportSelectionV1(stored, stored)
    )
    assert selected.as_of == now
    assert (
        query(
            account_id,
            OpaqueIdV1("unrelated-resource"),
            stored.report_id,
            period=period,
            as_of=now,
        )
        is None
    )
    assert (
        query(
            OpaqueIdV1("unrelated-account"),
            resource_id,
            stored.report_id,
            period=period,
            as_of=now,
        )
        is None
    )
    assert (
        query(
            account_id,
            resource_id,
            OpaqueIdV1("not-retained"),
            period=period,
            as_of=now,
        )
        is None
    )
    assert (
        query(
            account_id,
            resource_id,
            stored.report_id,
            period=BudgetPeriodV1(
                period.start - timedelta(days=1), period.end - timedelta(days=1)
            ),
            as_of=now,
        )
        is None
    )
    assert (
        query(
            account_id,
            resource_id,
            stored.report_id,
            period=period,
            as_of=stored.stored_at - timedelta(microseconds=1),
        )
        is None
    )

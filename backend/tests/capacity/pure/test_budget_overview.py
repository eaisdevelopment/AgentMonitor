"""Pure Overview policy; constructed metadata and money never enter I/O."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from agentmonitor.contracts.budget_query_v1 import (
    AccountBudgetCurrentV1,
    BudgetOverviewQueryV1,
    BudgetResourceCurrentV1,
)
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1, BudgetReportSelectionV1
from agentmonitor.contracts.common_v1 import (
    OpaqueIdV1,
    QueryAvailabilityV1,
    QueryPageV1,
)
from agentmonitor.contracts.registry_billing_v1 import BillingConnectionViewV1
from agentmonitor.contracts.registry_v1 import (
    AccountResourceViewV1,
    AccountViewV1,
    MaskedRegistryFieldV1,
    ResourceKindV1,
)

NOW = datetime(2026, 11, 11, 1, tzinfo=UTC)
PERIOD = BudgetPeriodV1(NOW.replace(hour=0) - timedelta(days=7), NOW.replace(hour=0))


def _account(index: int = 0) -> AccountViewV1:
    return AccountViewV1(
        OpaqueIdV1("pure-account" if index == 0 else f"account-{index:04}"),
        "claude",
        f"Account {index}",
        None,
        "active",
        "disabled",
        False,
        "monitoring_disabled",
        "owner_confirmed",
        MaskedRegistryFieldV1("unknown", None, "not_reported"),
        1,
        1,
        NOW,
        NOW,
        None,
        "api",
    )


def _resource(
    kind: ResourceKindV1 = "api_organization", resource_id: str = "pure-pool"
) -> AccountResourceViewV1:
    return AccountResourceViewV1(
        OpaqueIdV1(resource_id),
        _account().account_id,
        kind,
        None,
        MaskedRegistryFieldV1("unknown", None, "not_reported"),
        "active",
        (),
        1,
        1,
        NOW,
        NOW,
    )


def _current(*, counts_only: bool = False) -> AccountBudgetCurrentV1:
    from agentmonitor.modules.capacity.domain.budget_account_spend import reported_spend

    from backend.tests.capacity.pure.test_budget_report_selection import _report

    report = _report(1, None if counts_only else "0.30")
    payload = replace(
        report.report,
        requested_period=PERIOD,
        covered_period=PERIOD,
        cost_buckets=tuple(
            replace(b, period=PERIOD) for b in report.report.cost_buckets
        ),
        currency=None if counts_only else "USD",
        empty_means_zero=False,
        source_data_through=PERIOD.end,
        collected_at=NOW,
    )
    report = replace(report, report=payload, stored_at=NOW)
    selection = BudgetReportSelectionV1(report, report)
    spend = reported_spend(selection)
    assert spend is not None
    available = QueryAvailabilityV1("available", "read", NOW)
    connection = BillingConnectionViewV1(
        _account().account_id,
        OpaqueIdV1("pure-pool"),
        "claude",
        "pure-scope",
        "provider_verified",
        1,
        "enabled",
        "active",
        1,
        1,
        NOW,
        NOW,
    )
    return AccountBudgetCurrentV1(
        _account().account_id,
        PERIOD,
        NOW,
        available,
        (
            BudgetResourceCurrentV1(
                connection, (selection,), available, (spend,), None, available
            ),
        ),
    )


def test_filters_distinguish_all_none_and_explicit_ungrouped() -> None:
    from agentmonitor.modules.capacity.domain.budget_overview import account_matches

    account = _account()
    query = BudgetOverviewQueryV1(PERIOD, NOW)
    assert account_matches(account, query)
    assert not account_matches(account, replace(query, organization_ids=()))
    assert account_matches(
        account, replace(query, organization_ids=(), include_ungrouped=True)
    )
    assert not account_matches(account, replace(query, provider_key="codex"))
    assert not account_matches(
        replace(account, lifecycle="archived", archived_at=NOW), query
    )
    grouped = replace(account, organization_id=OpaqueIdV1("org"))
    assert account_matches(
        grouped, replace(query, organization_ids=(OpaqueIdV1("org"),))
    )
    assert not account_matches(
        grouped, replace(query, organization_ids=(), include_ungrouped=True)
    )


def test_actual_resources_override_creation_purpose_for_subscriptions() -> None:
    from agentmonitor.modules.capacity.domain.budget_overview import has_subscription

    account = _account()
    assert not has_subscription(account, ())
    assert has_subscription(replace(account, initial_connection_purpose=None), ())
    assert has_subscription(account, (_resource("subscription_pool"),))
    assert not has_subscription(
        replace(account, initial_connection_purpose=None), (_resource(),)
    )
    assert not has_subscription(
        account, (replace(_resource("subscription_pool"), lifecycle="retired"),)
    )


def test_compact_spend_and_counts_only_keep_report_identity_without_bodies() -> None:
    from agentmonitor.modules.capacity.domain.budget_overview import project_budget_rows

    query = BudgetOverviewQueryV1(PERIOD, NOW)
    for counts_only in (False, True):
        rows = project_budget_rows(
            _account(), (_resource(),), _current(counts_only=counts_only), query
        )
        assert len(rows) == 1
        row = rows[0]
        assert (
            row.monitoring_enabled
        )  # Independent billing monitoring, not subscription.
        assert len(row.row_id) == 64
        original = _current().resources[0].reports[0].current
        assert original is not None
        assert row.contexts[0].report_id == original.report_id
        assert not hasattr(row.contexts[0], "cost_buckets")
        if counts_only:
            assert row.contexts[0].spend is None
            assert row.contexts[0].spend_reason == "cost_not_reported"
        else:
            assert row.contexts[0].spend is not None
            assert row.contexts[0].spend.amount.as_decimal() == Decimal("0.30")


def test_pending_api_without_data_is_preserved_and_never_subscription() -> None:
    from agentmonitor.modules.capacity.domain.budget_overview import project_budget_rows

    account = replace(_account(), identity_state="unresolved", lifecycle="pending")
    rows = project_budget_rows(account, (), None, BudgetOverviewQueryV1(PERIOD, NOW))
    assert len(rows) == 1
    assert rows[0].resource_kind == "unconfigured"
    assert rows[0].state_rank == 0
    assert rows[0].contexts == ()


@pytest.mark.parametrize("has_counts", [False, True])
@pytest.mark.parametrize("has_watermark", [False, True])
def test_complete_coverage_without_money_is_not_incomplete(
    has_counts: bool, has_watermark: bool
) -> None:
    from agentmonitor.contracts.capacity_v1 import BudgetUsageBucketV1
    from agentmonitor.contracts.common_quantity_v1 import (
        CanonicalDecimalV1,
        ExactQuantityV1,
    )
    from agentmonitor.modules.capacity.domain.budget_overview import project_budget_rows

    current = _current(counts_only=True)
    original = current.resources[0].reports[0].current
    assert original is not None
    counts = BudgetUsageBucketV1(
        "requests", PERIOD, ExactQuantityV1(CanonicalDecimalV1("42", 0), "request"), ()
    )
    report = replace(
        original,
        report=replace(
            original.report,
            usage_buckets=(counts,) if has_counts else (),
            source_data_through=PERIOD.end if has_watermark else None,
        ),
    )
    current = replace(
        current,
        resources=(
            replace(
                current.resources[0], reports=(BudgetReportSelectionV1(report, report),)
            ),
        ),
    )
    row = project_budget_rows(
        _account(), (_resource(),), current, BudgetOverviewQueryV1(PERIOD, NOW)
    )[0]
    assert row.state_code == ("current" if has_watermark else "freshness_unknown")
    assert row.contexts[0].completeness == "complete"
    assert row.contexts[0].spend is None
    assert row.contexts[0].spend_reason == "cost_not_reported"
    assert row.contexts[0].source_data_through == (
        PERIOD.end if has_watermark else None
    )


@pytest.mark.parametrize("short_coverage", [False, True])
def test_missing_money_does_not_hide_genuinely_incomplete_coverage(
    short_coverage: bool,
) -> None:
    from agentmonitor.modules.capacity.domain.budget_overview import project_budget_rows

    current = _current(counts_only=True)
    original = current.resources[0].reports[0].current
    assert original is not None
    payload = (
        replace(
            original.report,
            covered_period=BudgetPeriodV1(PERIOD.start, PERIOD.end - timedelta(days=1)),
        )
        if short_coverage
        else replace(
            original.report, completeness="partial", omission_codes=("missing_page",)
        )
    )
    report = replace(original, report=payload)
    current = replace(
        current,
        resources=(
            replace(
                current.resources[0], reports=(BudgetReportSelectionV1(None, report),)
            ),
        ),
    )
    row = project_budget_rows(
        _account(), (_resource(),), current, BudgetOverviewQueryV1(PERIOD, NOW)
    )[0]
    assert row.state_code == "incomplete"
    assert row.contexts[0].spend is None
    assert row.contexts[0].spend_reason == "report_incomplete"


def test_inventory_pages_reject_revision_changes_duplicates_and_overflow() -> None:
    from agentmonitor.modules.capacity.domain.budget_overview import (
        append_inventory_page,
    )

    first = tuple(_account(i) for i in range(200))
    page = QueryPageV1(
        first, 200, True, "next", QueryAvailabilityV1("available", "read", NOW)
    )
    inventory = append_inventory_page((), page, NOW)
    last = QueryPageV1((_account(200),), 200, False, None, page.availability)
    assert len(append_inventory_page(inventory, last, NOW)) == 201
    with pytest.raises(ValueError, match="budget_overview_registry_changed"):
        append_inventory_page(
            inventory,
            replace(last, items=(replace(_account(200), registry_revision=2),)),
            NOW,
        )
    with pytest.raises(ValueError, match="budget_overview_inventory_invalid"):
        append_inventory_page(inventory, replace(last, items=(_account(0),)), NOW)
    with pytest.raises(ValueError, match="budget_overview_inventory_overflow"):
        append_inventory_page(tuple(_account(i) for i in range(2000)), last, NOW)


def test_page_cursor_pins_context_snapshot_and_summaries_never_infer_pools() -> None:
    from agentmonitor.modules.capacity.domain.budget_overview import (
        overview_result,
        project_budget_rows,
    )

    query = BudgetOverviewQueryV1(PERIOD, NOW, limit=1)
    first = project_budget_rows(_account(), (_resource(),), _current(), query)[0]
    other = replace(
        first, row_id="f" * 64, account=_account(1), resource_id=OpaqueIdV1("other")
    )
    result = overview_result(
        (other, first),
        query,
        registry_revision=1,
        inventory_count=2,
        subscription_account_ids=(),
    )
    assert result.inventory_count == 2 and result.summaries == ()
    assert result.exclusions[0].reason_code == "unresolved_overlap"
    assert result.exclusions[0].count == 2
    assert result.page.has_more and len(result.page.next_key or "") == 64
    second = overview_result(
        (first, other),
        replace(query, after_key=result.page.next_key),
        registry_revision=1,
        inventory_count=2,
        subscription_account_ids=(),
    )
    assert len(second.page.items) == 1 and not second.page.has_more
    assert second.page.items[0].row_id != result.page.items[0].row_id
    with pytest.raises(ValueError, match="budget_overview_cursor_expired"):
        overview_result(
            (first, other),
            replace(query, after_key=result.page.next_key, include_ungrouped=True),
            registry_revision=1,
            inventory_count=2,
            subscription_account_ids=(),
        )


def _funds_current() -> tuple[
    AccountViewV1, AccountResourceViewV1, AccountBudgetCurrentV1
]:
    from agentmonitor.adapters.providers.ollama.api.funds_projection import (
        project_funds,
    )
    from agentmonitor.contracts.budget_query_v1 import AccountBudgetFundsV1

    from backend.tests.providers.ollama.pure.test_funds_projection import _window

    component = project_funds(
        replace(
            _window(),
            provenance=replace(
                _window().provenance, freshness_deadline=NOW + timedelta(minutes=15)
            ),
        ),
        as_of=NOW,
    )
    assert component is not None
    account = replace(
        _account(),
        provider_key="ollama",
        monitoring_preference="enabled",
        is_effective_monitoring_enabled=True,
        effective_monitoring_reason="monitoring_enabled",
    )
    current = AccountBudgetCurrentV1(
        account.account_id,
        PERIOD,
        NOW,
        QueryAvailabilityV1("available", "read", NOW),
        (),
        AccountBudgetFundsV1(
            account.account_id,
            NOW,
            QueryAvailabilityV1("partial", "funds_scope_unresolved", NOW),
            (component,),
            1,
        ),
    )
    return account, _resource("prepaid_credit_pool", "pure-resource"), current


def test_funds_only_preserves_exact_ratio_lineage_and_no_false_exhaustion() -> None:
    from agentmonitor.modules.capacity.domain.budget_overview import project_budget_rows

    account, resource, current = _funds_current()
    query = BudgetOverviewQueryV1(PERIOD, NOW)
    row = project_budget_rows(account, (resource,), current, query)[0]
    assert row.contexts == () and row.resource_kind == "cloud"
    assert row.state_code == "current"
    fund = row.funds[0]
    assert current.funds is not None
    component = current.funds.components[0]
    assert fund.remaining == component.remaining and fund.limit == component.limit
    assert fund.observation_id == component.observation_id
    assert fund.percentage_text == "0.00" and fund.is_low is True
    assert fund.is_constraining is False  # A low component does not imply exhaustion.
    assert fund.percentage_method == "remaining-over-limit-percent-v1"
    assert (
        fund.percentage_decimal_places == 2 and fund.percentage_rounding == "half_even"
    )
    constraining = replace(component, is_constraining=True)
    low = replace(current, funds=replace(current.funds, components=(constraining,)))
    assert project_budget_rows(account, (resource,), low, query)[0].state_code == "low"
    stale = replace(
        current,
        funds=replace(
            current.funds, components=(replace(constraining, freshness="stale"),)
        ),
    )
    assert (
        project_budget_rows(account, (resource,), stale, query)[0].state_code == "stale"
    )


def test_partial_funds_and_unavailable_report_read_are_not_current() -> None:
    from agentmonitor.modules.capacity.domain.budget_overview import project_budget_rows

    account, resource, current = _funds_current()
    assert current.funds is not None
    partial = replace(current.funds.components[0], completeness="partial")
    current = replace(current, funds=replace(current.funds, components=(partial,)))
    query = BudgetOverviewQueryV1(PERIOD, NOW)
    assert (
        project_budget_rows(account, (resource,), current, query)[0].state_code
        == "incomplete"
    )


def test_unavailable_report_read_is_not_current() -> None:
    from agentmonitor.modules.capacity.domain.budget_overview import project_budget_rows

    query = BudgetOverviewQueryV1(PERIOD, NOW)
    billing = _current()
    billing = replace(
        billing,
        resources=(
            replace(
                billing.resources[0],
                report_availability=QueryAvailabilityV1(
                    "unavailable", "query_failed", NOW
                ),
            ),
        ),
    )
    assert (
        project_budget_rows(_account(), (_resource(),), billing, query)[0].state_code
        == "budget_query_unavailable"
    )


def test_projection_rejects_cross_provider_funds_and_wrong_report_resource() -> None:
    from agentmonitor.modules.capacity.domain.budget_overview import project_budget_rows

    account, resource, current = _funds_current()
    query = BudgetOverviewQueryV1(PERIOD, NOW)
    with pytest.raises(ValueError, match="budget_overview_funds_context_invalid"):
        project_budget_rows(
            replace(account, provider_key="codex"), (resource,), current, query
        )
    billing = _current()
    selection = billing.resources[0].reports[0]
    assert selection.current is not None
    wrong = replace(
        selection.current,
        report=replace(
            selection.current.report,
            subject=replace(
                selection.current.report.subject,
                resource_id=OpaqueIdV1("wrong-resource"),
            ),
        ),
    )
    billing = replace(
        billing,
        resources=(
            replace(
                billing.resources[0], reports=(BudgetReportSelectionV1(wrong, wrong),)
            ),
        ),
    )
    with pytest.raises(ValueError, match="budget_overview_report_context_invalid"):
        project_budget_rows(_account(), (_resource(),), billing, query)


@pytest.mark.parametrize("counts_only", [False, True])
def test_owner_action_failure_and_future_run_priority_preserve_last_report(
    counts_only: bool,
) -> None:
    from dataclasses import asdict

    from agentmonitor.contracts.collection_control_v1 import BudgetCollectionRunViewV1
    from agentmonitor.modules.capacity.domain.budget_overview import project_budget_rows

    from backend.tests.capacity.pure.test_budget_funds_lineage import _run

    original = _run()
    # Copy typed fields, retaining nested DTOs rather than serializing identifiers.
    fields = {key: getattr(original, key) for key in asdict(original)}
    fields.update(
        provider_key="claude",
        resource_id=OpaqueIdV1("pure-pool"),
        capability_id="api.billing.usage",
        state="failed",
        observation_ids=(),
        outcome_code="budget_source_unavailable",
        error_code="budget_source_unavailable",
    )
    failed = BudgetCollectionRunViewV1(**fields, report_id=None)
    current = _current(counts_only=counts_only)
    resource = replace(current.resources[0], latest_collection=failed)
    current = replace(current, resources=(resource,))
    query = BudgetOverviewQueryV1(PERIOD, NOW)
    row = project_budget_rows(_account(), (_resource(),), current, query)[0]
    assert row.state_code == "collection_failed" and row.state_rank == 1
    assert (row.contexts[0].spend is None) == counts_only
    disabled = replace(
        resource,
        connection=replace(resource.connection, monitoring_preference="disabled"),
    )
    row = project_budget_rows(
        _account(), (_resource(),), replace(current, resources=(disabled,)), query
    )[0]
    assert row.state_code == "monitoring_disabled" and row.state_rank == 0
    future = replace(
        resource,
        latest_collection=replace(failed, completed_at=NOW + timedelta(minutes=1)),
    )
    row = project_budget_rows(
        _account(), (_resource(),), replace(current, resources=(future,)), query
    )[0]
    assert row.state_code == "collection_history_unavailable"
    assert row.collection_state is None and row.collection_error is None


def test_cloud_graph_prevents_creation_purpose_subscription_fallback() -> None:
    from agentmonitor.modules.capacity.domain.budget_overview import has_subscription

    account = replace(
        _account(), provider_key="ollama", initial_connection_purpose=None
    )
    assert not has_subscription(account, (), has_cloud_resources=True)
    assert has_subscription(account, (), has_cloud_resources=False)
    assert has_subscription(
        account, (_resource("subscription_pool"),), has_cloud_resources=True
    )

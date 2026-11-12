"""Actual private financial reads: unchanged authority with less connection work."""

import cProfile
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
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
from agentmonitor.adapters.persistence.registry.sqlite.financial_pools import (
    SqliteFinancialPoolRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.composition.bootstrap import create_iam_application
from agentmonitor.composition.budget_funds import StoredAccountBudgetFundsV1
from agentmonitor.contracts.budget_query_v1 import BudgetOverviewQueryV1
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import ActiveCredentialBindingRefV1
from agentmonitor.foundation.application import LifecycleHooksV1
from agentmonitor.modules.capacity.application.budget_overview import (
    ListBudgetOverviewV1,
)
from agentmonitor.modules.capacity.application.budget_queries import (
    GetAccountBudgetCurrentV1,
)
from agentmonitor.modules.capacity.application.queries import ListQuotaWindowsV1
from agentmonitor.modules.registry.application.accounts import (
    CapacityScopeMembershipQueryV2,
    ListAccountResourcesV1,
    ListAccountsV1,
)
from agentmonitor.modules.registry.application.organizations import GetOrganizationV1
from agentmonitor.modules.registry.domain.credential_binding import (
    resolve_active_credential_binding,
)
from sqlalchemy import event
from sqlalchemy.engine import Engine

from backend.tests.integration.registry.test_billing_credential_binding import (
    _account,
    _billing_connection,
)
from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)


def _query() -> BudgetOverviewQueryV1:
    now = datetime.now(UTC)
    end = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return BudgetOverviewQueryV1(
        BudgetPeriodV1(end - timedelta(days=7), end), now, limit=200
    )


def _prior_current(reference: DatabaseRefV1) -> GetAccountBudgetCurrentV1:
    """Prior composition over actual public repositories, never a boundary double."""
    registry = SqliteRegistryRepositoryV1(reference)
    billing = SqliteBillingConnectionRepositoryV1(reference)
    bindings = SqliteCredentialBindingsV1(reference)
    runs = SqliteCollectionRepositoryV1(reference)

    def guarded_binding(account_id: OpaqueIdV1) -> ActiveCredentialBindingRefV1 | None:
        status = billing.get(account_id)
        if status is None or (
            status.provider_key != "ollama" and not status.connections
        ):
            return None
        return resolve_active_credential_binding(bindings.read(account_id))

    return GetAccountBudgetCurrentV1(
        billing,
        SqliteBudgetReportRepositoryV1(reference),
        runs,
        StoredAccountBudgetFundsV1(
            CapacityScopeMembershipQueryV2(registry),
            ListQuotaWindowsV1(SqliteCapacityRepositoryV1(reference)),
            active_binding=guarded_binding,
            get_run=runs.get_run,
        ),
        active_binding=guarded_binding,
        cloud_target=SqliteCloudCredentialRegistryV1(reference).read_monitoring_target,
    )


def test_overview_removes_redundant_billing_reads_without_changing_snapshot(
    tmp_path: Path,
) -> None:
    """T010/T012: actual current authority fences remain; duplicate guards do not."""
    reference = _private_real_copy(tmp_path)
    config = tmp_path / "isolated.env"
    config.write_text("")
    config.chmod(0o600)
    app = create_iam_application(config, tmp_path, lifecycle=LifecycleHooksV1())
    ports = app.state.observation_ports
    registry = SqliteRegistryRepositoryV1(reference)
    prior = ListBudgetOverviewV1(
        ListAccountsV1(registry),
        _prior_current(reference),
        ListAccountResourcesV1(registry),
        SqliteFinancialPoolRepositoryV1(reference),
        GetOrganizationV1(registry),
    )
    query = _query()
    expected = prior(query)
    assert expected.page.availability.state == "available"
    assert expected.page.items, "genuine_financial_inventory_required"
    profile = cProfile.Profile()
    with profile:
        actual = ports.list_budget_overview(query)
    if actual != expected:
        raise AssertionError("financial_snapshot_changed_by_read_optimization")
    current_calls = sum(
        item.callcount
        for item in profile.getstats()
        if item.code == GetAccountBudgetCurrentV1.__call__.__code__
    )
    billing_calls = sum(
        item.callcount
        for item in profile.getstats()
        if item.code == SqliteBillingConnectionRepositoryV1.get.__code__
    )
    assert current_calls > 0
    assert billing_calls == 2 * current_calls, (
        f"redundant_billing_reads: {billing_calls} actual; "
        f"{2 * current_calls} required authority fences"
    )


def test_ineligible_and_absent_bindings_preserve_real_account_results(
    tmp_path: Path,
) -> None:
    """Only isolated owner metadata commands; no key, activation or observation."""
    reference = _private_real_copy(tmp_path)
    registry = SqliteRegistryRepositoryV1(reference)
    billing = SqliteBillingConnectionRepositoryV1(reference)
    ineligible = tuple(
        account
        for account in registry.list_accounts(page_size=200)
        if account.lifecycle != "archived"
        and account.provider_key in {"claude", "codex"}
        and (status := billing.get(account.account_id)) is not None
        and not status.connections
    )
    assert ineligible, "genuine_ineligible_binding_account_required"
    pending = _account(reference, "codex")
    _billing_connection(reference, pending)
    assert SqliteCredentialBindingsV1(reference).read(pending.account_id).bindings == ()
    config = tmp_path / "isolated.env"
    config.write_text("")
    config.chmod(0o600)
    app = create_iam_application(config, tmp_path, lifecycle=LifecycleHooksV1())
    current = app.state.observation_ports.get_account_budget_current
    prior = _prior_current(reference)
    query = _query()
    for account in (ineligible[0], pending):
        expected = prior(account.account_id, period=query.period, as_of=query.as_of)
        actual = current(account.account_id, period=query.period, as_of=query.as_of)
        assert expected is not None and expected.availability.state == "available"
        if actual != expected:
            raise AssertionError("absent_binding_changed_account_read")
        assert actual is not None
        assert not actual.cloud_resources
        assert all(not resource.reports for resource in actual.resources)
        assert actual.funds is not None and not actual.funds.components
    assert (
        current(
            OpaqueIdV1("missing-budget-efficiency-account"),
            period=query.period,
            as_of=query.as_of,
        )
        is None
    )


def test_resource_read_does_not_assign_journal_mode(tmp_path: Path) -> None:
    """Observe real DBAPI policy SQL through an actual SQLAlchemy connection event."""
    reference = _private_real_copy(tmp_path)
    registry = SqliteRegistryRepositoryV1(reference)
    accounts = registry.list_accounts(page_size=200)
    assert accounts, "genuine_registry_required"
    expected = tuple(registry.list_account_resources(a.account_id) for a in accounts)
    assignments = 0
    inspected = 0

    def inspect_statement(statement: str) -> None:
        nonlocal assignments, inspected
        # Retain counts only, never query text, rows or identifiers.
        normalized = "".join(statement.upper().split())
        if normalized.startswith("PRAGMAJOURNAL_MODE"):
            inspected += 1
            assignments += "=" in normalized

    def connected(driver: object, record: object) -> None:
        assert isinstance(driver, sqlite3.Connection)
        driver.set_trace_callback(inspect_statement)

    event.listen(Engine, "connect", connected)
    try:
        actual = tuple(registry.list_account_resources(a.account_id) for a in accounts)
    finally:
        event.remove(Engine, "connect", connected)
    if actual != expected:
        raise AssertionError("resource_read_changed_metadata")
    assert inspected > 0, "actual_policy_reads_not_observed"
    assert assignments == 0, "read_only_resources_assign_journal_mode"

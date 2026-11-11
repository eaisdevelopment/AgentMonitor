"""Read the genuine stored usage report through the account application query."""

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
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
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import CloudMonitoringTargetV1
from agentmonitor.modules.capacity.application.budget_queries import (
    GetAccountBudgetCurrentV1,
)
from agentmonitor.modules.registry.application.cloud_connection import (
    resolve_active_credential_binding,
)

ROOT = Path("/home/dev/.local/share/agentmonitor")


def test_genuine_cloud_report_is_visible_without_billing_enrollment() -> None:
    reference = DatabaseRefV1(ROOT / "agentmonitor.db", ROOT)
    reports = SqliteBudgetReportRepositoryV1(reference)
    with sqlite3.connect(f"file:{ROOT / 'agentmonitor.db'}?mode=ro", uri=True) as db:
        row = db.execute(
            "SELECT report_id, account_id FROM capacity_budget_report WHERE "
            "json_extract(canonical_report_json,'$.source_id')="
            "'ollama.cloud.usage.v1' ORDER BY stored_at DESC LIMIT 1"
        ).fetchone()
    assert row is not None, "genuine_usage_report_required"
    stored = reports.get_report(OpaqueIdV1(row[1]), OpaqueIdV1(row[0]))
    assert stored is not None
    account_id = stored.report.subject.account_id
    assert account_id is not None
    graph_repository = SqliteCloudCredentialRegistryV1(reference)
    graph_reads: list[OpaqueIdV1] = []

    def cloud_target(account: OpaqueIdV1) -> CloudMonitoringTargetV1 | None:
        graph = graph_repository.read_monitoring_target(account)
        graph_reads.append(account)
        return graph

    query = GetAccountBudgetCurrentV1(
        SqliteBillingConnectionRepositoryV1(reference),
        reports,
        SqliteCollectionRepositoryV1(reference),
        active_binding=lambda account: resolve_active_credential_binding(
            SqliteCredentialBindingsV1(reference).read(account)
        ),
        cloud_target=cloud_target,
    )
    value = query(
        account_id, period=stored.report.requested_period, as_of=datetime.now(UTC)
    )
    assert value is not None and value.availability.state == "available"
    assert value.resources == (), "no_duplicate_billing_enrollment_expected"
    assert len(value.cloud_resources) == 1
    cloud = value.cloud_resources[0]
    assert any(r.current == stored for r in cloud.reports)
    assert cloud.latest_collection is not None
    assert cloud.latest_collection.report_id == stored.report_id
    assert graph_reads == [account_id, account_id]
    assert all(
        selected.report.source_category == "self_requests_and_cost"
        for r in cloud.reports
        if (selected := r.latest_attempt or r.current) is not None
    )
    if not stored.report.cost_buckets:
        assert all(item.total is None for item in cloud.reported_spend)

    # Different requested coverage must not borrow the stored run's status.
    period = stored.report.requested_period
    shifted = query(
        account_id,
        period=BudgetPeriodV1(
            period.start - timedelta(days=1), period.end - timedelta(days=1)
        ),
        as_of=datetime.now(UTC),
    )
    assert shifted is not None and len(shifted.cloud_resources) == 1
    assert shifted.cloud_resources[0].latest_collection is None
    assert shifted.cloud_resources[0].reports == ()
    assert shifted.cloud_resources[0].report_availability.state == "unavailable"

    unsupported = query(
        account_id,
        period=BudgetPeriodV1(period.start - timedelta(days=1), period.end),
        as_of=datetime.now(UTC),
    )
    assert unsupported is not None and len(unsupported.cloud_resources) == 1
    assert unsupported.cloud_resources[0].latest_collection is None
    assert unsupported.cloud_resources[0].reports == ()
    assert (
        unsupported.cloud_resources[0].collection_availability.reason_code
        == "budget_cloud_context_unavailable"
    )

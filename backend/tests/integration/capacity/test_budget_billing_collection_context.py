"""Actual empty SQLite status reads; registry metadata only, no seeded runs."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
    SqliteBillingConnectionRepositoryV1,
)
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1
from agentmonitor.modules.capacity.application.budget_queries import (
    GetAccountBudgetCurrentV1,
)

from backend.tests.integration.registry.test_billing_connections import (
    _account,
    _command,
)


@pytest.mark.parametrize(
    ("days", "hour", "valid"),
    [(7, 0, True), (30, 0, True), (8, 0, False), (7, 12, False)],
)
def test_empty_billing_status_is_available_only_for_admitted_context(
    tmp_path: Path, days: int, hour: int, valid: bool
) -> None:
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    account = _account(ref)
    registry = SqliteBillingConnectionRepositoryV1(ref)
    registry.create(replace(_command(account), scope_id=None))
    query = GetAccountBudgetCurrentV1(
        registry, SqliteBudgetReportRepositoryV1(ref), SqliteCollectionRepositoryV1(ref)
    )
    end = datetime(2026, 11, 12, hour, tzinfo=UTC)
    result = query(
        account.account_id,
        period=BudgetPeriodV1(end - timedelta(days=days), end),
        as_of=end + timedelta(hours=1),
    )
    assert result is not None
    assert len(result.resources) == 1
    resource = result.resources[0]
    assert resource.latest_collection is None
    assert resource.reports == ()
    assert resource.collection_availability.state == (
        "available" if valid else "unavailable"
    )
    assert resource.collection_availability.reason_code == (
        "budget_collection_not_started"
        if valid
        else "budget_billing_context_unavailable"
    )

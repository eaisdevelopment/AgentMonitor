"""An actual account without funds preserves its existing unavailable reason."""

from datetime import UTC, datetime
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.composition.budget_funds import StoredAccountBudgetFundsV1
from agentmonitor.modules.capacity.application.queries import ListQuotaWindowsV1
from agentmonitor.modules.registry.application.accounts import (
    CapacityScopeMembershipQueryV2,
)

from backend.tests.integration.registry.test_billing_connections import _account


def test_absent_funds_do_not_require_lineage_callbacks(tmp_path: Path) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    account = _account(reference, "ollama")
    query = StoredAccountBudgetFundsV1(
        CapacityScopeMembershipQueryV2(SqliteRegistryRepositoryV1(reference)),
        ListQuotaWindowsV1(SqliteCapacityRepositoryV1(reference)),
    )
    result = query(account.account_id, as_of=datetime.now(UTC))
    assert result.components == ()
    assert result.availability.reason_code == "funds_source_unavailable"

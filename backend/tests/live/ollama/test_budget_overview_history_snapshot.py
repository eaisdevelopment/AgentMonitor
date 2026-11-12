"""Current metadata must not invalidate an earlier genuine financial cutoff."""

from datetime import datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    open_sqlite_database,
)
from agentmonitor.composition.bootstrap import create_iam_application
from agentmonitor.contracts.budget_query_v1 import BudgetOverviewQueryV1
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1
from agentmonitor.foundation.application import LifecycleHooksV1

from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)


def test_genuine_overview_keeps_financial_cutoff_after_registry_update(
    tmp_path: Path,
) -> None:
    reference = _private_real_copy(tmp_path)
    with open_sqlite_database(reference, "runtime_read_only") as database:
        with database.connect() as connection:
            updated = datetime.fromisoformat(
                connection.exec_driver_sql(
                    "SELECT updated_at FROM reg_registry_state WHERE singleton_key=1"
                ).scalar_one()
            )
    cutoff = updated - timedelta(microseconds=1)
    end = cutoff.replace(hour=0, minute=0, second=0, microsecond=0)
    period = BudgetPeriodV1(end - timedelta(days=7), end)
    config = tmp_path / "isolated.env"
    config.write_text("")
    config.chmod(0o600)
    app = create_iam_application(config, tmp_path, lifecycle=LifecycleHooksV1())
    result = app.state.observation_ports.list_budget_overview(
        BudgetOverviewQueryV1(period, cutoff, provider_key="ollama", limit=200)
    )
    assert result.page.availability.state == "available", (
        result.page.availability.reason_code
    )
    assert result.page.items, "genuine_cloud_resources_required"
    assert result.as_of == cutoff and result.period == period
    assert all(
        context.collected_at <= cutoff
        for row in result.page.items
        for context in row.contexts
    )

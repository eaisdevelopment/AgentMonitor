"""Real empty SQLite action guards; no cloud accounts or telemetry are seeded."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.contracts.cloud_usage_actions_v1 import CloudUsageCollectCommandV1
from agentmonitor.contracts.collection_control_v1 import CloudBudgetReportContextV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def test_empty_cloud_action_neither_enrolls_nor_reserves(tmp_path: Path) -> None:
    from agentmonitor.composition.cloud_usage_actions import CloudUsageActionsV1

    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    service = CloudUsageActionsV1(reference)
    now = datetime.now(UTC)
    end = now.replace(hour=0, minute=0, second=0, microsecond=0)
    context = CloudBudgetReportContextV1("self", "7d", end - timedelta(days=7), end)
    account, resource = OpaqueIdV1("absent-account"), OpaqueIdV1("absent-resource")
    assert service.eligibility(account, resource, context, now) is None
    assert service.get_status(account, resource, OpaqueIdV1("absent-run")) is None
    with pytest.raises(ValueError, match="cloud_usage_target_unavailable"):
        service.collect(
            CloudUsageCollectCommandV1(
                account,
                resource,
                1,
                1,
                OpaqueIdV1("absent-owner"),
                OpaqueIdV1("absent-command"),
                now,
                context,
            )
        )
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            for table in (
                "reg_provider_access_target",
                "reg_cloud_monitoring_target",
                "collection_run",
                "collection_request",
                "collection_schedule",
                "collection_budget_reservation",
                "collection_ollama_cloud_admission",
            ):
                assert (
                    connection.exec_driver_sql(
                        f"SELECT count(*) FROM {table}"
                    ).scalar_one()
                    == 0
                )
            assert (
                connection.exec_driver_sql("PRAGMA integrity_check").scalar_one()
                == "ok"
            )

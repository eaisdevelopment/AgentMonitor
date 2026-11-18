"""Read-only evidence that the installed service invoked financial retention."""

import subprocess
import time
from datetime import UTC, datetime, timedelta

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)

from backend.tests.live.ollama.test_budget_monetary_persistence import _require
from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _LIVE_DATABASE,
)


def test_installed_service_recorded_its_own_retention_cycle() -> None:
    started = subprocess.run(
        [
            "systemctl",
            "--user",
            "show",
            "agentmonitor-dashboard.service",
            "--property=ActiveEnterTimestampMonotonic",
            "--value",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    _require(started.stdout.strip().isdigit(), "installed_service_start_unavailable")
    since_boot = int(started.stdout.strip()) / 1_000_000
    _require(since_boot > 0, "installed_service_not_active")
    now = datetime.now(UTC)
    service_start = now - timedelta(seconds=time.monotonic() - since_boot + 1)
    reference = DatabaseRefV1(_LIVE_DATABASE, _LIVE_DATABASE.parent)
    with open_sqlite_database(reference, "runtime_read_only") as database:
        with database.connect() as connection:
            audit = connection.exec_driver_sql(
                "SELECT as_of,cutoff_at,started_at,completed_at,batch_limit,"
                "batch_count,deleted_quota_count,export_checkpoint_ref,state "
                "FROM capacity_retention_run WHERE policy_id=? "
                "AND correlation_id LIKE 'budget-retention-%' "
                "ORDER BY completed_at DESC LIMIT 1",
                ("budget_reports_365_days",),
            ).first()
    _require(audit is not None, "installed_retention_invocation_absent")
    assert audit is not None
    as_of, cutoff, begun, completed = (
        datetime.fromisoformat(str(value)) for value in audit[:4]
    )
    _require(service_start <= begun <= completed <= now, "retention_audit_not_current")
    _require(as_of - cutoff == timedelta(days=365), "retention_cutoff_incorrect")
    _require(audit[4] == 1 and 0 <= audit[5] <= 1, "retention_batch_unbounded")
    _require(audit[6] == 0, "retention_deleted_subscription_history")
    _require(
        (audit[5] == 0) == (audit[7] is None), "retention_export_audit_inconsistent"
    )
    _require(audit[8] in {"partial", "completed"}, "retention_cycle_incomplete")

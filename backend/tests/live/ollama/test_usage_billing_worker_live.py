"""One real supervised usage attempt with existing owner-enabled cloud accounts.

Uses the production registry, gate and selected protected credential location.
No key values, provider payloads or account configuration enter this test.
"""

import asyncio
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from agentmonitor.composition.billing_worker_supervisor import BillingWorkerSupervisorV1
from agentmonitor.composition.ollama_env_store import read_env_location

ROOT = Path("/home/dev/.local/share/agentmonitor")


def test_supervised_worker_persists_real_cloud_usage_report() -> None:
    start = datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    worker = BillingWorkerSupervisorV1(
        ROOT, credential_env_file=read_env_location(ROOT)
    )
    state = asyncio.run(worker.run_once())
    assert state == "completed", "real_usage_worker_" + state
    with sqlite3.connect(f"file:{ROOT / 'agentmonitor.db'}?mode=ro", uri=True) as db:
        row = db.execute(
            "SELECT COUNT(*) FROM capacity_budget_report WHERE "
            "json_extract(canonical_report_json,'$.source_id')='ollama.cloud.usage.v1' "
            "AND stored_at>=?",
            (start,),
        ).fetchone()
    assert row is not None and row[0] > 0, "supervised_cloud_usage_report_missing"

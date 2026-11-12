"""Built P02 discovery over private genuine history; no provider requests."""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.composition.bootstrap import create_iam_application
from agentmonitor.contracts.collection_control_v1 import BudgetCollectionRunViewV1
from agentmonitor.foundation.application import LifecycleHooksV1

from backend.tests.integration.api.test_iam_http import _running
from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)


def test_source_history_built_browser_on_genuine_private_snapshot(
    tmp_path: Path,
) -> None:
    reference = _private_real_copy(tmp_path)
    reports = SqliteBudgetReportRepositoryV1(reference)
    runs = SqliteCollectionRepositoryV1(reference)
    now = datetime.now(UTC)
    genuine = []
    for run in runs.list_runs("ollama", None, now, 500):
        if (
            not isinstance(run, BudgetCollectionRunViewV1)
            or run.report_id is None
            or run.account_id is None
        ):
            continue
        report = reports.get_report(run.account_id, run.report_id)
        if report is not None and report.report.usage_buckets:
            genuine.append(report)
    assert genuine, "genuine_stored_usage_required"
    selected = max(genuine, key=lambda value: (value.stored_at, value.report_id.value))
    selection = {
        "account_id": selected.report.subject.account_id.value,
        "resource_id": selected.report.subject.resource_id.value,
        "period_start": selected.report.requested_period.start.isoformat().replace(
            "+00:00", "Z"
        ),
        "period_end": selected.report.requested_period.end.isoformat().replace(
            "+00:00", "Z"
        ),
        "as_of": now.isoformat().replace("+00:00", "Z"),
    }
    config = tmp_path / "isolated.env"
    config.write_text("")
    config.chmod(0o600)
    app = create_iam_application(config, tmp_path, lifecycle=LifecycleHooksV1())
    runtime = app.state.lifecycle
    runtime.hooks = replace(runtime.hooks, tasks=())

    async def exercise() -> None:
        async with _running(app) as origin:
            process = await asyncio.create_subprocess_exec(
                "node",
                "frontend/tests/browser/m7/source_history.mjs",
                origin,
                cwd=Path(__file__).resolve().parents[4],
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            try:
                output, _ = await asyncio.wait_for(
                    process.communicate(json.dumps(selection).encode()),
                    timeout=180,
                )
            finally:
                if process.returncode is None:
                    process.terminate()
                    await asyncio.wait_for(process.wait(), timeout=10)
            assert process.returncode == 0, output.decode("utf-8", errors="replace")
            assert output.startswith(b"M7 SOURCE HISTORY BROWSER: PASSED"), (
                "browser_output_invalid"
            )

    asyncio.run(exercise())

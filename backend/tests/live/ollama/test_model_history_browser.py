"""Read a retained genuine model report through private HTTP and the built UI."""

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


def test_retained_model_report_exact_history_in_built_browser(tmp_path: Path) -> None:
    reference = _private_real_copy(tmp_path)
    reports = SqliteBudgetReportRepositoryV1(reference)
    runs = SqliteCollectionRepositoryV1(reference)
    now = datetime.now(UTC)
    selected = None
    cursor = None
    for _ in range(20):
        page = runs.list_runs("ollama", None, now, 500, cursor)
        for run in page:
            if (
                not isinstance(run, BudgetCollectionRunViewV1)
                or run.report_id is None
                or run.account_id is None
            ):
                continue
            view = reports.get_report(run.account_id, run.report_id)
            if (
                view is not None
                and view.report.grouping == ("model",)
                and view.report.source_category
                in {"self_requests_and_cost", "team_requests_and_cost"}
                and (view.report.usage_buckets or view.report.cost_buckets)
            ):
                selected = view
                break
        if selected is not None or len(page) < 500:
            break
        cursor = page[-1].run_id.value
    assert selected is not None, "genuine_retained_model_report_required"
    report = selected.report
    assert report.subject.account_id is not None
    assert report.subject.resource_id is not None
    selection = {
        "account_id": report.subject.account_id.value,
        "resource_id": report.subject.resource_id.value,
        "report_id": selected.report_id.value,
        "source_id": report.source_id,
        "source_category": report.source_category,
        "period_start": report.requested_period.start.isoformat(),
        "period_end": report.requested_period.end.isoformat(),
        "as_of": now.isoformat(),
    }
    config = tmp_path / "isolated.env"
    config.write_text("")
    config.chmod(0o600)
    app = create_iam_application(config, tmp_path, lifecycle=LifecycleHooksV1())
    app.state.lifecycle.hooks = replace(app.state.lifecycle.hooks, tasks=())

    async def exercise() -> None:
        async with _running(app) as origin:
            process = await asyncio.create_subprocess_exec(
                "node",
                "frontend/tests/browser/m7/model_history.mjs",
                origin,
                cwd=Path(__file__).resolve().parents[4],
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            try:
                output, _ = await asyncio.wait_for(
                    process.communicate(json.dumps(selection).encode()), timeout=180
                )
            finally:
                if process.returncode is None:
                    process.terminate()
                    await asyncio.wait_for(process.wait(), timeout=10)
            assert process.returncode == 0, output.decode("utf-8", errors="replace")
            evidence = json.loads(output)
            assert evidence["status"] == "passed"
            assert evidence["mutations"] == 0
            assert evidence["rows"] > 0
            assert evidence["reload_verified"] is True
            # Natural counts-only and absent remainder remain explicit coverage
            # limits, never claims of monetary or remainder mapping execution.
            print(json.dumps(evidence, sort_keys=True))

    asyncio.run(exercise())

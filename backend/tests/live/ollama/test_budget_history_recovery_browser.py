"""Real service restart invalidates a genuine history cursor in the built UI."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.composition.bootstrap import create_iam_application, serve_loopback
from agentmonitor.contracts.collection_control_v1 import BudgetCollectionRunViewV1
from agentmonitor.foundation.application import LifecycleHooksV1

from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)


def test_genuine_history_cursor_restart_in_built_browser(tmp_path: Path) -> None:
    reference = _private_real_copy(tmp_path)
    reports = SqliteBudgetReportRepositoryV1(reference)
    runs = SqliteCollectionRepositoryV1(reference)
    now = datetime.now(UTC)
    genuine = []
    for run in runs.list_runs("ollama", None, now, 500):
        if (
            isinstance(run, BudgetCollectionRunViewV1)
            and run.report_id is not None
            and run.account_id is not None
        ):
            report = reports.get_report(run.account_id, run.report_id)
            if (
                report is not None
                and report.report.collected_at < report.stored_at
                and len(report.report.cost_buckets) + len(report.report.usage_buckets)
                > 50
            ):
                genuine.append(report)
    assert genuine, "genuine_history_continuation_required"
    selected = max(genuine, key=lambda value: value.stored_at)
    selection = {
        "account_id": selected.report.subject.account_id.value,
        "resource_id": selected.report.subject.resource_id.value,
        "report_id": selected.report_id.value,
        "period_start": selected.report.requested_period.start.isoformat(),
        "period_end": selected.report.requested_period.end.isoformat(),
        "as_of": now.isoformat(),
        "unavailable_as_of": selected.report.collected_at.isoformat(),
    }
    config = tmp_path / "isolated.env"
    config.write_text("")
    config.chmod(0o600)

    @asynccontextmanager
    async def running(port: int) -> AsyncIterator[str]:
        app = create_iam_application(config, tmp_path, lifecycle=LifecycleHooksV1())
        app.state.lifecycle.hooks = replace(app.state.lifecycle.hooks, tasks=())
        stop = asyncio.Event()
        ready = asyncio.get_running_loop().create_future()
        task = asyncio.create_task(
            serve_loopback(
                app, host="127.0.0.1", port=port, ready=ready.set_result, stop=stop
            )
        )
        try:
            yield await asyncio.wait_for(asyncio.shield(ready), timeout=10)
        finally:
            stop.set()
            await asyncio.wait_for(task, timeout=10)

    async def exercise() -> None:
        process = None
        try:
            async with running(0) as origin:
                process = await asyncio.create_subprocess_exec(
                    "node",
                    "frontend/tests/browser/m7/history_recovery.mjs",
                    origin,
                    cwd=Path(__file__).resolve().parents[4],
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                assert process.stdin is not None and process.stdout is not None
                process.stdin.write((json.dumps(selection) + "\n").encode())
                await process.stdin.drain()
                signal = await asyncio.wait_for(process.stdout.readline(), timeout=60)
                assert signal == b"RESTART PRIVATE HISTORY SERVICE\n", signal.decode()
            # Recreate the actual HTTP application/signing key on the same private
            # port. No installed process, provider state or response is replaced.
            async with running(int(origin.rsplit(":", 1)[1])) as restarted:
                assert restarted == origin
                process.stdin.write(b"PRIVATE HISTORY SERVICE READY\n")
                await process.stdin.drain()
                output, _ = await asyncio.wait_for(process.communicate(), timeout=60)
                assert process.returncode == 0, output.decode()
                assert output == b"M7 HISTORY RECOVERY BROWSER: PASSED\n"
        finally:
            if process is not None and process.returncode is None:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=10)

    asyncio.run(exercise())

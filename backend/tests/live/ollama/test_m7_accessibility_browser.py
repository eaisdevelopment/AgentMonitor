"""Keyboard access in the built dashboard over an unchanged genuine snapshot."""

import asyncio
import json
import re
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from agentmonitor.composition.bootstrap import create_iam_application
from agentmonitor.foundation.application import LifecycleHooksV1

from backend.tests.integration.api.test_iam_http import _installation, _running
from backend.tests.live.ollama.test_budget_monetary_persistence import _monetary_report
from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)


def test_m7_accessibility_built_browser_on_genuine_snapshot(tmp_path: Path) -> None:
    data_root, iam_root = tmp_path / "reports", tmp_path / "iam"
    data_root.mkdir(mode=0o700)
    iam_root.mkdir(mode=0o700)
    reference = _private_real_copy(data_root)
    _, stored = _monetary_report(reference)
    config = data_root / "isolated.env"
    config.write_text("")
    config.chmod(0o600)
    readers = create_iam_application(config, data_root, lifecycle=LifecycleHooksV1())
    readers.state.lifecycle.hooks = replace(readers.state.lifecycle.hooks, tasks=())
    app, credential = _installation(iam_root)
    app.state.lifecycle.hooks = replace(app.state.lifecycle.hooks, tasks=())
    app.state.observation_ports = readers.state.observation_ports
    packet = {
        "credential": credential,
        "period_start": stored.report.requested_period.start.isoformat(),
        "period_end": stored.report.requested_period.end.isoformat(),
        "as_of": datetime.now(UTC).isoformat(),
    }

    async def exercise() -> None:
        async with _running(app) as origin:
            process = await asyncio.create_subprocess_exec(
                "node",
                "frontend/tests/browser/m7/accessibility.mjs",
                origin,
                cwd=Path(__file__).resolve().parents[4],
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            try:
                output, _ = await asyncio.wait_for(
                    process.communicate(json.dumps(packet).encode()), timeout=180
                )
            finally:
                if process.returncode is None:
                    process.terminate()
                    await asyncio.wait_for(process.wait(), timeout=10)
            success = re.fullmatch(
                rb"M7 ACCESSIBILITY BROWSER: PASSED focus_checks=[1-9][0-9]* "
                rb"native_zoom=not_run\n",
                output,
            )
            if process.returncode != 0 or success is None:
                stage = re.fullmatch(
                    rb"M7 ACCESSIBILITY BROWSER: FAILED \xe2\x80\x94 ([a-z0-9_\-]+)\n",
                    output,
                )
                pytest.fail(
                    "accessibility_browser_"
                    + (stage.group(1).decode("ascii") if stage else "protocol_or_exit"),
                    pytrace=False,
                )

    asyncio.run(exercise())

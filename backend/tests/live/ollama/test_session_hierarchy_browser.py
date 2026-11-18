"""On-demand hierarchy in a built browser over an unchanged genuine snapshot."""

import asyncio
import re
from dataclasses import replace
from pathlib import Path

import pytest
from agentmonitor.composition.bootstrap import create_iam_application
from agentmonitor.foundation.application import LifecycleHooksV1

from backend.tests.integration.api.test_iam_http import _running
from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)


def test_session_hierarchy_built_browser_on_genuine_snapshot(tmp_path: Path) -> None:
    _private_real_copy(tmp_path)
    config = tmp_path / "isolated.env"
    config.write_text("")
    config.chmod(0o600)
    app = create_iam_application(config, tmp_path, lifecycle=LifecycleHooksV1())
    app.state.lifecycle.hooks = replace(app.state.lifecycle.hooks, tasks=())

    async def exercise() -> None:
        async with _running(app) as origin:
            process = await asyncio.create_subprocess_exec(
                "node",
                "frontend/tests/browser/m7/session_hierarchy.mjs",
                origin,
                cwd=Path(__file__).resolve().parents[4],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            try:
                output, _ = await asyncio.wait_for(process.communicate(), timeout=120)
            finally:
                if process.returncode is None:
                    process.terminate()
                    await asyncio.wait_for(process.wait(), timeout=10)
            success = re.fullmatch(
                rb"M7 SESSION HIERARCHY BROWSER: PASSED explicit_reads=3 "
                rb"rows_checked=[1-9][0-9]* account_entry=(true|false)\n",
                output,
            )
            if process.returncode != 0 or success is None:
                stage = re.fullmatch(
                    rb"M7 SESSION HIERARCHY BROWSER: FAILED \xe2\x80\x94 ([a-z_]+)\n",
                    output,
                )
                pytest.fail(
                    "session_hierarchy_browser_"
                    + (stage.group(1).decode("ascii") if stage else "protocol_or_exit"),
                    pytrace=False,
                )

    asyncio.run(exercise())

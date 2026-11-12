"""Built pool controls against isolated real IAM/registry; no provider access."""

from __future__ import annotations

import asyncio
import subprocess
import tempfile
from pathlib import Path

from backend.tests.integration.api.test_iam_http import _installation, _running

ROOT = Path(__file__).resolve().parents[4]
STAGES = {
    "browser_launch",
    "login",
    "owner_metadata",
    "pool_controls_missing",
    "create_pool",
    "join_pool",
    "shared_overview",
    "edit_attribution",
    "unlink_pool",
    "stale_revision",
    "pagination",
    "uncertain_outcome",
    "reload_keyboard_narrow",
    "no_provider_work",
    "overview_sort_source",
    "overview_sort_first_page",
    "overview_sort_pagination",
    "overview_sort_reset",
    "overview_sort_reload",
}


async def run() -> None:
    with tempfile.TemporaryDirectory(prefix="agentmonitor-pool-browser-") as directory:
        app, credential = _installation(Path(directory))
        async with _running(app) as origin:
            result = await asyncio.to_thread(
                subprocess.run,
                ["node", str(Path(__file__).with_name("financial_pools.mjs")), origin],
                input=credential,
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
                timeout=420,
            )
        passed = "M7 FINANCIAL POOLS BROWSER: PASSED"
        if (
            result.returncode == 0
            and result.stdout.strip() == passed
            and not result.stderr
        ):
            print(passed)
            return
        prefix = "M7 FINANCIAL POOLS BROWSER: FAILED — "
        stage = result.stderr.strip().removeprefix(prefix)
        if result.stdout or stage not in STAGES:
            stage = "browser_output_invalid"
        raise RuntimeError(stage)


def main() -> int:
    try:
        asyncio.run(run())
    except (RuntimeError, TimeoutError, subprocess.TimeoutExpired) as error:
        stage = str(error) if str(error) in STAGES else "browser_boundary"
        print("M7 FINANCIAL POOLS BROWSER: FAILED — " + stage)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

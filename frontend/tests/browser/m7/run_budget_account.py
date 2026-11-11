"""Dedicated M7 account scenario using the existing isolated real P02 runner."""

import asyncio
import importlib.util
from pathlib import Path


def main() -> int:
    runner = Path(__file__).resolve().parents[1] / "p02" / "run_browser.py"
    spec = importlib.util.spec_from_file_location("p02_budget_browser_runner", runner)
    if spec is None or spec.loader is None:
        raise RuntimeError("browser_runner_unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        asyncio.run(module.run_scenario("budget_account"))
    except (RuntimeError, TimeoutError) as error:
        stages = (
            "browser_launch",
            "login",
            "create_metadata",
            "budget_panel",
            "configured_no_report",
            "range_and_read_only",
            "reload_narrow",
        )
        stage = next(
            (value for value in stages if "FAILED — " + value in str(error)), "boundary"
        )
        print("M7 BUDGET ACCOUNT: FAILED — " + stage)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

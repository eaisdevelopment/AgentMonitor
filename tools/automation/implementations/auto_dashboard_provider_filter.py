"""Build and verify the real mixed-provider Overview filter."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    required = (
        "AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT",
        "AGENTMONITOR_TEST_DASHBOARD_ORIGIN",
    )
    if any(not os.environ.get(name) for name in required):
        print(
            "AUTO-DASHBOARD-PROVIDER-FILTER: BLOCKED — authenticated shared "
            "dashboard selectors required"
        )
        return 3
    commands = (
        ["python3", "tools/automation/implementations/auto_build.py"],
        ["node", "tools/ui/verify_dashboard_provider_filter.mjs"],
    )
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            status = "BLOCKED" if result.returncode == 3 else "FAILED"
            print(
                f"AUTO-DASHBOARD-PROVIDER-FILTER: {status} — production build "
                "or real browser verification did not pass"
            )
            return result.returncode
    print(
        "AUTO-DASHBOARD-PROVIDER-FILTER: PASSED — production build and real "
        "Claude/Codex Overview filtering"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

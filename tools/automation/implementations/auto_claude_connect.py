"""Selected real dashboard connection gate; never starts provider sign-in."""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    required = (
        "AGENTMONITOR_TEST_OWNER_DATA_ROOT",
        "AGENTMONITOR_TEST_MANAGED_ACCOUNT_ID",
        "AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT",
        "AGENTMONITOR_TEST_DASHBOARD_ORIGIN",
    )
    if any(not os.environ.get(name) for name in required):
        print(
            "AUTO-CLAUDE-CONNECT: BLOCKED — selected real owner flow "
            "and dashboard required"
        )
        return 3
    commands = (
        [
            str(ROOT / "backend/.venv/bin/python"),
            "-m",
            "pytest",
            "-q",
            "--tb=short",
            "backend/tests/integration/api/test_provider_connection_routes.py",
            "backend/tests/adapters/providers/claude/live/test_connection_process.py",
        ],
        [
            str(ROOT / "backend/.venv/bin/python"),
            "frontend/tests/browser/p02/run_browser.py",
            "claude_connection",
            "--no-build",
        ],
        ["node", "tools/providers/verify_claude_dashboard_connection.mjs"],
        [
            str(ROOT / "backend/.venv/bin/python"),
            "-m",
            "pytest",
            "-q",
            "--tb=short",
            "backend/tests/adapters/providers/claude/live/test_managed_quota.py",
        ],
        ["node", "tools/providers/verify_claude_connection.mjs"],
        ["node", "tools/ui/verify_dashboard_overview.mjs"],
    )
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            print(
                "AUTO-CLAUDE-CONNECT: BLOCKED — a real boundary or owner "
                "interaction is incomplete"
            )
            return 3
    print(
        "AUTO-CLAUDE-CONNECT: PASSED — selected owner-driven dashboard "
        "authentication and real quota; full M4 remains separate"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

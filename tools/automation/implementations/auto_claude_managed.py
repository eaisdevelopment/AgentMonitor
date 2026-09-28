"""Fail-closed live managed Claude connection and shared-dashboard gate."""

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
            "AUTO-CLAUDE-MANAGED: BLOCKED — "
            "real managed account and shared dashboard required"
        )
        return 3
    for command in (
        [
            str(ROOT / "backend/.venv/bin/python"),
            "-m",
            "pytest",
            "-q",
            "--tb=short",
            "backend/tests/adapters/providers/claude/live/test_managed_identity.py",
            "backend/tests/adapters/providers/claude/live/test_managed_quota.py",
            "backend/tests/collection_control/test_polling.py",
            "backend/tests/integration/registry/test_verified_pending_account.py",
            "backend/tests/integration/registry/test_managed_connection.py",
            "backend/tests/integration/collection_control/test_managed_polling.py::test_latest_source_cadence_is_account_scoped",
        ],
        ["node", "tools/providers/verify_claude_connection.mjs"],
    ):
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            print(
                "AUTO-CLAUDE-MANAGED: BLOCKED — "
                "live prerequisite or verification failed"
            )
            return 3
    print(
        "AUTO-CLAUDE-MANAGED: PASSED — selected managed identity, "
        "enrollment, quota, and real dashboard"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

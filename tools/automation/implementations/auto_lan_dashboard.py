"""Fail-closed real owner-selected LAN HTTP and built-browser verification."""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    if not all(
        os.environ.get(name)
        for name in (
            "AGENTMONITOR_TEST_LAN_HOST",
            "AGENTMONITOR_TEST_LAN_NETWORK",
        )
    ):
        print(
            "AUTO-LAN-DASHBOARD: BLOCKED — explicit real LAN interface "
            "and subnet required"
        )
        return 3
    command = [
        str(ROOT / "backend/.venv/bin/python"),
        "-m",
        "pytest",
        "-q",
        "--tb=short",
        "backend/tests/integration/api/test_lan_http.py",
    ]
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode:
        print(
            "AUTO-LAN-DASHBOARD: FAILED — real LAN/loopback HTTP "
            "or built Chrome boundary"
        )
        return result.returncode
    print(
        "AUTO-LAN-DASHBOARD: PASSED — real dual sockets, "
        "subnet/Host/Origin/auth/CSRF and built Chrome; "
        "second-computer reachability remains owner verification"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

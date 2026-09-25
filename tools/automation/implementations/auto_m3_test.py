"""Run the bounded real M3 technical test surface.

M2's complete browser routine intentionally includes a 30-minute real idle
expiry scenario. M3's exit gate already performs its own fresh authenticated
visible browser and provider checks, so it runs the M3-owned backend/contract
surface here and leaves the long M2 routine under AUTO-TEST.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

COMMANDS: tuple[tuple[str, ...], ...] = (
    (
        ".venv-m0-g1/bin/python",
        "-m",
        "unittest",
        "tools.discovery.m3_handoff_contract_tests",
    ),
    (
        "backend/.venv/bin/python",
        "-m",
        "pytest",
        "backend/tests/capacity",
        "backend/tests/collection_control",
        "backend/tests/contracts",
        "backend/tests/provider_system",
        "backend/tests/registry",
        "backend/tests/runtime_observation",
        "backend/tests/integration/api",
        "backend/tests/integration/capacity",
        "backend/tests/integration/collection_control",
        "backend/tests/integration/provider_system",
        "backend/tests/integration/registry",
        "--ignore=backend/tests/integration/identity_access/test_argon2_workload.py",
        "-q",
        "--tb=short",
    ),
)


def main() -> int:
    for command in COMMANDS:
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode != 0:
            print("AUTO-M3-TEST: FAILED — required M3 technical test failed")
            return result.returncode
    print("AUTO-M3-TEST: PASSED — M3 contract and technical backend boundaries")
    return 0


if __name__ == "__main__":
    sys.exit(main())

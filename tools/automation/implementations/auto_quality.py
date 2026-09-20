"""Run the V1-M1 local quality checks without installing or publishing anything."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from shutil import which

ROOT = Path(__file__).resolve().parents[3]
BACKEND_PYTHON = ROOT / "backend/.venv/bin/python"
BACKEND_RUFF = ROOT / "backend/.venv/bin/ruff"
BACKEND_MYPY = ROOT / "backend/.venv/bin/mypy"


def run(command: list[str], *, environment: dict[str, str] | None = None) -> int:
    return subprocess.run(command, cwd=ROOT, check=False, env=environment).returncode


def main() -> int:
    tools = {name: which(name) for name in ("node", "npm", "uv")}
    if any(path is None for path in tools.values()):
        print("AUTO-QUALITY: FAILED — admitted_toolchain_command_missing")
        return 1
    commands = (
        [
            str(BACKEND_PYTHON),
            "tooling/foundation/check_toolchain.py",
            "--root",
            ".",
            "--node",
            str(tools["node"]),
            "--npm",
            str(tools["npm"]),
            "--uv",
            str(tools["uv"]),
        ],
        [
            str(BACKEND_RUFF),
            "check",
            "--config",
            "backend/pyproject.toml",
            "backend/src",
            "backend/tests",
            "tools/automation/implementations",
        ],
        [
            str(BACKEND_RUFF),
            "format",
            "--check",
            "--config",
            "backend/pyproject.toml",
            "backend/src",
            "backend/tests",
            "tools/automation/implementations",
        ],
        [
            str(BACKEND_MYPY),
            "--config-file",
            "backend/pyproject.toml",
            "--explicit-package-bases",
            "backend/src/agentmonitor",
            "backend/tests",
        ],
        ["python3", "tooling/foundation/check_boundaries.py", "."],
        [str(BACKEND_PYTHON), "tooling/foundation/openapi_client.py", "--check"],
        ["npm", "--prefix", "frontend", "run", "typecheck"],
        ["uv", "lock", "--check", "--directory", "backend"],
        ["npm", "--prefix", "frontend", "run", "build"],
    )
    if not all(path.is_file() for path in (BACKEND_PYTHON, BACKEND_RUFF, BACKEND_MYPY)):
        print("AUTO-QUALITY: FAILED — admitted_backend_toolchain_missing")
        return 1
    mypy_environment = {
        "PATH": "/home/dev/.local/bin:/usr/local/bin:/usr/bin:/bin",
        "MYPYPATH": str(ROOT / "backend/src"),
    }
    for command in commands:
        environment = mypy_environment if command[0] == str(BACKEND_MYPY) else None
        if run(command, environment=environment):
            print("AUTO-QUALITY: FAILED — quality_gate_failed")
            return 1
    print("QUALITY STATUS: Passed local static/boundary/generated/locked-input checks")
    print(
        "QUALITY STATUS: Not Run hosted GitLab, live provider, platform, "
        "SBOM/notices release generation"
    )
    print(
        json.dumps(
            {
                "contract_id": "CTR-FND-008",
                "test_id": "FND-QUALITY-001",
                "requirement_ids": ["NFR-TEST-002", "NFR-LIC-001"],
                "acceptance_ids": ["AC-TEST-002", "AC-TEST-006"],
                "boundary_class": "local static quality",
                "command_registry_id": "AUTO-QUALITY",
                "environment_versions": [],
                "red_reference": None,
                "green_reference": "task-5-report.md#green-evidence",
                "refactor_reference": "task-5-report.md#refactor-evidence",
                "status": "Passed",
                "recorded_at": datetime.now(UTC).isoformat(),
                "sanitization_review": "allowlist-only command status",
                "reviewer": "PLAN-FND",
                "live_owner_countersignature": None,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

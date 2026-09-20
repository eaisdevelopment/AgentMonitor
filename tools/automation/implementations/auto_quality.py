"""Run the V1-M1 local quality checks without installing or publishing anything."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from shutil import which

from auto_build import verify_frontend_inputs

ROOT = Path(__file__).resolve().parents[3]
BACKEND_PYTHON = ROOT / "backend/.venv/bin/python"
BACKEND_RUFF = ROOT / "backend/.venv/bin/ruff"
BACKEND_MYPY = ROOT / "backend/.venv/bin/mypy"


def run(command: list[str], *, environment: dict[str, str] | None = None) -> int:
    return subprocess.run(command, cwd=ROOT, check=False, env=environment).returncode


def minimum_local_controls() -> bool:
    """Fail closed on prohibited doubles, secret literals, or unsafe shell use."""
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, check=False, capture_output=True, text=True
    )
    if tracked.returncode:
        return False
    patterns = (
        r"unittest\.mock|pytest_mock|\bMagicMock\b|\bmonkeypatch\b",
        r"\bshell\s*=\s*True\b|\bos\.system\(",
        r"(?:api[_-]?key|secret|password)\s*[:=]\s*['\"][^'\"]{8,}",
    )
    source_suffixes = {".py", ".ts", ".tsx", ".js", ".json", ".toml", ".yml"}
    for relative in tracked.stdout.splitlines():
        path = ROOT / relative
        if path == Path(__file__).resolve():
            continue
        if path.suffix not in source_suffixes or "node_modules" in path.parts:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return False
        if any(re.search(pattern, content) for pattern in patterns):
            return False
    return (
        (ROOT / "docs/dependencies/m1-foundation-admission.md").is_file()
        and (ROOT / "docs/dependencies/m1-foundation-lock-review.md").is_file()
        and verify_frontend_inputs()
    )


def main() -> int:
    tools = {name: which(name) for name in ("node", "npm", "uv")}
    if any(path is None for path in tools.values()):
        print("AUTO-QUALITY: FAILED — admitted_toolchain_command_missing")
        return 1
    if not minimum_local_controls():
        print("AUTO-QUALITY: FAILED — minimum_m1_local_control_failed")
        return 1
    print("M1 LOCAL CONTROLS: PASSED")
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
        [
            str(ROOT / "frontend/node_modules/.bin/tsc"),
            "--project",
            "frontend/tsconfig.node.json",
        ],
        [str(tools["uv"]), "lock", "--check", "--directory", "backend"],
        [str(ROOT / "frontend/node_modules/.bin/vite"), "build", "frontend"],
    )
    if not all(path.is_file() for path in (BACKEND_PYTHON, BACKEND_RUFF, BACKEND_MYPY)):
        print("AUTO-QUALITY: FAILED — admitted_backend_toolchain_missing")
        return 1
    mypy_environment = {
        "PATH": os.environ.get("PATH", os.defpath),
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
                "red_reference": "task-5-report.md#fix-round-1-red-evidence",
                "green_reference": "task-5-report.md#fix-round-1-green-evidence",
                "refactor_reference": "task-5-report.md#fix-round-1-refactor-evidence",
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

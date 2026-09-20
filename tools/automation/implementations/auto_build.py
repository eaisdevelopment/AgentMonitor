"""Build the M1 frontend from locked inputs and verify generated API artifacts."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BACKEND_PYTHON = ROOT / "backend/.venv/bin/python"
FRONTEND = ROOT / "frontend"


def verify_frontend_inputs() -> bool:
    """Verify manifest, lock, and installed non-optional packages without writes."""
    try:
        manifest = json.loads((FRONTEND / "package.json").read_text())
        lock = json.loads((FRONTEND / "package-lock.json").read_text())
        packages = lock["packages"]
        root = packages[""]
        declared = {
            **manifest["dependencies"],
            **manifest["devDependencies"],
        }
        if (
            lock["lockfileVersion"] != 3
            or root["dependencies"] != manifest["dependencies"]
        ):
            return False
        if root["devDependencies"] != manifest["devDependencies"]:
            return False
        if root["engines"] != manifest["engines"]:
            return False
        for name, version in declared.items():
            locked = packages[f"node_modules/{name}"]
            if version != locked["version"] or not locked.get("license"):
                return False
        for relative, record in packages.items():
            if not relative or record.get("optional"):
                continue
            package_json = FRONTEND / relative / "package.json"
            if not package_json.is_file():
                return False
            installed = json.loads(package_json.read_text())
            if installed.get("version") != record.get("version"):
                return False
    except (KeyError, OSError, TypeError, json.JSONDecodeError):
        return False
    return True


def main() -> int:
    if not verify_frontend_inputs():
        print("AUTO-BUILD: FAILED — frontend_inputs_unlocked_or_unavailable")
        return 1
    print("FRONTEND INPUTS: PASSED")
    commands = (
        ["uv", "lock", "--check", "--directory", "backend"],
        [str(BACKEND_PYTHON), "tooling/foundation/openapi_client.py", "--check"],
        [str(FRONTEND / "node_modules/.bin/vite"), "build", "frontend"],
    )
    if not BACKEND_PYTHON.is_file():
        print("AUTO-BUILD: FAILED — admitted_backend_toolchain_missing")
        return 1
    for command in commands:
        if subprocess.run(command, cwd=ROOT, check=False).returncode:
            print("AUTO-BUILD: FAILED — reproducible_build_failed")
            return 1
    if not (ROOT / "frontend/dist/index.html").is_file():
        print("AUTO-BUILD: FAILED — frontend_artifact_missing")
        return 1
    print(
        "BUILD STATUS: Passed generated contract check and production frontend artifact"
    )
    print("BUILD STATUS: Not Run release SBOM/notices and hosted artifact publication")
    print(
        json.dumps(
            {
                "contract_id": "CTR-FND-008",
                "test_id": "FND-BUILD-001",
                "requirement_ids": ["NFR-API-002", "NFR-LIC-001"],
                "acceptance_ids": ["AC-TEST-004", "AC-TEST-006"],
                "boundary_class": "local production build",
                "command_registry_id": "AUTO-BUILD",
                "environment_versions": [],
                "red_reference": "task-5-report.md#fix-round-1-red-evidence",
                "green_reference": "task-5-report.md#fix-round-1-green-evidence",
                "refactor_reference": "task-5-report.md#fix-round-1-refactor-evidence",
                "status": "Passed",
                "recorded_at": datetime.now(UTC).isoformat(),
                "sanitization_review": "allowlist-only build metadata",
                "reviewer": "PLAN-FND",
                "live_owner_countersignature": None,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

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
APPROVED_FRONTEND_DIRECT = {
    "react": ("19.3.0", "MIT"),
    "react-dom": ("19.3.0", "MIT"),
    "@playwright/test": ("1.63.0", "Apache-2.0"),
    "@vitejs/plugin-react": ("6.1.1", "MIT"),
    "typescript": ("7.0.2", "Apache-2.0"),
    "vite": ("8.3.0", "MIT"),
}
APPROVED_NPM_LICENSES = frozenset(
    {"Apache-2.0", "BSD-3-Clause", "ISC", "MIT", "MPL-2.0"}
)


def verify_frontend_inputs() -> bool:
    """Verify manifest, lock, and installed packages without writes."""
    try:
        manifest = json.loads((FRONTEND / "package.json").read_text())
        lock = json.loads((FRONTEND / "package-lock.json").read_text())
        packages = lock["packages"]
        root = packages[""]
        declared = {
            **manifest["dependencies"],
            **manifest["devDependencies"],
        }
        if set(declared) != set(APPROVED_FRONTEND_DIRECT):
            return False
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
            expected_version, expected_license = APPROVED_FRONTEND_DIRECT[name]
            if (
                version != expected_version
                or locked["version"] != expected_version
                or locked.get("license") != expected_license
            ):
                return False
        for relative, record in packages.items():
            if not relative:
                continue
            package_json = FRONTEND / relative / "package.json"
            if not package_json.is_file() and record.get("optional"):
                continue
            if not package_json.is_file():
                return False
            if record.get("license") not in APPROVED_NPM_LICENSES:
                return False
            installed = json.loads(package_json.read_text())
            if installed.get("version") != record.get("version"):
                return False
        expected_packages = {relative for relative in packages if relative}
        for package_json in (FRONTEND / "node_modules").rglob("package.json"):
            package_parts = package_json.parent.relative_to(FRONTEND).parts
            node_modules_index = (
                len(package_parts) - 1 - package_parts[::-1].index("node_modules")
            )
            package_name_parts = package_parts[node_modules_index + 1 :]
            if len(package_name_parts) not in (1, 2) or (
                len(package_name_parts) == 2
                and not package_name_parts[0].startswith("@")
            ):
                continue
            relative = str(package_json.parent.relative_to(FRONTEND))
            if relative not in expected_packages:
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
                "red_reference": "task-5-report.md#fix-round-3-red-evidence",
                "green_reference": "task-5-report.md#fix-round-3-green-evidence",
                "refactor_reference": "task-5-report.md#fix-round-3-refactor-evidence",
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

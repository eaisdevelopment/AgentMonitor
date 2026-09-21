"""Build the M1 frontend from locked inputs and verify generated API artifacts."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

from evidence import actual_tool_versions, evidence_row

ROOT = Path(__file__).resolve().parents[3]
BACKEND_PYTHON = ROOT / "backend/.venv/bin/python"
FRONTEND = ROOT / "frontend"
APPROVED_FRONTEND_DIRECT = {
    "react": ("19.3.0", "MIT"),
    "react-dom": ("19.3.0", "MIT"),
    "@playwright/test": ("1.63.0", "Apache-2.0"),
    "@scarf/scarf": ("1.4.0", "Apache-2.0"),
    "@types/react": ("19.3.0", "MIT"),
    "@types/react-dom": ("19.3.0", "MIT"),
    "@vitejs/plugin-react": ("6.1.1", "MIT"),
    "swagger-ui-dist": ("5.33.0", "Apache-2.0"),
    "typescript": ("7.0.2", "Apache-2.0"),
    "vite": ("8.3.0", "MIT"),
}
APPROVED_NPM_LICENSES = frozenset(
    {"Apache-2.0", "BSD-3-Clause", "ISC", "MIT", "MPL-2.0"}
)


def direct_package_approved(
    name: str, declared_version: str, locked_version: str, license_name: str
) -> bool:
    """Pure exact-pin and direct-license policy for a reviewed package."""
    approved = APPROVED_FRONTEND_DIRECT.get(name)
    return approved is not None and (
        declared_version,
        locked_version,
        license_name,
    ) == (approved[0], approved[0], approved[1])


def installed_package_approved(
    record: Mapping[str, object], installed_version: str | None
) -> bool:
    """Pure policy for one locked versus installed package."""
    if record.get("license") not in APPROVED_NPM_LICENSES:
        return False
    if installed_version is None:
        return record.get("optional") is True
    return installed_version == record.get("version")


def installed_inventory_approved(expected: set[str], installed: set[str]) -> bool:
    """Optional packages may be absent, but unreviewed installs are refused."""
    return installed <= expected


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
        if manifest.get("scarfSettings") != {"enabled": False}:
            return False
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
            if not direct_package_approved(
                name, version, locked["version"], locked.get("license", "")
            ):
                return False
        for relative, record in packages.items():
            if not relative:
                continue
            package_json = FRONTEND / relative / "package.json"
            installed_version = (
                json.loads(package_json.read_text()).get("version")
                if package_json.is_file()
                else None
            )
            if not installed_package_approved(record, installed_version):
                return False
        expected_packages = {relative for relative in packages if relative}
        observed_packages: set[str] = set()
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
            observed_packages.add(relative)
        if not installed_inventory_approved(expected_packages, observed_packages):
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
        ["python3", "tools/automation/docs_assets.py", "--check"],
        ["npm", "--prefix", "frontend", "run", "typecheck"],
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
    print(
        "BUILD STATUS: Not Run fresh frozen install, release SBOM/notices "
        "and hosted artifact publication"
    )
    print(
        json.dumps(
            evidence_row(
                test_id="FND-BUILD-001",
                command_id="AUTO-BUILD",
                boundary="local production build from installed locked inputs",
                status="Passed",
                versions=actual_tool_versions(("python", "node", "npm", "uv")),
                requirement_ids=("NFR-API-002", "NFR-LIC-001"),
                acceptance_ids=("AC-TEST-004", "AC-TEST-006"),
                red_reference="docs/evidence/m1-audit-fixes.md#red",
                green_reference="docs/evidence/m1-audit-fixes.md#green",
                refactor_reference="docs/evidence/m1-audit-fixes.md#refactor",
            ),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

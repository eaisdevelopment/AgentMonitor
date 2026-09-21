"""Run the V1-M1 local quality checks without installing or publishing anything."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from shutil import which

from auto_build import verify_frontend_inputs
from evidence import actual_tool_versions, evidence_row

ROOT = Path(__file__).resolve().parents[3]
BACKEND_PYTHON = ROOT / "backend/.venv/bin/python"
BACKEND_RUFF = ROOT / "backend/.venv/bin/ruff"
BACKEND_MYPY = ROOT / "backend/.venv/bin/mypy"
BACKEND_DIRECT = {
    "fastapi": ("0.141.1", "MIT"),
    "uvicorn": ("0.53.0", "BSD-3-Clause"),
    "pydantic": ("2.13.5", "MIT"),
    "SQLAlchemy": ("2.0.54", "MIT"),
    "alembic": ("1.20.0", "MIT"),
    "argon2-cffi": ("25.1.0", "MIT"),
    "pytest": ("9.1.1", "MIT"),
    "ruff": ("0.16.8", "MIT"),
    "mypy": ("2.3.1", "MIT"),
}
M2_ARGON2_TRANSITIVE = {
    "argon2-cffi-bindings": ("26.1.0", "MIT"),
    "cffi": ("2.1.1", "MIT-0"),
    "pycparser": ("3.0", "BSD-3-Clause"),
}
ALLOWED_TEST_SETTING_LITERAL = 'SECRET = "AGENTMONITOR_TEST_BOOTSTRAP_SECRET'
PROHIBITED_SOURCE_PATTERNS = (
    r"(?:unittest\s*\.\s*mock|from\s+unittest\s+import\s+[^\n#]*\bmock\b|"
    r"pytest_mock|\bmagicmock\b|\bmonkeypatch\b)",
    r"\bshell\s*=\s*True\b|\bos\.system\(",
    r"\b(?:page|context)\s*\.\s*route(?:FromHAR)?\s*\(",
    r"\broute\s*\.\s*fulfill\s*\(",
)
SECRET_ASSIGNMENT_PATTERN = (
    r"(?m)^[ \t]*(?:(?:const|let|var)[ \t]+)?(?:self\.|this\.)?"
    r"(?:api[_-]?key|secret|password)(?:[ \t]*:[^=\r\n]+)?"
    r"[ \t]*=[ \t]*['\"][^'\"\r\n]{8,}"
    r"|^[ \t]*(?:api[_-]?key|secret|password)[ \t]*:[ \t]*"
    r"['\"][^'\"\r\n]{8,}"
    r"|['\"](?:api[_-]?key|secret|password)['\"][ \t]*:[ \t]*"
    r"['\"][^'\"\r\n]{8,}"
)


def run(command: list[str], *, environment: dict[str, str] | None = None) -> int:
    return subprocess.run(command, cwd=ROOT, check=False, env=environment).returncode


def approved_manifest_sections(manifest: dict[str, object]) -> bool:
    """Pure policy for the exact approved backend manifest sections."""
    project = manifest.get("project")
    groups = manifest.get("dependency-groups")
    return (
        isinstance(project, dict)
        and isinstance(groups, dict)
        and set(project)
        == {
            "name",
            "version",
            "requires-python",
            "dependencies",
        }
        and set(groups) == {"dev"}
    )


def source_is_allowed(content: str) -> bool:
    """Pure local-minimum policy; this is not a full secret or SAST scanner."""
    if any(
        re.search(pattern, content, flags=re.IGNORECASE)
        for pattern in PROHIBITED_SOURCE_PATTERNS
    ):
        return False
    return all(
        match.group() == ALLOWED_TEST_SETTING_LITERAL
        for match in re.finditer(
            SECRET_ASSIGNMENT_PATTERN, content, flags=re.IGNORECASE
        )
    )


def verify_backend_inputs() -> bool:
    """Check the admitted direct backend manifest, lock, and installed licenses."""
    try:
        manifest = tomllib.loads((ROOT / "backend/pyproject.toml").read_text())
        if not approved_manifest_sections(manifest):
            return False
        direct = {
            item.split("==", maxsplit=1)[0]: item.split("==", maxsplit=1)[1]
            for item in (
                manifest["project"]["dependencies"]
                + manifest["dependency-groups"]["dev"]
            )
        }
        if direct != {name: version for name, (version, _) in BACKEND_DIRECT.items()}:
            return False
        lock = tomllib.loads((ROOT / "backend/uv.lock").read_text())
        locked = {
            package["name"].lower(): package["version"] for package in lock["package"]
        }
        admitted_graph = BACKEND_DIRECT | M2_ARGON2_TRANSITIVE
        if any(
            locked.get(name.lower()) != version
            for name, (version, _) in admitted_graph.items()
        ):
            return False
        expected = json.dumps(admitted_graph, sort_keys=True)
        probe = (
            "import importlib.metadata as metadata, json, sys; "
            "expected=json.loads(sys.argv[1]); "
            "actual={name: (metadata.version(name), "
            "metadata.metadata(name).get('License-Expression') or "
            "metadata.metadata(name).get('License')) for name in expected}; "
            "raise SystemExit(0 if all(actual[name] == tuple(expected[name]) "
            "for name in expected) else 1)"
        )
        return (
            subprocess.run(
                [str(BACKEND_PYTHON), "-c", probe, expected],
                cwd=ROOT,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).returncode
            == 0
        )
    except (KeyError, OSError, TypeError, ValueError, tomllib.TOMLDecodeError):
        return False


def checked_source_paths() -> tuple[Path, ...]:
    """Return the real checkout source paths covered by local controls."""
    sources = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if sources.returncode:
        raise RuntimeError("local_source_inventory_unavailable")
    source_suffixes = {".py", ".ts", ".tsx", ".js", ".mjs", ".json", ".toml", ".yml"}
    return tuple(
        ROOT / relative
        for relative in sources.stdout.split("\x00")
        if relative
        and (ROOT / relative) != Path(__file__).resolve()
        and (ROOT / relative).suffix in source_suffixes
        and "node_modules" not in (ROOT / relative).parts
    )


def minimum_local_controls() -> bool:
    """Check tracked and untracked real source with the bounded local policy."""
    try:
        checked_paths = checked_source_paths()
    except RuntimeError:
        return False
    for path in checked_paths:
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return False
        if not source_is_allowed(content):
            return False
    return (
        (ROOT / "docs/dependencies/m1-foundation-admission.md").is_file()
        and (ROOT / "docs/dependencies/m1-foundation-lock-review.md").is_file()
        and verify_backend_inputs()
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
        ["npm", "--prefix", "frontend", "run", "typecheck"],
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
        "full secret/SAST/vulnerability scans, fresh frozen install, "
        "SBOM/notices release generation"
    )
    print(
        json.dumps(
            evidence_row(
                test_id="FND-QUALITY-001",
                command_id="AUTO-QUALITY",
                boundary="local minimum static and dependency-metadata checks",
                status="Passed",
                versions=actual_tool_versions(("python", "node", "npm", "uv")),
                requirement_ids=("NFR-TEST-002", "NFR-LIC-001"),
                acceptance_ids=("AC-TEST-002", "AC-TEST-006"),
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

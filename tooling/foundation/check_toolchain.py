"""Fail-closed local M1 toolchain preflight; not a release-runtime approval."""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

EXACT_VERSIONS = {"node": "22.23.2", "npm": "10.9.8", "uv": "0.11.16"}
VERSION_PATTERNS = {
    "node": r"v([0-9]+\.[0-9]+\.[0-9]+)",
    "npm": r"([0-9]+\.[0-9]+\.[0-9]+)",
    "uv": r"uv ([0-9]+\.[0-9]+\.[0-9]+)(?: \([^\r\n]*\))?",
}


def version_supported(tool: str, version: str) -> bool:
    """Apply the owner-approved local-development policy without I/O."""
    if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) is None:
        return False
    if tool == "python":
        return (3, 12, 3) <= tuple(map(int, version.split("."))) < (3, 13, 0)
    return EXACT_VERSIONS.get(tool) == version


def version_files_supported(python_text: str, node_text: str) -> bool:
    """Require exact reference files, including a single terminating newline."""
    return python_text == "3.12.3\n" and node_text == "22.23.2\n"


def inspect_tool(tool: str, executable: Path, node: Path) -> tuple[bool, str]:
    """Inspect only an explicitly supplied executable, never inherited settings."""
    if not executable.is_absolute():
        return False, "missing-or-unusable"
    try:
        with tempfile.TemporaryDirectory(prefix="agentmonitor-toolchain-") as scratch:
            result = subprocess.run(
                [str(executable), "--version"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
                env={
                    "PATH": str(node.parent) + os.pathsep + os.defpath,
                    "NPM_CONFIG_USERCONFIG": str(Path(scratch) / "user.npmrc"),
                    "NPM_CONFIG_GLOBALCONFIG": str(Path(scratch) / "global.npmrc"),
                    "NPM_CONFIG_UPDATE_NOTIFIER": "false",
                },
            )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return False, "missing-or-unusable"
    if result.returncode != 0 or result.stderr:
        return False, "missing-or-unusable"
    match = re.fullmatch(VERSION_PATTERNS[tool], result.stdout.strip())
    if match is None or not version_supported(tool, match.group(1)):
        return False, "unsupported-version"
    return True, match.group(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    for tool in EXACT_VERSIONS:
        parser.add_argument(f"--{tool}", required=True, type=Path)
    args = parser.parse_args()
    try:
        files_ok = version_files_supported(
            (args.root / ".python-version").read_bytes().decode("utf-8"),
            (args.root / ".node-version").read_bytes().decode("utf-8"),
        )
    except (OSError, UnicodeError):
        files_ok = False
    print(
        "version-files: OK" if files_ok else "version-files: FAIL mismatch-or-missing"
    )
    python_version = ".".join(map(str, sys.version_info[:3]))
    python_ok = (
        sys.implementation.name == "cpython"
        and sys.version_info.releaselevel == "final"
        and version_supported("python", python_version)
    )
    print(
        f"python: OK {python_version}"
        if python_ok
        else "python: FAIL unsupported-version"
    )
    passed = files_ok and python_ok
    for tool in EXACT_VERSIONS:
        ok, detail = inspect_tool(tool, getattr(args, tool), args.node)
        print(f"{tool}: {'OK' if ok else 'FAIL'} {detail}")
        passed = passed and ok
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

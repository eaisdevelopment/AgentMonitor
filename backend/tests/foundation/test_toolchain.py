"""FND-VER-001: pure policy and real explicitly selected tool processes."""

import importlib
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[3]
CHECKER = ROOT / "tooling/foundation/check_toolchain.py"


def checker_module() -> ModuleType:
    assert CHECKER.is_file(), "FND-VER-001: toolchain preflight is not implemented"
    return importlib.import_module("tooling.foundation.check_toolchain")


@pytest.mark.parametrize(
    ("tool", "version", "expected"),
    [
        ("python", "3.12.3", True),
        ("python", "3.12.14", True),
        ("python", "3.12.2", False),
        ("python", "3.13.0", False),
        ("python", "3.12.14rc1", False),
        ("node", "22.23.3", True),
        ("node", "22.23.1", False),
        ("node", "24.0.0", False),
        ("npm", "10.9.9", True),
        ("npm", "10.9.7", False),
        ("uv", "0.11.16", True),
        ("uv", "0.11.15", False),
        ("unknown", "1.0.0", False),
        ("node", "22.23.3\nextra", False),
    ],
)
def test_version_policy(tool: str, version: str, expected: bool) -> None:
    assert checker_module().version_supported(tool, version) is expected


@pytest.mark.parametrize(
    ("python_text", "node_text", "expected"),
    [
        ("3.12.3\n", "22.23.3\n", True),
        ("3.12.2\n", "22.23.3\n", False),
        ("3.12.3\n", "22.23.2\n", False),
        ("3.12.3\nextra\n", "22.23.3\n", False),
    ],
)
def test_version_file_policy(python_text: str, node_text: str, expected: bool) -> None:
    assert checker_module().version_files_supported(python_text, node_text) is expected


def selected_tools() -> dict[str, str]:
    tools = {}
    for name in ("node", "npm", "uv"):
        executable = shutil.which(name)
        assert executable is not None, f"required real tool is unavailable: {name}"
        tools[name] = executable
    return tools


def run_checker(tools: dict[str, str]) -> subprocess.CompletedProcess[str]:
    checker_module()
    command = [sys.executable, str(CHECKER), "--root", str(ROOT)]
    for name, executable in tools.items():
        command.extend([f"--{name}", executable])
    return subprocess.run(
        command, capture_output=True, text=True, check=False, timeout=30, env={}
    )


def test_real_selected_tools_and_version_files_pass() -> None:
    result = run_checker(selected_tools())
    assert result.returncode == 0, result.stdout
    assert result.stderr == ""
    assert result.stdout == (
        "version-files: OK\n"
        f"python: OK {sys.version_info.major}.{sys.version_info.minor}."
        f"{sys.version_info.micro}\n"
        "node: OK 22.23.3\nnpm: OK 10.9.9\nuv: OK 0.11.16\n"
    )


def test_real_wrong_executable_is_rejected_without_raw_output() -> None:
    tools = selected_tools()
    tools["node"] = sys.executable
    result = run_checker(tools)
    assert result.returncode == 1
    assert "node: FAIL unsupported-version\n" in result.stdout
    assert "Python " not in result.stdout
    assert result.stderr == ""


def test_real_non_executable_is_rejected_safely() -> None:
    tools = selected_tools()
    tools["uv"] = str(ROOT / ".python-version")
    result = run_checker(tools)
    assert result.returncode == 1
    assert "uv: FAIL missing-or-unusable\n" in result.stdout
    assert str(ROOT) not in result.stdout
    assert result.stderr == ""

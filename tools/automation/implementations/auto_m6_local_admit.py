"""Verify the narrow real local Ollama slice; never claim full M6 completion."""

from __future__ import annotations

import ast
import hashlib
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FILES = (
    "backend/src/agentmonitor/adapters/providers/ollama/local_catalog/source.py",
    "backend/src/agentmonitor/adapters/providers/ollama/manifest.py",
    "backend/src/agentmonitor/adapters/providers/ollama/installation.py",
    "backend/src/agentmonitor/contracts/ollama_local_catalog_v1.py",
    "backend/src/agentmonitor/composition/ollama_local_catalog.py",
    "backend/src/agentmonitor/adapters/platform/linux/processes.py",
    "backend/src/agentmonitor/adapters/providers/ollama/installation_discovery.py",
    "backend/src/agentmonitor/composition/linux_process_locations.py",
    "backend/src/agentmonitor/composition/linux_runtime_monitoring.py",
    "backend/src/agentmonitor/composition/ollama_installation_reconciliation.py",
    "backend/src/agentmonitor/composition/ollama_runtime_collection.py",
    "backend/src/agentmonitor/adapters/persistence/collection_control/state/runtime_backoff.py",
    "backend/migrations/catalog.toml",
    "backend/migrations/versions/v1_0708_m04_ollama_cloud_admission.py",
    "backend/src/agentmonitor/adapters/persistence/_shared/sqlite/schema/compatibility.py",
    "backend/src/agentmonitor/adapters/persistence/registry/sqlite/repository.py",
    "backend/src/agentmonitor/adapters/persistence/collection_control/sqlite/repository.py",
    "backend/src/agentmonitor/adapters/persistence/runtime_observation/sqlite/repository.py",
    "backend/src/agentmonitor/contracts/runtime_observation_v1.py",
    "backend/src/agentmonitor/contracts/collection_control_v1.py",
    "backend/tests/live/ollama/test_process_discovery.py",
    "backend/tests/integration/registry/test_ollama_installation_reconciliation.py",
    "backend/tests/integration/collection_control/test_ollama_runtime_run.py",
    "backend/tests/integration/collection_control/test_ollama_runtime_lifecycle.py",
    "backend/tests/collection_control/test_ollama_runtime_diagnostics.py",
    "tools/automation/test_m6_local_admit.py",
    "backend/tests/integration/api/test_ollama_process_observation_http.py",
    "backend/tests/integration/api/test_observation_http.py",
    "backend/tests/runtime_observation/test_linux_process_location_discovery.py",
    "backend/tests/runtime_observation/test_linux_runtime_policy.py",
    "backend/src/agentmonitor/composition/bootstrap.py",
    "backend/src/agentmonitor/api/v1/routers/providers.py",
    "backend/src/agentmonitor/api/v1/schemas/providers.py",
    "backend/src/agentmonitor/api/v1/dependencies.py",
    "contracts/openapi/agentmonitor-v1.json",
    "frontend/src/generated/api/index.ts",
    "frontend/src/shared/api/client.ts",
    "frontend/src/features/providers/ProviderPage.tsx",
    "frontend/src/features/accounts/AccountWorkspaceSummary.tsx",
    "frontend/src/features/accounts/LiveClaudeProcesses.tsx",
    "frontend/src/features/providers/ollamaFreshness.ts",
    "frontend/src/features/providers/ollamaStatus.ts",
    "frontend/src/app/dashboard.css",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/vite.config.ts",
    "frontend/dashboard.html",
    "frontend/tests/browser/p02/ollama_catalog.mjs",
    "frontend/tests/pure/ollama-freshness.mjs",
    "frontend/tests/pure/ollama-status.mjs",
    "backend/tests/integration/api/test_ollama_local_catalog_http.py",
    "backend/tests/contracts/test_ollama_local_catalog_v1.py",
    "backend/tests/adapters/providers/ollama/live/test_local_catalog.py",
    "backend/tests/adapters/providers/ollama/live/test_chunked_transport.py",
    "backend/tests/adapters/providers/ollama/live/test_catalog_concurrency.py",
    "backend/tests/adapters/providers/ollama/live/test_installation.py",
    "backend/tests/adapters/providers/ollama/test_deadline_policy.py",
    "backend/tests/adapters/providers/ollama/test_local_name_policy.py",
    "backend/tests/adapters/providers/ollama/test_local_source_policy.py",
    "backend/tests/adapters/providers/ollama/test_manifest.py",
    "backend/tests/adapters/providers/ollama/test_version_consistency.py",
    "frontend/tests/browser/p02/run_browser.py",
    "tooling/foundation/openapi_client.py",
    "tools/discovery/m6_local_inventory.py",
    "tools/automation/run.py",
    "tools/automation/routines.toml",
    "tools/automation/implementations/auto_m6_local_admit.py",
)

_RUNTIME_FAILURE_CODES = frozenset(
    {
        "internal_error",
        "ollama_runtime_backoff_store_unavailable",
        "ollama_runtime_tick_deadline",
        "ollama_runtime_installation_ambiguous",
        "ollama_installation_discovery_invalid",
        "ollama_installation_reconciliation_invalid",
        "ollama_installation_unavailable",
        "ollama_process_executable_changed",
        "registry_repository_unavailable",
        "linux_runtime_registered_installation_unresolved",
        "linux_runtime_installation_version_mismatch",
        "linux_runtime_database_missing",
        "linux_runtime_operation_deadline",
        "linux_runtime_receipt_invalid",
        "linux_runtime_projection_missing",
        "linux_runtime_collection_linux_deadline_exceeded",
        "linux_runtime_collection_linux_procfs_unavailable",
        "linux_runtime_collection_linux_boot_scope_unavailable",
        "linux_runtime_collection_linux_ollama_process_not_observed",
    }
)
_TEST_PATH = re.compile(r"(?:backend/tests|tools/automation)/[A-Za-z0-9_/]+\.py\Z")
_TEST_NAME = re.compile(r"test_[A-Za-z0-9_]+\Z")


def declared_test_ids(sources: Mapping[str, str]) -> frozenset[str]:
    """Allow only actual named tests in selected, checked-out project sources."""

    found = set()
    for path, source in sources.items():
        if _TEST_PATH.fullmatch(path) is None:
            continue
        try:
            parsed = ast.parse(source)
        except SyntaxError:
            continue
        for node in parsed.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if _TEST_NAME.fullmatch(node.name):
                    found.add(f"{path}::{node.name}")
            elif isinstance(node, ast.ClassDef) and re.fullmatch(
                r"[A-Za-z_][A-Za-z0-9_]*", node.name
            ):
                for method in node.body:
                    if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if _TEST_NAME.fullmatch(method.name):
                            found.add(f"{path}::{node.name}::{method.name}")
    return frozenset(found)


def safe_failure_summary(
    output: bytes, allowed_test_ids: frozenset[str]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Filter transient pytest output; never return messages or parameter values."""

    if len(output) > 2_097_152:
        return (), ()
    text = output.decode("utf-8", errors="replace")
    tests = {
        match.group(1)
        for match in re.finditer(r"^(?:FAILED|ERROR) ([A-Za-z0-9_/:.]+)", text, re.M)
        if match.group(1) in allowed_test_ids
    }
    tokens = set(re.findall(r"(?<![A-Za-z0-9_])[a-z][a-z0-9_]+(?![A-Za-z0-9_])", text))
    return tuple(sorted(tests)), tuple(sorted(tokens & _RUNTIME_FAILURE_CODES))


def _selected_test_ids(command: list[str]) -> frozenset[str]:
    sources = {}
    for argument in command:
        relative = argument.partition("::")[0]
        if not relative.startswith(("backend/tests/", "tools/automation/")):
            continue
        selected = ROOT / relative
        paths = selected.rglob("test_*.py") if selected.is_dir() else (selected,)
        for path in paths:
            if path.is_symlink() or not path.resolve().is_relative_to(ROOT.resolve()):
                continue
            if path.is_file() and path.stat().st_size <= 2_097_152:
                sources[path.relative_to(ROOT).as_posix()] = path.read_text()
    return declared_test_ids(sources)


def same_source(before: str, after: str) -> bool:
    return bool(before) and before == after


def source_digest() -> str:
    digest = hashlib.sha256()
    for name in FILES:
        path = ROOT / name
        if not path.is_file() or path.is_symlink():
            raise ValueError("source_missing")
        digest.update(name.encode("utf-8") + b"\0" + path.read_bytes())
    return digest.hexdigest()


def main() -> int:
    os.chdir(ROOT)
    executable = ROOT / "backend/.venv/bin/python"
    if not executable.is_file():
        print("M6 LOCAL ADMISSION: BLOCKED — backend environment unavailable")
        return 3
    try:
        before = source_digest()
    except (OSError, ValueError):
        print("M6 LOCAL ADMISSION: BLOCKED — source missing")
        return 3
    os.environ["PYTHONPATH"] = os.pathsep.join((str(ROOT / "backend/src"), str(ROOT)))
    commands = (
        (
            "freshness policy",
            [
                "node",
                "--experimental-strip-types",
                "frontend/tests/pure/ollama-freshness.mjs",
            ],
        ),
        (
            "status policy",
            [
                "node",
                "--experimental-strip-types",
                "frontend/tests/pure/ollama-status.mjs",
            ],
        ),
        (
            "real adapter and HTTP",
            [
                str(executable),
                "-m",
                "pytest",
                "-q",
                "-p",
                "tools.automation.pytest_no_skip",
                "backend/tests/contracts/test_ollama_local_catalog_v1.py",
                "backend/tests/adapters/providers/ollama",
                "backend/tests/integration/api/test_ollama_local_catalog_http.py",
                "backend/tests/live/ollama/test_process_discovery.py",
                "backend/tests/integration/registry/test_ollama_installation_reconciliation.py",
                "backend/tests/integration/collection_control/test_ollama_runtime_run.py",
                "backend/tests/integration/collection_control/test_ollama_runtime_lifecycle.py",
                "backend/tests/collection_control/test_ollama_runtime_diagnostics.py",
                "tools/automation/test_m6_local_admit.py",
                "backend/tests/integration/api/test_ollama_process_observation_http.py",
                "backend/tests/integration/api/test_observation_http.py::test_real_ollama_installation_has_registered_truthful_manifest",
                "backend/tests/runtime_observation/test_linux_process_location_discovery.py",
                "backend/tests/runtime_observation/test_linux_runtime_policy.py",
            ],
        ),
        (
            "real browser",
            [
                str(executable),
                "frontend/tests/browser/p02/run_browser.py",
                "ollama_catalog",
            ],
        ),
    )
    for label, command in commands:
        try:
            result = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                timeout=120,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            print(f"M6 LOCAL ADMISSION: BLOCKED — {label} could not run")
            return 3
        if result.returncode:
            print(f"M6 LOCAL ADMISSION: FAILED — {label}")
            try:
                allowed = _selected_test_ids(command)
            except (OSError, UnicodeError, ValueError):
                allowed = frozenset()
            tests, codes = safe_failure_summary(result.stdout, allowed)
            for test in tests:
                print(f"Failed project test: {test}")
            if codes:
                print("Closed runtime codes observed: " + ", ".join(codes))
            return 1
    try:
        after = source_digest()
    except (OSError, ValueError):
        print("M6 LOCAL ADMISSION: BLOCKED — source missing")
        return 3
    if not same_source(before, after):
        print("M6 LOCAL ADMISSION: FAILED — source changed during verification")
        return 1
    print("M6 LOCAL ADMISSION: PASSED — real local source and browser at this moment")
    print(f"Selected source-and-test digest: {after}")
    print("Nonempty models, natural failures and full M6 are not established.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

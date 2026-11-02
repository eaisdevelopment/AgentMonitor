"""Verify the narrow real local Ollama slice; never claim full M6 completion."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
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
    "backend/tests/live/ollama/test_process_discovery.py",
    "backend/tests/integration/registry/test_ollama_installation_reconciliation.py",
    "backend/tests/integration/collection_control/test_ollama_runtime_run.py",
    "backend/tests/integration/collection_control/test_ollama_runtime_lifecycle.py",
    "backend/tests/integration/api/test_ollama_process_observation_http.py",
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
                "backend/tests/integration/api/test_ollama_process_observation_http.py",
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

"""Run the V1-M1 real local test boundaries and print sanitized evidence rows."""

from __future__ import annotations

import json
import os
import select
import signal
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[3]
BACKEND_PYTHON = ROOT / "backend/.venv/bin/python"


def fail(code: str) -> NoReturn:
    print(f"AUTO-TEST: FAILED — {code}")
    raise SystemExit(1)


def run(command: list[str], *, environment: dict[str, str] | None = None) -> None:
    result = subprocess.run(command, cwd=ROOT, check=False, env=environment)
    if result.returncode:
        fail("required_local_boundary_failed")


def backend_environment() -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", os.defpath),
        "PYTHONPATH": str(ROOT / "backend/src"),
    }


def wait_for_origin(process: subprocess.Popen[str]) -> str:
    assert process.stdout is not None
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            break
        readable, _, _ = select.select([process.stdout], [], [], 0.1)
        if not readable:
            continue
        line = process.stdout.readline()
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("event") == "ready" and isinstance(event.get("origin"), str):
            return event["origin"]
    fail("loopback_runner_not_ready")


def run_browser_boundary() -> None:
    with tempfile.TemporaryDirectory(prefix="agentmonitor-m1-") as temporary:
        data_root = Path(temporary)
        data_root.chmod(0o700)
        config = data_root / "foundation.env"
        config.write_text("")
        config.chmod(0o600)
        migration = (
            "from pathlib import Path\n"
            "import sys\n"
            "from agentmonitor.adapters.persistence._shared.sqlite.core.policy "
            "import DatabaseRefV1\n"
            "from agentmonitor.adapters.persistence._shared.sqlite.schema."
            "compatibility import migrate_to_head\n"
            "root = Path(sys.argv[1])\n"
            "migrate_to_head(DatabaseRefV1(root / 'agentmonitor.db', root))\n"
        )
        run(
            [str(BACKEND_PYTHON), "-c", migration, str(data_root)],
            environment=backend_environment(),
        )
        server = subprocess.Popen(
            [
                str(BACKEND_PYTHON),
                "-m",
                "agentmonitor.composition.bootstrap",
                "--config",
                str(config),
                "--data-root",
                str(data_root),
                "--host",
                "127.0.0.1",
                "--port",
                "0",
                "--foundation-contract",
            ],
            cwd=ROOT,
            env=backend_environment(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            origin = wait_for_origin(server)
            run(
                [
                    str(ROOT / "frontend/node_modules/.bin/playwright"),
                    "test",
                    "frontend/tests/browser/foundation/shell.spec.ts",
                ],
                environment={
                    "PATH": os.defpath,
                    "AGENTMONITOR_TEST_ORIGIN": origin,
                },
            )
        finally:
            if server.poll() is None:
                server.send_signal(signal.SIGTERM)
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)


def evidence(test_id: str, boundary: str, status: str) -> dict[str, object]:
    return {
        "contract_id": "CTR-FND-008",
        "test_id": test_id,
        "requirement_ids": ["NFR-TEST-001", "NFR-TEST-002"],
        "acceptance_ids": ["AC-TEST-001", "AC-TEST-002", "AC-TEST-004"],
        "boundary_class": boundary,
        "command_registry_id": "AUTO-TEST",
        "environment_versions": [],
        "red_reference": "task-5-report.md#fix-round-1-red-evidence",
        "green_reference": "task-5-report.md#fix-round-1-green-evidence",
        "refactor_reference": "task-5-report.md#fix-round-1-refactor-evidence",
        "status": status,
        "recorded_at": datetime.now(UTC).isoformat(),
        "sanitization_review": (
            "allowlist-only command status; no provider or account data"
        ),
        "reviewer": "PLAN-FND",
        "live_owner_countersignature": None,
    }


def main() -> int:
    if not BACKEND_PYTHON.is_file():
        fail("admitted_backend_toolchain_missing")
    run(
        [
            "python3",
            "-m",
            "unittest",
            "tools.automation.test_run.AutomationRoutineTests.test_m1_routines_resolve_from_canonical_catalog",
            "tools.automation.test_run.AutomationRoutineTests.test_catalog_index_rejects_duplicate_routine_ids",
            "tools.automation.test_run.AutomationRoutineTests.test_operational_limited_routine_requires_named_limitations",
            "tools.automation.test_run.AutomationRoutineTests.test_real_catalog_defines_every_mandatory_routine",
            "tools.automation.test_run.AutomationRoutineTests.test_blocked_routine_fails_closed_in_the_real_checkout",
            "tools.automation.test_run.AutomationRoutineTests.test_m1_quality_and_build_report_required_local_controls",
            "tools.docs.test_check",
            "tools.planning.test_implementation_backlog",
            "tools.planning.test_validate_plans",
        ]
    )
    run(
        [
            str(BACKEND_PYTHON),
            "-m",
            "pytest",
            "backend/tests/foundation",
            "backend/tests/persistence/sqlite",
            "backend/tests/integration/foundation",
            "-q",
            "--tb=short",
        ],
        environment=backend_environment(),
    )
    run(
        [str(BACKEND_PYTHON), "tooling/foundation/openapi_client.py", "--check"],
        environment=backend_environment(),
    )
    run([str(ROOT / "frontend/node_modules/.bin/vite"), "build", "frontend"])
    run_browser_boundary()
    for row in (
        evidence("FND-TEST-001", "T1/T2/T3/T4 real local stack", "Passed"),
        evidence("FND-TEST-PLATFORM", "T5 workstation platform", "Not Run"),
        evidence("FND-TEST-PROVIDER", "T6 live provider/account", "Not Run"),
        evidence("FND-TEST-OPERATIONS", "T7 native lifecycle", "Not Run"),
        evidence("FND-CI-001", "hosted GitLab pipeline", "Not Run"),
    ):
        print(json.dumps(row, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

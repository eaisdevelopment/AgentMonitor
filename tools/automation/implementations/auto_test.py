"""Run the V1-M1 real local test boundaries and print sanitized evidence rows."""

from __future__ import annotations

import json
import os
import select
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from shutil import which
from typing import NoReturn

from evidence import actual_tool_versions, evidence_row

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


def browser_environment(origin: str) -> dict[str, str]:
    """Provide only the resolved Node directory needed by Playwright's shebang."""
    node = which("node")
    if node is None:
        fail("admitted_node_command_missing")
    return {
        "PATH": str(Path(node).parent) + os.pathsep + os.defpath,
        "AGENTMONITOR_TEST_ORIGIN": origin,
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
                environment=browser_environment(origin),
            )
        finally:
            if server.poll() is None:
                server.send_signal(signal.SIGTERM)
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)


def main() -> int:
    if not BACKEND_PYTHON.is_file():
        fail("admitted_backend_toolchain_missing")
    run(
        [
            "python3",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tools",
            "-p",
            "test_*.py",
        ]
    )
    m0_exit = subprocess.run(
        ["python3", "tools/automation/run.py", "AUTO-M0-G1-EXIT"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    m0_status = {0: "Passed", 2: "Failed", 3: "Blocked"}.get(
        m0_exit.returncode, "Failed"
    )
    print(
        f"SEPARATE M0-G1 APPROVAL: {m0_status} "
        f"(exit {m0_exit.returncode}; outside the M1 acceptance gate)"
    )
    print(
        json.dumps(
            evidence_row(
                test_id="M0-G1-EXIT",
                command_id="AUTO-M0-G1-EXIT",
                boundary="separate exact-digest M0 approval gate",
                status=m0_status,
                versions=actual_tool_versions(("python",))
                if m0_status == "Passed"
                else (),
                requirement_ids=("NFR-TEST-002",),
                acceptance_ids=("AC-TEST-002",),
            ),
            sort_keys=True,
        )
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
    versions = actual_tool_versions(("python", "node", "npm", "uv", "google-chrome"))
    for row in (
        evidence_row(
            test_id="FND-TEST-001",
            command_id="AUTO-TEST",
            boundary="T1/T2/T3/T4 real local stack",
            status="Passed",
            versions=versions,
            requirement_ids=("NFR-TEST-001", "NFR-TEST-002"),
            acceptance_ids=("AC-TEST-001", "AC-TEST-002", "AC-TEST-004"),
            red_reference="docs/evidence/m1-audit-fixes.md#red",
            green_reference="docs/evidence/m1-audit-fixes.md#green",
            refactor_reference="docs/evidence/m1-audit-fixes.md#refactor",
        ),
        *(
            evidence_row(
                test_id=test_id,
                command_id="AUTO-TEST",
                boundary=boundary,
                status="Not Run",
                versions=(),
            )
            for test_id, boundary in (
                ("FND-TEST-PLATFORM", "T5 workstation platform"),
                ("FND-TEST-PROVIDER", "T6 live provider/account"),
                ("FND-TEST-OPERATIONS", "T7 native lifecycle"),
                ("FND-CI-001", "hosted GitLab pipeline"),
            )
        ),
    ):
        print(json.dumps(row, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

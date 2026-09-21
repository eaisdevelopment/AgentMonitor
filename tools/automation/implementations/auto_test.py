"""Run the V1-M2 real local test boundaries and print sanitized evidence rows."""

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
M0_OWNER_LOCAL_ASSETS = (
    ROOT / ".venv-m0-g1/bin/python",
    ROOT / ".venv-m0-g1/bin/gitleaks",
    ROOT / ".agentmonitor-local/m0-g1-exit.json",
)
M1_TOOL_TEST_MODULES = (
    "tools.automation.test_run",
    "tools.docs.test_check",
    "tools.git.test_preflight",
    "tools.planning.test_implementation_backlog",
    "tools.planning.test_validate_plans",
)


def fail(code: str) -> NoReturn:
    print(f"AUTO-TEST: FAILED — {code}")
    raise SystemExit(1)


def run(command: list[str], *, environment: dict[str, str] | None = None) -> None:
    result = subprocess.run(command, cwd=ROOT, check=False, env=environment)
    if result.returncode:
        fail("required_local_boundary_failed")


def m2_local_suite_commands() -> dict[str, list[str]]:
    """Select complete M2 backend and production-browser suites, without exclusions."""
    browser_runner = "frontend/tests/browser/p02/run_browser.py"
    return {
        "backend": [
            str(BACKEND_PYTHON),
            "-m",
            "pytest",
            "backend/tests",
            "-q",
            "--tb=short",
        ],
        "p02_all": [
            str(BACKEND_PYTHON),
            browser_runner,
            "all",
            "--no-build",
        ],
        "p02_security": [
            str(BACKEND_PYTHON),
            browser_runner,
            "security_boundary",
            "--no-build",
        ],
    }


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
    selected_browser = os.environ.get("AGENTMONITOR_TEST_BROWSER", "chrome")
    if selected_browser not in {"chrome", "chromium"}:
        fail("test_browser_selection_invalid")
    environment = {
        "PATH": str(Path(node).parent) + os.pathsep + os.defpath,
        "AGENTMONITOR_TEST_ORIGIN": origin,
        "AGENTMONITOR_TEST_BROWSER": selected_browser,
    }
    if selected_browser == "chromium":
        browser_root = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
        if not browser_root or not Path(browser_root).is_dir():
            fail("playwright_browser_root_unavailable")
        environment["PLAYWRIGHT_BROWSERS_PATH"] = browser_root
    return environment


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
    if all(path.is_file() for path in M0_OWNER_LOCAL_ASSETS):
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
        print("M0 OWNER-LOCAL TOOL SUITE: Passed with real local assets")
    else:
        print("M0 OWNER-LOCAL TOOL SUITE: Not Run — local assets unavailable")
        print(
            json.dumps(
                evidence_row(
                    test_id="M0-G1-LOCAL-TOOLS",
                    command_id="AUTO-TEST",
                    boundary="separate owner-local M0 G1 tool tests",
                    status="Not Run",
                    versions=(),
                ),
                sort_keys=True,
            )
        )
        run(["python3", "-m", "unittest", *M1_TOOL_TEST_MODULES])
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
        f"(exit {m0_exit.returncode}; outside the M2 local acceptance gate)"
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
    suite_commands = m2_local_suite_commands()
    run(suite_commands["backend"], environment=backend_environment())
    run(
        [str(BACKEND_PYTHON), "tooling/foundation/openapi_client.py", "--check"],
        environment=backend_environment(),
    )
    run([str(ROOT / "frontend/node_modules/.bin/vite"), "build", "frontend"])
    run_browser_boundary()
    run(suite_commands["p02_all"], environment=backend_environment())
    run(suite_commands["p02_security"], environment=backend_environment())
    browser_tool = (
        "playwright-chromium"
        if os.environ.get("AGENTMONITOR_TEST_BROWSER", "chrome") == "chromium"
        else "google-chrome"
    )
    versions = actual_tool_versions(("python", "node", "npm", "uv", browser_tool))
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
        evidence_row(
            test_id="M2-LOCAL-001",
            command_id="AUTO-TEST",
            boundary=(
                "T2/T3/T4 migrated SQLite, production Uvicorn, "
                "generated client, and installed Chrome"
            ),
            status="Passed",
            versions=versions,
            requirement_ids=("FR-IAM-007", "NFR-TEST-001", "NFR-TEST-002"),
            acceptance_ids=("AC-UI-001", "AC-TEST-001", "AC-TEST-003", "AC-TEST-006"),
            red_reference="docs/evidence/m2-st-api-002.md#red-evidence",
            green_reference="docs/evidence/m2-st-api-002.md#green-and-refactor-evidence",
            refactor_reference="docs/evidence/m2-st-api-002.md#green-and-refactor-evidence",
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
                ("M2-TEST-PLATFORM", "T5 workstation platform"),
                ("M2-TEST-PROVIDER", "T6 live provider/account"),
                ("M2-TEST-OPERATIONS", "T7 native lifecycle"),
                ("M2-CI-001", "hosted GitLab pipeline"),
            )
        ),
    ):
        print(json.dumps(row, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

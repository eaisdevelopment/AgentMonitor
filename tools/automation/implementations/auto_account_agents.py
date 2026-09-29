"""Real owner-selected account agent view; no automated owner attestation."""

import os
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PYTHON = ROOT / "backend/.venv/bin/python"


def main() -> int:
    required = (
        "AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT",
        "AGENTMONITOR_TEST_DASHBOARD_ORIGIN",
        "AGENTMONITOR_TEST_AGENT_ACCOUNT_ID",
        "AGENTMONITOR_TEST_AGENT_PID",
        "AGENTMONITOR_TEST_AGENT_DATA_ROOT",
    )
    if not all(os.environ.get(name) for name in required):
        print(
            "AUTO-ACCOUNT-AGENTS: BLOCKED — "
            "real dashboard/account/PID/data root required"
        )
        return 3
    environment = dict(os.environ, PYTHONPATH=str(ROOT / "backend/src"))
    commands = (
        [str(PYTHON), "tooling/foundation/openapi_client.py", "--check"],
        ["npm", "--prefix", "frontend", "run", "typecheck"],
        ["npm", "--prefix", "frontend", "run", "build"],
        [
            str(PYTHON),
            "-m",
            "pytest",
            "-q",
            "--tb=short",
            "backend/tests/runtime_observation/test_owner_process_association.py",
            "backend/tests/runtime_observation/test_owner_association_settings.py",
            "backend/tests/integration/api/test_owner_process_association_routes.py",
            "backend/tests/integration/api/test_openapi_policy.py",
        ],
        ["node", "tools/ui/verify_account_agents.mjs"],
    )
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, env=environment, check=False)
        if result.returncode:
            print(
                "AUTO-ACCOUNT-AGENTS: "
                + ("BLOCKED" if result.returncode == 3 else "FAILED")
                + " — executable boundary rejected"
            )
            return result.returncode
    if environment.get("AGENTMONITOR_TEST_DUPLICATE_IDENTITY") == "1":
        result = subprocess.run(
            ["node", "tools/ui/verify_duplicate_identity.mjs"],
            cwd=ROOT,
            env=environment,
            check=False,
        )
        if result.returncode:
            return result.returncode
    root = Path(environment["AGENTMONITOR_TEST_AGENT_DATA_ROOT"])
    try:
        if not root.is_absolute() or root.is_symlink():
            raise ValueError("private_root_required")
        info = root.stat()
        if stat.S_IMODE(info.st_mode) != 0o700 or info.st_uid != os.getuid():
            raise ValueError("private_root_required")
        # Late static imports: dispatcher may use system Python; the real
        # contract/repository remain dependency-free for read-only verification.
        sys.path.insert(0, str(ROOT / "backend/src"))
        from agentmonitor.adapters.persistence.runtime_observation.settings import (
            repository,
        )
        from agentmonitor.composition.linux_process_locations import (
            read_live_claude_process_locations_v1,
        )
        from agentmonitor.modules.runtime_observation.application.ports import (
            owner_association_key,
        )

        first = repository.OwnerAssociationSettingsRepositoryV1(root).records()
        reopened = repository.OwnerAssociationSettingsRepositoryV1(root).records()
        if first != reopened:
            raise ValueError("settings_changed_during_reopen")
        observed = read_live_claude_process_locations_v1()
        pid = int(environment["AGENTMONITOR_TEST_AGENT_PID"])
        item = next(
            (value for value in observed.items if value.identity.pid == pid), None
        )
        if (
            observed.availability.state != "available"
            or item is None
            or item.snapshot is None
        ):
            raise ValueError("actual_owner_terminal_required")
        key = owner_association_key(item.identity, item.snapshot.executable_identity)
        record = reopened.get(key)
        if (
            record is None
            or record.account_id is None
            or record.account_id.value
            != environment["AGENTMONITOR_TEST_AGENT_ACCOUNT_ID"]
        ):
            raise ValueError("owner_completed_account_link_required")
    except (OSError, RuntimeError, ValueError, TypeError):
        print(
            "AUTO-ACCOUNT-AGENTS: BLOCKED — "
            "current owner-confirmed persistent link required"
        )
        return 3
    environment["AGENTMONITOR_TEST_REQUIRE_CONFIRMED_AGENT"] = "1"
    result = subprocess.run(
        ["node", "tools/ui/verify_account_agents.mjs"],
        cwd=ROOT,
        env=environment,
        check=False,
    )
    if result.returncode:
        return result.returncode
    print(
        "AUTO-ACCOUNT-AGENTS: PASSED — real HTTP guards, owner receipt, "
        "safe filesystem reopen and built account agent view"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

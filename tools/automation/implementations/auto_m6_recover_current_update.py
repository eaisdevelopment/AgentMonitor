"""Recover the fixed dashboard same-schema update."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

_RUNTIME = Path("/home/dev/.local/share/agentmonitor/releases/m6-runtime-2fedf0809fc9")
_ROOT = Path(__file__).resolve().parents[3]
_FIXED_SOURCE = Path(
    "/home/dev/.local/share/agentmonitor/worktrees/m6-signal-composition"
)


def _checkout_revision() -> str:
    env = {"PATH": "/usr/bin:/bin", "HOME": "/home/dev", "LANG": "C"}
    status = subprocess.run(
        ["/usr/bin/git", "status", "--porcelain"],
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    revision = subprocess.run(
        ["/usr/bin/git", "rev-parse", "--verify", "HEAD"],
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    lines = status.stdout.splitlines()
    allowed = {"?? backend/.venv", "?? frontend/node_modules"}
    if (
        status.returncode
        or revision.returncode
        or any(line not in allowed for line in lines)
        or any(not (_ROOT / line[3:]).is_symlink() for line in lines)
        or re.fullmatch(r"[a-f0-9]{40}", revision.stdout.strip()) is None
    ):
        raise RuntimeError("operator_checkout_not_clean")
    return revision.stdout.strip()


def main() -> int:
    if len(sys.argv) != 1:
        print("M6 CURRENT UPDATE RECOVERY: BLOCKED — no target arguments are accepted")
        return 3
    if _ROOT != _FIXED_SOURCE:
        print("M6 CURRENT UPDATE RECOVERY: BLOCKED — fixed candidate checkout required")
        return 3
    try:
        revision = _checkout_revision()
        sys.path.insert(0, str(_ROOT))
        from tools.automation.implementations.m6_runtime_integrity import (
            _runtime_digest,
        )

        inherited_revision = os.environ.get(
            "AGENTMONITOR_UPDATE_RECOVERY_CHECKOUT_REVISION"
        )
        if inherited_revision is not None and inherited_revision != revision:
            raise RuntimeError("operator_checkout_changed")
        python = Path("/usr/bin/python3.12")
        if (
            hashlib.sha256(python.read_bytes()).hexdigest()
            != "e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f"
        ):
            raise RuntimeError("operator_runtime_changed")
        if (
            _runtime_digest(_RUNTIME)
            != "84112363e7525a6ff42764bfaf7f9dfacbfb22399dfe8275898ac105b3d7edbc"
        ):
            raise RuntimeError("operator_runtime_changed")
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError):
        print(
            "M6 CURRENT UPDATE RECOVERY: BLOCKED — operator checkout or runtime unavailable"
        )
        return 3
    if Path(sys.prefix).resolve() != _RUNTIME:
        try:
            os.execve(
                str(_RUNTIME / "bin/python"),
                [str(_RUNTIME / "bin/python"), str(Path(__file__).resolve())],
                {
                    "PATH": "/usr/bin:/bin",
                    "HOME": "/home/dev",
                    "LANG": "C",
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "AGENTMONITOR_UPDATE_RECOVERY_CHECKOUT_REVISION": revision,
                },
            )
        except OSError:
            print("M6 CURRENT UPDATE RECOVERY: BLOCKED — private runtime unavailable")
            return 3
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "backend/src"))
    try:
        from tools.automation.implementations.m6_cutover import (
            recover_current_schema_update,
        )

        status = recover_current_schema_update()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        print(
            "M6 CURRENT UPDATE RECOVERY: BLOCKED — review the transition journal and service state"
        )
        return 3
    if status not in {
        "candidate_ready_restart_restored",
        "baseline_ready_restart_restored",
    }:
        print("M6 CURRENT UPDATE RECOVERY: BLOCKED — cutover result unverified")
        return 3
    print(
        "M6 CURRENT UPDATE RECOVERY: same-schema transition recovered and original restart policy restored"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

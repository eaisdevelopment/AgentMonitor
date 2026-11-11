"""Update the fixed dashboard to a sealed same-schema candidate."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import time
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


def _admitted_revision(arguments: list[str]) -> str:
    """Admit this controller before accessing its runtime or installed service."""
    expected = None
    if arguments:
        if (
            len(arguments) != 1
            or re.fullmatch(r"--expected-revision=[a-f0-9]{40}", arguments[0]) is None
        ):
            raise RuntimeError("operator_arguments_invalid")
        expected = arguments[0].split("=", 1)[1]
    elif _ROOT != _FIXED_SOURCE:
        raise RuntimeError("operator_fixed_checkout_required")
    revision = _checkout_revision()
    if expected is not None and revision != expected:
        raise RuntimeError("operator_checkout_revision_mismatch")
    return revision


def main() -> int:
    try:
        revision = _admitted_revision(sys.argv[1:])
        sys.path.insert(0, str(_ROOT))
        from tools.automation.implementations.m6_runtime_integrity import (
            _runtime_digest,
        )

        inherited_revision = os.environ.get("AGENTMONITOR_UPDATE_CHECKOUT_REVISION")
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
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        reason = {
            "operator_arguments_invalid": "no target arguments are accepted",
            "operator_fixed_checkout_required": "fixed candidate checkout required",
            "operator_checkout_revision_mismatch": "expected revision does not match",
        }.get(str(error), "operator checkout or runtime unavailable")
        print("M6 CURRENT UPDATE: BLOCKED — " + reason)
        return 3
    if Path(sys.prefix).resolve() != _RUNTIME:
        try:
            os.execve(
                str(_RUNTIME / "bin/python"),
                [
                    str(_RUNTIME / "bin/python"),
                    str(Path(__file__).resolve()),
                    *sys.argv[1:],
                ],
                {
                    "PATH": "/usr/bin:/bin",
                    "HOME": "/home/dev",
                    "LANG": "C",
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "AGENTMONITOR_UPDATE_CHECKOUT_REVISION": revision,
                },
            )
        except OSError:
            print("M6 CURRENT UPDATE: BLOCKED — private runtime unavailable")
            return 3
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "backend/src"))
    try:
        from tools.automation.implementations.m6_cutover import (
            CutoverError,
            finalize_candidate,
            update_current_schema,
        )

        if _admitted_revision(sys.argv[1:]) != revision:
            raise RuntimeError("operator_checkout_changed")
        status = (
            update_current_schema(candidate=_ROOT, expected_revision=revision)
            if sys.argv[1:]
            else update_current_schema()
        )
        if status == "candidate_started_product_verification_required":
            deadline = time.monotonic() + 15
            while True:
                try:
                    status = finalize_candidate()
                    break
                except CutoverError as error:
                    if (
                        str(error)
                        not in {
                            "candidate_listener_unverified",
                            "candidate_http_unverified",
                            "candidate_start_unverified",
                        }
                        or time.monotonic() >= deadline
                    ):
                        raise
                    time.sleep(0.1)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        from tools.automation.implementations.m6_cutover_diagnostics import (
            cutover_failure_message,
        )

        print(cutover_failure_message(error))
        return 3
    if status != "candidate_ready_restart_restored":
        print("M6 CURRENT UPDATE: BLOCKED — cutover result unverified")
        return 3
    print(
        "M6 CURRENT UPDATE: candidate local readiness verified and "
        "original restart policy restored"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

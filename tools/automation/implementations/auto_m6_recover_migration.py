"""Recover the fixed dashboard's recorded pre-start migration only."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_RUNTIME = Path("/home/dev/.local/share/agentmonitor/releases/m6-runtime-2fedf0809fc9")
_ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    if len(sys.argv) != 1:
        print("M6 MIGRATION RECOVERY: BLOCKED — no target arguments are accepted")
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
                },
            )
        except OSError:
            print("M6 MIGRATION RECOVERY: BLOCKED — private runtime unavailable")
            return 3
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "backend/src"))
    from tools.automation.implementations.m6_cutover import (
        recover_interrupted_migration,
    )

    try:
        status = recover_interrupted_migration()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        print(
            "M6 MIGRATION RECOVERY: BLOCKED — review the transition journal and service state"
        )
        return 3
    if status != "migration_recovered":
        print("M6 MIGRATION RECOVERY: BLOCKED — recovery result unverified")
        return 3
    print(
        "M6 MIGRATION RECOVERY: migration recovered; dashboard remains stopped and start-blocked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

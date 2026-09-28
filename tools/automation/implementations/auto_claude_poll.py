"""Run the bounded real Claude polling gate; no absent owner input is a pass."""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    selected = os.environ.get("AGENTMONITOR_TEST_OWNER_DATA_ROOT")
    if selected is None:
        print("AUTO-CLAUDE-POLL: BLOCKED — explicit owner data root required")
        return 3
    root = Path(selected)
    if not root.is_absolute() or not (root / "agentmonitor.db").is_file():
        print("AUTO-CLAUDE-POLL: FAILED — invalid owner data root")
        return 1
    result = subprocess.run(
        [
            str(ROOT / "backend/.venv/bin/python"),
            "-m",
            "pytest",
            "-q",
            "--tb=short",
            "backend/tests/collection_control/test_polling.py",
            "backend/tests/integration/collection_control/test_dashboard_polling.py",
        ],
        cwd=ROOT,
        check=False,
    )
    if result.returncode:
        return result.returncode
    print("AUTO-CLAUDE-POLL: PASSED — real quota, preserved registry, restart cadence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

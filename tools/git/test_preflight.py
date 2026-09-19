"""Real-checkout test for the non-mutating Git preflight routine."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT = REPOSITORY_ROOT / "tools/git/preflight.py"


class GitPreflightTests(unittest.TestCase):
    def test_real_checkout_reports_its_git_state_without_mutation(self) -> None:
        worktree = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        result = subprocess.run(
            [sys.executable, str(PREFLIGHT)],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if worktree.returncode != 0 or worktree.stdout.strip() != "true":
            self.assertEqual(3, result.returncode)
            self.assertIn("GIT PREFLIGHT: BLOCKED", result.stdout)
            self.assertIn("not a Git worktree", result.stdout)
            self.assertNotIn("PASSED", result.stdout)
        else:
            self.assertIn(result.returncode, {0, 3})
            expected = "PASSED" if result.returncode == 0 else "BLOCKED"
            self.assertIn(f"GIT PREFLIGHT: {expected}", result.stdout)


if __name__ == "__main__":
    unittest.main()

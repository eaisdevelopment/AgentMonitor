"""Real-checkout test for the non-mutating Git preflight routine."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT = REPOSITORY_ROOT / "tools/git/preflight.py"


class GitPreflightTests(unittest.TestCase):
    def test_local_commit_preflight_does_not_require_a_remote(self) -> None:
        """The real checkout may commit locally before GitLab is configured."""
        result = subprocess.run(
            [sys.executable, str(PREFLIGHT), "--operation", "commit"],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotIn("no Git remote is configured", result.stdout)
        self.assertNotIn("current branch has no upstream", result.stdout)
        local_checks = (
            ["git", "symbolic-ref", "--quiet", "--short", "HEAD"],
            ["git", "config", "--get", "user.name"],
            ["git", "config", "--get", "user.email"],
        )
        local_ready = all(
            subprocess.run(
                command,
                cwd=REPOSITORY_ROOT,
                check=False,
                capture_output=True,
                text=True,
            ).returncode
            == 0
            for command in local_checks
        )
        self.assertEqual(0 if local_ready else 3, result.returncode)

    def test_remote_push_preflight_requires_the_real_remote(self) -> None:
        remotes = subprocess.run(
            ["git", "remote"],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        result = subprocess.run(
            [sys.executable, str(PREFLIGHT), "--operation", "push"],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if remotes.returncode == 0 and not remotes.stdout.split():
            self.assertEqual(3, result.returncode)
            self.assertIn("no Git remote is configured", result.stdout)

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

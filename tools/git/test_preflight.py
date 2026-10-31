"""Real-checkout test for the non-mutating Git preflight routine."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT = REPOSITORY_ROOT / "tools/git/preflight.py"


class GitPreflightTests(unittest.TestCase):
    @staticmethod
    def _git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )

    @staticmethod
    def _run_preflight(
        root: Path,
        *,
        selector: str | None = None,
        operation: str = "commit",
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        if selector is None:
            environment.pop("AGENTMONITOR_M5_DETACHED_GIT_PREFLIGHT", None)
        else:
            environment["AGENTMONITOR_M5_DETACHED_GIT_PREFLIGHT"] = selector
        return subprocess.run(
            [sys.executable, "tools/git/preflight.py", "--operation", operation],
            cwd=root,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_m5_selector_accepts_only_one_clean_stable_detached_commit(self) -> None:
        """M5's immutable service checkout has a bounded Git-preflight path."""

        with tempfile.TemporaryDirectory(prefix="agentmonitor-git-preflight-") as raw:
            repository = Path(raw) / "repository"
            detached = Path(raw) / "detached"
            (repository / "tools/git").mkdir(parents=True)
            shutil.copy2(PREFLIGHT, repository / "tools/git/preflight.py")
            self.assertEqual(
                0, self._git(repository, "init", "--initial-branch=main").returncode
            )
            self.assertEqual(
                0,
                self._git(
                    repository, "config", "user.name", "AgentMonitor Test"
                ).returncode,
            )
            self.assertEqual(
                0,
                self._git(
                    repository,
                    "config",
                    "user.email",
                    "agentmonitor@example.invalid",
                ).returncode,
            )
            (repository / "tracked.txt").write_text("tracked\n", encoding="utf-8")
            self.assertEqual(0, self._git(repository, "add", ".").returncode)
            self.assertEqual(
                0, self._git(repository, "commit", "-m", "initial").returncode
            )

            attached = self._run_preflight(repository, selector="1")
            self.assertEqual(3, attached.returncode)
            self.assertIn(
                "M5 detached preflight requires detached HEAD", attached.stdout
            )

            self.assertEqual(
                0,
                self._git(
                    repository, "worktree", "add", "--detach", str(detached), "HEAD"
                ).returncode,
            )
            ordinary = self._run_preflight(detached)
            self.assertEqual(3, ordinary.returncode)
            self.assertIn("HEAD is detached", ordinary.stdout)

            selected = self._run_preflight(detached, selector="1")
            self.assertEqual(0, selected.returncode)
            self.assertIn("M5 DETACHED REVISION: PASSED", selected.stdout)

            (detached / "untracked.txt").write_text("dirty\n", encoding="utf-8")
            dirty = self._run_preflight(detached, selector="1")
            self.assertEqual(3, dirty.returncode)
            self.assertIn(
                "M5 detached preflight requires a clean checkout", dirty.stdout
            )

    def test_m5_selector_rejects_invalid_value_and_noncommit_operation(self) -> None:
        """The exception is not an alternate generic push or release path."""

        invalid = self._run_preflight(REPOSITORY_ROOT, selector="yes")
        self.assertEqual(3, invalid.returncode)
        self.assertIn("M5 detached preflight selector is invalid", invalid.stdout)

        noncommit = self._run_preflight(
            REPOSITORY_ROOT, selector="1", operation="push"
        )
        self.assertEqual(3, noncommit.returncode)
        self.assertIn("M5 detached preflight is limited to commit", noncommit.stdout)

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

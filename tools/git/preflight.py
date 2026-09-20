"""Read-only, fail-closed Git preflight for the real AgentMonitor checkout."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Literal

Operation = Literal["commit", "push", "release"]


def _git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )


def preflight(root: Path, *, operation: Operation = "commit") -> tuple[str, list[str]]:
    """Check the real Git boundary required by the selected operation."""
    blockers: list[str] = []
    worktree = _git(root, "rev-parse", "--is-inside-work-tree")
    if worktree.returncode != 0 or worktree.stdout.strip() != "true":
        return "blocked", ["checkout is not a Git worktree"]

    top_level = _git(root, "rev-parse", "--show-toplevel")
    if top_level.returncode != 0 or Path(top_level.stdout.strip()).resolve() != root:
        blockers.append("checkout root does not match the Git top-level directory")
    branch = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    if branch.returncode != 0:
        blockers.append("HEAD is detached or the current branch cannot be resolved")
    if operation in ("push", "release"):
        remotes = _git(root, "remote")
        if remotes.returncode != 0 or not remotes.stdout.split():
            blockers.append("no Git remote is configured")
        upstream = _git(
            root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"
        )
        if upstream.returncode != 0:
            blockers.append("current branch has no upstream")
    identity_name = _git(root, "config", "--get", "user.name")
    identity_email = _git(root, "config", "--get", "user.email")
    if identity_name.returncode != 0 or not identity_name.stdout.strip():
        blockers.append("Git user.name is not configured")
    if identity_email.returncode != 0 or not identity_email.stdout.strip():
        blockers.append("Git user.email is not configured")
    tracked_secrets = _git(root, "ls-files", "--", ".env", ".env.*")
    if tracked_secrets.returncode != 0:
        blockers.append("tracked-secret check could not run")
    elif tracked_secrets.stdout.splitlines():
        blockers.append("a prohibited .env secret file is tracked")
    status = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    if status.returncode != 0:
        blockers.append("worktree status could not be read")

    return ("blocked", blockers) if blockers else ("passed", [])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--operation", choices=("commit", "push", "release"), default="commit"
    )
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    status, blockers = preflight(root, operation=arguments.operation)
    if status == "passed":
        print("GIT PREFLIGHT: PASSED")
        if arguments.operation == "commit":
            print("REMOTE/UPSTREAM: NOT RUN (local commit only)")
        return 0
    print("GIT PREFLIGHT: BLOCKED")
    for blocker in blockers:
        print(f"- {blocker}")
    return 3


if __name__ == "__main__":
    sys.exit(main())

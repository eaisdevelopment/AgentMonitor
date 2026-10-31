"""Read-only, fail-closed Git preflight for the real AgentMonitor checkout."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Literal

Operation = Literal["commit", "push", "release"]
M5_DETACHED_SELECTOR = "AGENTMONITOR_M5_DETACHED_GIT_PREFLIGHT"
_REVISION = re.compile(r"[0-9a-f]{40}\Z")


def _git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )


def preflight(
    root: Path,
    *,
    operation: Operation = "commit",
    m5_detached: bool = False,
) -> tuple[str, list[str]]:
    """Check the real Git boundary required by the selected operation."""
    blockers: list[str] = []
    worktree = _git(root, "rev-parse", "--is-inside-work-tree")
    if worktree.returncode != 0 or worktree.stdout.strip() != "true":
        return "blocked", ["checkout is not a Git worktree"]

    top_level = _git(root, "rev-parse", "--show-toplevel")
    if top_level.returncode != 0 or Path(top_level.stdout.strip()).resolve() != root:
        blockers.append("checkout root does not match the Git top-level directory")
    head_before = (
        _git(root, "rev-parse", "--verify", "HEAD^{commit}")
        if m5_detached
        else None
    )
    branch = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    status = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    if m5_detached:
        if operation != "commit":
            blockers.append("M5 detached preflight is limited to commit")
        if branch.returncode != 1 or branch.stdout or branch.stderr:
            blockers.append("M5 detached preflight requires detached HEAD")
        if status.returncode != 0 or status.stderr or status.stdout:
            blockers.append("M5 detached preflight requires a clean checkout")
    elif branch.returncode != 0:
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
    if status.returncode != 0:
        blockers.append("worktree status could not be read")
    if m5_detached:
        head_after = _git(root, "rev-parse", "--verify", "HEAD^{commit}")
        revision = "" if head_before is None else head_before.stdout.strip()
        if (
            head_before is None
            or head_before.returncode != 0
            or head_after.returncode != 0
            or head_before.stderr
            or head_after.stderr
            or _REVISION.fullmatch(revision) is None
            or head_after.stdout.strip() != revision
        ):
            blockers.append("M5 detached preflight requires one stable commit")

    return ("blocked", blockers) if blockers else ("passed", [])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--operation", choices=("commit", "push", "release"), default="commit"
    )
    arguments = parser.parse_args()
    selector = os.environ.get(M5_DETACHED_SELECTOR)
    if selector not in {None, "", "1"}:
        print("GIT PREFLIGHT: BLOCKED")
        print("- M5 detached preflight selector is invalid")
        return 3
    root = Path(__file__).resolve().parents[2]
    m5_detached = selector == "1"
    status, blockers = preflight(
        root,
        operation=arguments.operation,
        m5_detached=m5_detached,
    )
    if status == "passed":
        print("GIT PREFLIGHT: PASSED")
        if m5_detached:
            print("M5 DETACHED REVISION: PASSED")
        if arguments.operation == "commit":
            print("REMOTE/UPSTREAM: NOT RUN (local commit only)")
        return 0
    print("GIT PREFLIGHT: BLOCKED")
    for blocker in blockers:
        print(f"- {blocker}")
    return 3


if __name__ == "__main__":
    sys.exit(main())

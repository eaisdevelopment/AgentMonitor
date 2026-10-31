"""M5-CDX-GATE-007: real Git startup revision and cleanliness evidence."""

from __future__ import annotations

import importlib
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import cast

GIT = Path("/usr/bin/git")
GIT_ENV = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_NO_REPLACE_OBJECTS": "1",
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_TERMINAL_PROMPT": "0",
    "HOME": "/nonexistent",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/bin:/bin",
    "XDG_CONFIG_HOME": "/nonexistent",
}


def _git(root: Path, *arguments: str, capture: bool = False) -> str:
    result = subprocess.run(
        [str(GIT), "-c", "core.fsmonitor=false", *arguments],
        cwd=root,
        env=GIT_ENV,
        check=False,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0
    return result.stdout.strip() if capture else ""


def _reader() -> Callable[[Path], str | None]:
    module = importlib.import_module("agentmonitor.composition.bootstrap")
    reader = getattr(module, "read_clean_source_revision_v1", None)
    assert callable(reader), "clean source-revision reader is absent"
    return cast(Callable[[Path], str | None], reader)


def test_real_git_revision_is_available_only_for_clean_tracked_and_untracked_state(
    tmp_path: Path,
) -> None:
    """A dirty tracked or untracked file cannot be labeled by clean HEAD."""

    assert GIT.is_file() and not GIT.is_symlink()
    _git(tmp_path, "init", "--quiet")
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("clean\n")
    _git(tmp_path, "add", "--", tracked.name)
    _git(
        tmp_path,
        "-c",
        "user.name=AgentMonitor test",
        "-c",
        "user.email=agentmonitor@example.invalid",
        "commit",
        "--quiet",
        "-m",
        "clean revision",
    )
    expected = _git(tmp_path, "rev-parse", "--verify", "HEAD", capture=True)
    reader = _reader()
    assert reader(tmp_path) == expected

    tracked.write_text("dirty tracked\n")
    assert reader(tmp_path) is None
    _git(tmp_path, "add", "--", tracked.name)
    assert reader(tmp_path) is None

    tracked.write_text("clean\n")
    _git(tmp_path, "add", "--", tracked.name)
    assert reader(tmp_path) == expected
    untracked = tmp_path / "untracked.txt"
    untracked.write_text("untracked\n")
    assert reader(tmp_path) is None


def test_non_repository_has_no_source_revision(tmp_path: Path) -> None:
    assert _reader()(tmp_path) is None

"""M5-CDX-GATE-007: real Git startup revision and cleanliness evidence."""

from __future__ import annotations

import importlib
import os
import stat
import subprocess
import time
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


def _git_exit(root: Path, *arguments: str) -> int:
    return subprocess.run(
        [str(GIT), "-c", "core.fsmonitor=false", *arguments],
        cwd=root,
        env=GIT_ENV,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=5,
    ).returncode


def _seal_checkout(root: Path) -> None:
    """Apply the real retained-release permission policy to an isolated clone."""
    for directory, _, files in os.walk(root, topdown=False, followlinks=False):
        for name in files:
            path = Path(directory) / name
            info = path.lstat()
            assert stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode)
            path.chmod(stat.S_IMODE(info.st_mode) & ~0o222)
        Path(directory).chmod(0o500)


def _make_cleanup_writable(root: Path) -> None:
    for directory, _, files in os.walk(root, topdown=True, followlinks=False):
        Path(directory).chmod(0o700)
        for name in files:
            (Path(directory) / name).chmod(0o600)


def _stable_file_identity(path: Path) -> tuple[int, ...]:
    value = path.lstat()
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


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


def test_real_sealed_tracked_checkout_reports_clean_revision_without_index_write(
    tmp_path: Path,
) -> None:
    """Permission sealing must not turn unchanged tracked bytes into dirty state."""

    source = Path(__file__).resolve().parents[4]
    release = tmp_path / "release"
    clone = subprocess.run(
        [str(GIT), "clone", "--quiet", "--no-hardlinks", str(source), str(release)],
        env=GIT_ENV,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
    )
    assert clone.returncode == 0
    expected = _git(release, "rev-parse", "--verify", "HEAD", capture=True)

    # The retained build naturally takes longer between checkout and sealing;
    # preserve that distinct ctime interval rather than fabricating index bytes.
    time.sleep(1.1)
    _seal_checkout(release)
    index = release / ".git/index"
    before = _stable_file_identity(index)
    try:
        assert (
            _git_exit(
                release,
                "diff-index",
                "--quiet",
                "--ignore-submodules=none",
                "HEAD",
                "--",
            )
            == 1
        )
        assert (
            _git_exit(
                release,
                "diff",
                "--no-ext-diff",
                "--no-textconv",
                "--quiet",
                "--ignore-submodules=none",
                "HEAD",
                "--",
            )
            == 0
        )
        assert _reader()(release) == expected
        assert _stable_file_identity(index) == before
    finally:
        _make_cleanup_writable(release)

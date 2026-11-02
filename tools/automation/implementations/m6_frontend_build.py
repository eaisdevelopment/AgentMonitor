"""Fresh, offline frontend build bound to a clean candidate checkout."""

from __future__ import annotations

import os
import secrets
import stat
import subprocess
from pathlib import Path

from tools.automation.implementations.auto_m6_local_activate import tree_digest
from tools.automation.implementations.m6_offline_restore import _exchange, _fsync_dir


class FrontendBuildError(RuntimeError):
    """A closed build/preparation failure."""


def _private_dir(path: Path) -> None:
    info = path.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o700
    ):
        raise FrontendBuildError("frontend_build_directory_unsafe")


def _clean_revision(root: Path) -> str:
    status = subprocess.run(
        ["/usr/bin/git", "status", "--porcelain"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    revision = subprocess.run(
        ["/usr/bin/git", "rev-parse", "--verify", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    value = revision.stdout.strip()
    if (
        status.returncode
        or status.stdout
        or revision.returncode
        or len(value) != 40
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise FrontendBuildError("frontend_source_not_clean")
    return value


def _sync_build(root: Path) -> None:
    """Persist real build files and directories before publishing the output."""
    for directory, children, files in os.walk(root, topdown=False, followlinks=False):
        parent = Path(directory)
        if parent.is_symlink() or any(
            (parent / name).is_symlink() for name in children
        ):
            raise FrontendBuildError("frontend_output_unsafe")
        for name in files:
            path = parent / name
            fd = os.open(
                path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
            )
            try:
                if not stat.S_ISREG(os.fstat(fd).st_mode):
                    raise FrontendBuildError("frontend_output_unsafe")
                os.fsync(fd)
            finally:
                os.close(fd)
        _fsync_dir(parent)


def build_clean_frontend(
    candidate: Path, data_root: Path, tool_modules: Path
) -> tuple[str, str]:
    """Build current tracked sources offline, retain prior output, and pin bytes.

    The build is installed only into the inactive candidate checkout. The prior
    generated directory is retained under the private build root after an
    atomic exchange. No provider or dashboard process is contacted.
    """
    revision = _clean_revision(candidate)
    frontend = candidate / "frontend"
    modules = frontend / "node_modules"
    if (
        modules.exists()
        or modules.is_symlink()
        or not tool_modules.is_dir()
        or tool_modules.is_symlink()
    ):
        raise FrontendBuildError("frontend_tooling_unavailable")
    _private_dir(data_root)
    build_root = data_root / ".m6-frontend-builds"
    build_root.mkdir(mode=0o700, exist_ok=True)
    _private_dir(build_root)
    _fsync_dir(data_root)
    work = build_root / ("build-" + secrets.token_hex(16))
    work.mkdir(mode=0o700)
    _fsync_dir(build_root)
    output = work / "dist"
    os.symlink(tool_modules, modules, target_is_directory=True)
    link = modules.lstat()
    try:
        env = {
            "PATH": "/usr/bin:/bin",
            "HOME": str(Path.home()),
            "LANG": "C",
            "NPM_CONFIG_USERCONFIG": "/dev/null",
        }
        result = subprocess.run(
            [
                "/usr/bin/npm",
                "run",
                "build",
                "--",
                "--outDir",
                str(output),
                "--emptyOutDir",
            ],
            cwd=frontend,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=180,
            check=False,
        )
        if (
            result.returncode
            or output.is_symlink()
            or not (output / "dashboard.html").is_file()
        ):
            raise FrontendBuildError("frontend_build_failed")
        build_digest = tree_digest(output)
        _sync_build(output)
        if tree_digest(output) != build_digest:
            raise FrontendBuildError("frontend_output_changed")
    finally:
        current = modules.lstat()
        if (
            (current.st_dev, current.st_ino) != (link.st_dev, link.st_ino)
            or not modules.is_symlink()
            or modules.resolve() != tool_modules.resolve()
        ):
            raise FrontendBuildError("frontend_tool_link_changed")
        modules.unlink()
    if _clean_revision(candidate) != revision:
        raise FrontendBuildError("frontend_source_changed")
    installed = frontend / "dist"
    if installed.is_symlink() or (installed.exists() and not installed.is_dir()):
        raise FrontendBuildError("frontend_output_unsafe")
    if installed.exists():
        _exchange(installed, output)
    else:
        os.rename(output, installed)
    _fsync_dir(frontend)
    _fsync_dir(work)
    if _clean_revision(candidate) != revision or tree_digest(installed) != build_digest:
        raise FrontendBuildError("frontend_output_changed")
    return revision, build_digest

"""Retain a private, revision-bound candidate independently of its source checkout."""

from __future__ import annotations

import ctypes
import os
import re
import secrets
import stat
import subprocess
from pathlib import Path

from tools.automation.implementations.auto_m6_local_activate import tree_digest
from tools.automation.implementations.m6_frontend_build import (
    _clean_revision,
    build_clean_frontend,
)


class CandidateReleaseError(RuntimeError):
    """Candidate could not be retained or verified."""


def _seal(root: Path) -> None:
    for directory, dirs, files in os.walk(root, topdown=False, followlinks=False):
        for name in files:
            path = Path(directory) / name
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise CandidateReleaseError("candidate_release_unsafe")
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
                raise CandidateReleaseError("candidate_release_unsafe")
            path.chmod(stat.S_IMODE(info.st_mode) & ~0o222)
        for name in dirs:
            path = Path(directory) / name
            if path.is_symlink():
                raise CandidateReleaseError("candidate_release_unsafe")
        Path(directory).chmod(0o500)


def _sync_release(root: Path) -> None:
    for directory, _, files in os.walk(root, topdown=False, followlinks=False):
        for name in files:
            path = Path(directory) / name
            if path.is_symlink():
                continue
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        fd = os.open(
            directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        )
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def verify_candidate_release(
    release: Path, releases: Path, revision: str, digest: str
) -> bool:
    if (
        re.fullmatch(r"[a-f0-9]{40}", revision) is None
        or re.fullmatch(r"[a-f0-9]{64}", digest) is None
        or release != releases / ("m6-candidate-" + revision + "-" + digest)
    ):
        raise CandidateReleaseError("candidate_release_identity_invalid")
    parent = releases.lstat()
    if (
        not stat.S_ISDIR(parent.st_mode)
        or parent.st_uid != os.getuid()
        or stat.S_IMODE(parent.st_mode) != 0o700
        or release.is_symlink()
    ):
        raise CandidateReleaseError("candidate_release_unsafe")
    for directory, dirs, files in os.walk(release, followlinks=False):
        for path in [Path(directory), *(Path(directory) / name for name in files)]:
            info = path.lstat()
            if (
                info.st_uid != os.getuid()
                or stat.S_ISLNK(info.st_mode)
                or info.st_mode & 0o222
            ):
                raise CandidateReleaseError("candidate_release_not_sealed")
        if any((Path(directory) / name).is_symlink() for name in dirs):
            raise CandidateReleaseError("candidate_release_unsafe")
    if (
        _clean_revision(release) != revision
        or tree_digest(release / "frontend/dist") != digest
    ):
        raise CandidateReleaseError("candidate_release_changed")
    ignored = subprocess.run(
        ["/usr/bin/git", "status", "--porcelain", "--ignored"],
        cwd=release,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(Path.home()),
            "LANG": "C",
            "GIT_OPTIONAL_LOCKS": "0",
        },
    )
    if ignored.returncode or set(ignored.stdout.splitlines()) != {"!! frontend/dist/"}:
        raise CandidateReleaseError("candidate_release_unexpected_files")
    return True


def prepare_candidate_release(
    source: Path, releases: Path, data: Path, modules: Path
) -> tuple[Path, str, str]:
    revision = _clean_revision(source)
    releases.mkdir(mode=0o700, exist_ok=True)
    info = releases.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o700
    ):
        raise CandidateReleaseError("candidate_release_unsafe")
    prefix = "m6-candidate-" + revision + "-"
    existing = [entry for entry in releases.iterdir() if entry.name.startswith(prefix)]
    if len(existing) > 1:
        raise CandidateReleaseError("candidate_release_ambiguous")
    if existing:
        release = existing[0]
        digest = release.name[len(prefix) :]
        verify_candidate_release(release, releases, revision, digest)
        if _clean_revision(source) != revision:
            raise CandidateReleaseError("candidate_release_source_changed")
        return release, revision, digest
    staging = releases / (".m6-candidate-stage-" + secrets.token_hex(16))
    result = subprocess.run(
        [
            "/usr/bin/git",
            "clone",
            "--quiet",
            "--no-hardlinks",
            str(source),
            str(staging),
        ],
        capture_output=True,
        timeout=120,
        check=False,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(Path.home()),
            "LANG": "C",
            "GIT_OPTIONAL_LOCKS": "0",
        },
    )
    if (
        result.returncode
        or _clean_revision(staging) != revision
        or _clean_revision(source) != revision
    ):
        raise CandidateReleaseError("candidate_release_clone_failed")
    built_revision, digest = build_clean_frontend(staging, data, modules)
    if built_revision != revision or _clean_revision(source) != revision:
        raise CandidateReleaseError("candidate_release_source_changed")
    release = releases / (prefix + digest)
    _seal(staging)
    _sync_release(staging)
    directory_fd = os.open(
        releases, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        result = libc.renameat2(
            directory_fd,
            os.fsencode(staging.name),
            directory_fd,
            os.fsencode(release.name),
            1,
        )
        if result != 0:
            raise CandidateReleaseError("candidate_release_publish_failed")
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    verify_candidate_release(release, releases, revision, digest)
    return release, revision, digest

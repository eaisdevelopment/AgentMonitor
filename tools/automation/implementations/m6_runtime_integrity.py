"""Bounded stdlib-only private runtime integrity verification."""

import hashlib
import os
import stat
import time
from pathlib import Path


def _runtime_digest(root: Path) -> str:
    """Hash a bounded private runtime through pinned, no-follow descriptors."""
    digest = hashlib.sha256()
    deadline = time.monotonic() + 30
    count = 0
    total = 0
    allowed_links = {
        "bin/python": "/usr/bin/python3",
        "bin/python3": "python",
        "bin/python3.12": "python",
        "lib64": "lib",
    }
    directory = os.open(
        root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    try:
        root_info = os.fstat(directory)
        path_info = root.lstat()
        if (
            root_info.st_uid != os.getuid()
            or stat.S_IMODE(root_info.st_mode) != 0o700
            or (root_info.st_dev, root_info.st_ino)
            != (path_info.st_dev, path_info.st_ino)
        ):
            raise RuntimeError("runtime_changed")

        def walk(fd: int, prefix: str) -> None:
            nonlocal count, total
            initial = os.fstat(fd)
            if initial.st_uid != os.getuid() or stat.S_IMODE(initial.st_mode) != 0o700:
                raise RuntimeError("runtime_changed")
            names = sorted(os.listdir(fd))
            for name in names:
                count += 1
                if count > 100000 or time.monotonic() > deadline:
                    raise RuntimeError("runtime_too_large")
                relative = prefix + name
                item = os.stat(name, dir_fd=fd, follow_symlinks=False)
                if item.st_uid != os.getuid():
                    raise RuntimeError("runtime_changed")
                if stat.S_ISLNK(item.st_mode):
                    if relative not in allowed_links:
                        raise RuntimeError("runtime_symlink_invalid")
                    target = os.readlink(name, dir_fd=fd)
                    if target != allowed_links[relative]:
                        raise RuntimeError("runtime_symlink_invalid")
                    digest.update(
                        b"L" + relative.encode() + b"\0" + target.encode() + b"\0"
                    )
                elif stat.S_ISDIR(item.st_mode):
                    digest.update(b"D" + relative.encode() + b"\0")
                    child = os.open(
                        name,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                        dir_fd=fd,
                    )
                    try:
                        pinned = os.fstat(child)
                        if (pinned.st_dev, pinned.st_ino) != (item.st_dev, item.st_ino):
                            raise RuntimeError("runtime_changed")
                        walk(child, relative + "/")
                    finally:
                        os.close(child)
                elif stat.S_ISREG(item.st_mode):
                    if item.st_nlink != 1 or stat.S_IMODE(item.st_mode) not in {
                        0o600,
                        0o700,
                    }:
                        raise RuntimeError("runtime_changed")
                    total += item.st_size
                    if total > 1_073_741_824:
                        raise RuntimeError("runtime_too_large")
                    child = os.open(
                        name,
                        os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                        dir_fd=fd,
                    )
                    try:
                        pinned = os.fstat(child)
                        identity = (
                            item.st_dev,
                            item.st_ino,
                            item.st_mode,
                            item.st_size,
                            item.st_mtime_ns,
                            item.st_ctime_ns,
                        )
                        if (
                            pinned.st_dev,
                            pinned.st_ino,
                            pinned.st_mode,
                            pinned.st_size,
                            pinned.st_mtime_ns,
                            pinned.st_ctime_ns,
                        ) != identity:
                            raise RuntimeError("runtime_changed")
                        digest.update(
                            b"F"
                            + relative.encode()
                            + b"\0"
                            + str(stat.S_IMODE(item.st_mode)).encode()
                            + b"\0"
                        )
                        while block := os.read(child, 1024 * 1024):
                            digest.update(block)
                            if time.monotonic() > deadline:
                                raise RuntimeError("runtime_too_large")
                        final = os.fstat(child)
                        if (
                            final.st_dev,
                            final.st_ino,
                            final.st_mode,
                            final.st_size,
                            final.st_mtime_ns,
                            final.st_ctime_ns,
                        ) != identity:
                            raise RuntimeError("runtime_changed")
                    finally:
                        os.close(child)
                else:
                    raise RuntimeError("runtime_entry_invalid")
            final_dir = os.fstat(fd)
            if (
                initial.st_dev,
                initial.st_ino,
                initial.st_mtime_ns,
                initial.st_ctime_ns,
            ) != (
                final_dir.st_dev,
                final_dir.st_ino,
                final_dir.st_mtime_ns,
                final_dir.st_ctime_ns,
            ):
                raise RuntimeError("runtime_changed")

        walk(directory, "")
        return digest.hexdigest()
    finally:
        os.close(directory)


def _trusted_checkout_revision(root: Path) -> str:
    """Pin one clean operator checkout under the project's trusted-host model."""
    import re
    import subprocess

    env = {"PATH": "/usr/bin:/bin", "LANG": "C", "HOME": str(Path.home())}
    status = subprocess.run(
        ["/usr/bin/git", "status", "--porcelain"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    revision = subprocess.run(
        ["/usr/bin/git", "rev-parse", "--verify", "HEAD"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    lines = status.stdout.splitlines()
    allowed = {"?? backend/.venv", "?? frontend/node_modules"}
    if (
        status.returncode
        or revision.returncode
        or any(line not in allowed for line in lines)
        or any(not (root / line[3:]).is_symlink() for line in lines)
        or re.fullmatch(r"[a-f0-9]{40}", revision.stdout.strip()) is None
    ):
        raise RuntimeError("operator_checkout_not_clean")
    return revision.stdout.strip()

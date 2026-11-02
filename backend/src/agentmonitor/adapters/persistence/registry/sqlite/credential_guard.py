"""M02-owned non-secret guard for credential creation and file cleanup."""

import fcntl
import os
import stat
from pathlib import Path


def acquire_credential_staging_guard(staging_root: Path) -> tuple[int, int]:
    root = os.open(staging_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    lock = None
    try:
        metadata = os.fstat(root)
        current = os.stat(staging_root, follow_symlinks=False)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != 0o700
            or (metadata.st_dev, metadata.st_ino) != (current.st_dev, current.st_ino)
        ):
            raise ValueError("ollama_env_staging_root_invalid")
        lock = os.open(
            ".ollama-env-staging.lock",
            os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
            0o600,
            dir_fd=root,
        )
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        held = os.fstat(lock)
        entry = os.stat(".ollama-env-staging.lock", dir_fd=root, follow_symlinks=False)
        if (
            not stat.S_ISREG(held.st_mode)
            or held.st_uid != os.getuid()
            or stat.S_IMODE(held.st_mode) != 0o600
            or held.st_nlink != 1
            or not stat.S_ISREG(entry.st_mode)
            or entry.st_uid != os.getuid()
            or stat.S_IMODE(entry.st_mode) != 0o600
            or entry.st_nlink != 1
            or (held.st_dev, held.st_ino) != (entry.st_dev, entry.st_ino)
        ):
            raise ValueError("ollama_env_staging_lock_invalid")
        os.fsync(root)
        validate_credential_staging_guard(staging_root, root, lock)
        return root, lock
    except BaseException:
        if lock is not None:
            os.close(lock)
        os.close(root)
        raise


def validate_credential_staging_guard(staging_root: Path, root: int, lock: int) -> None:
    """Reject a replaced root or lock before a protected operation."""
    try:
        _validate_credential_staging_guard(staging_root, root, lock)
    except OSError:
        raise ValueError("ollama_env_staging_lock_invalid") from None


def _validate_credential_staging_guard(
    staging_root: Path, root: int, lock: int
) -> None:
    pinned = os.fstat(root)
    current = os.stat(staging_root, follow_symlinks=False)
    held = os.fstat(lock)
    entry = os.stat(".ollama-env-staging.lock", dir_fd=root, follow_symlinks=False)
    if (
        not stat.S_ISDIR(current.st_mode)
        or current.st_uid != os.getuid()
        or stat.S_IMODE(current.st_mode) != 0o700
        or (pinned.st_dev, pinned.st_ino) != (current.st_dev, current.st_ino)
        or not stat.S_ISREG(held.st_mode)
        or held.st_uid != os.getuid()
        or held.st_nlink != 1
        or stat.S_IMODE(held.st_mode) != 0o600
        or not stat.S_ISREG(entry.st_mode)
        or entry.st_uid != os.getuid()
        or entry.st_nlink != 1
        or stat.S_IMODE(entry.st_mode) != 0o600
        or (held.st_dev, held.st_ino) != (entry.st_dev, entry.st_ino)
    ):
        raise ValueError("ollama_env_staging_lock_invalid")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)

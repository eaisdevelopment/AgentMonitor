"""Private held deployment locks for guarded M6 recovery."""

from __future__ import annotations

import fcntl
import os
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from tools.automation.implementations.m5_service_activation import (
    acquire_m5_service_activation_lock_v1,
    release_m5_service_activation_lock_v1,
    validate_m5_service_activation_lock_v1,
)

_ISSUER = object()


@dataclass(frozen=True, slots=True)
class _State:
    active: bool = True


@dataclass(frozen=True, slots=True)
class _TransitionLease:
    root: Path
    directory: int
    descriptor: int
    root_identity: tuple[int, int]
    lock_identity: tuple[int, int]
    activation: object
    state: _State
    issuer: object

    def validate(self, root: Path) -> None:
        try:
            directory = os.fstat(self.directory)
            path_root = root.lstat()
            held = os.fstat(self.descriptor)
            lock_path = os.stat(
                ".m6-cutover.lock", dir_fd=self.directory, follow_symlinks=False
            )
            if (
                self.issuer is not _ISSUER
                or not self.state.active
                or self.root != root
                or not stat.S_ISDIR(directory.st_mode)
                or directory.st_uid != os.getuid()
                or stat.S_IMODE(directory.st_mode) != 0o700
                or (directory.st_dev, directory.st_ino) != self.root_identity
                or (path_root.st_dev, path_root.st_ino) != self.root_identity
                or not stat.S_ISREG(held.st_mode)
                or held.st_uid != os.getuid()
                or stat.S_IMODE(held.st_mode) != 0o600
                or held.st_nlink != 1
                or (held.st_dev, held.st_ino) != self.lock_identity
                or (lock_path.st_dev, lock_path.st_ino) != self.lock_identity
            ):
                raise OSError
            fcntl.flock(self.descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            validate_m5_service_activation_lock_v1(self.activation)
        except (OSError, ValueError, RuntimeError):
            raise RuntimeError("transition_lock_changed") from None


@contextmanager
def _hold_transition_locks(root: Path) -> Iterator[_TransitionLease]:
    """Hold both permanent cutover flock and fixed service transition guard."""
    directory = os.open(
        root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    try:
        root_info = os.fstat(directory)
        descriptor = os.open(
            ".m6-cutover.lock",
            os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=directory,
        )
        try:
            info = os.fstat(descriptor)
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            activation = acquire_m5_service_activation_lock_v1()
            try:
                lease = _TransitionLease(
                    root,
                    directory,
                    descriptor,
                    (root_info.st_dev, root_info.st_ino),
                    (info.st_dev, info.st_ino),
                    activation,
                    _State(),
                    _ISSUER,
                )
                try:
                    lease.validate(root)
                    yield lease
                    lease.validate(root)
                finally:
                    object.__setattr__(lease.state, "active", False)
            finally:
                release_m5_service_activation_lock_v1(activation)
        finally:
            os.close(descriptor)
    finally:
        os.close(directory)

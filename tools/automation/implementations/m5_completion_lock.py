"""Serialize M5 archive and receipt creation in one kernel namespace."""

from __future__ import annotations

import errno
import fcntl
import hashlib
import os
import socket
import stat
from dataclasses import dataclass
from pathlib import Path

_GUARD_PREFIX = b"\0agentmonitor-m5-completion-v1-"
_FIRST_USE_DIRECTORY_BASENAME = ".agentmonitor-local"
_FIRST_USE_RECEIPT_BASENAME = "m5-current-gate-receipt.json"


class M5CompletionLockErrorV1(ValueError):
    """A sanitized receipt-scope or kernel-exclusion refusal."""


@dataclass(frozen=True, slots=True)
class M5CompletionLockV1:
    """Held checkout-global exclusion bound to one private receipt directory."""

    receipt_path: Path
    directory_descriptor: int
    guard_descriptor: int
    directory_device: int
    directory_inode: int
    guard_address: bytes


def _guard_address_v1(receipt_path: Path) -> bytes:
    material = f"{os.getuid()}:{receipt_path}".encode()
    return _GUARD_PREFIX + hashlib.sha256(material).hexdigest().encode("ascii")


def _validate_receipt_directory_v1(
    receipt_path: Path,
    descriptor: int,
) -> tuple[int, int]:
    try:
        directory = receipt_path.parent
        metadata = os.fstat(descriptor)
        path_metadata = directory.lstat()
        if (
            not receipt_path.is_absolute()
            or receipt_path.name in {"", ".", ".."}
            or directory.resolve(strict=True) != directory
            or not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != 0o700
            or (metadata.st_dev, metadata.st_ino)
            != (path_metadata.st_dev, path_metadata.st_ino)
        ):
            raise OSError
        return metadata.st_dev, metadata.st_ino
    except OSError:
        raise M5CompletionLockErrorV1("m5_completion_lock_invalid") from None


def validate_m5_completion_lock_v1(lock: M5CompletionLockV1) -> None:
    """Prove the held directory and abstract guard still match acquisition."""

    try:
        identity = _validate_receipt_directory_v1(
            lock.receipt_path,
            lock.directory_descriptor,
        )
    except M5CompletionLockErrorV1:
        raise M5CompletionLockErrorV1("m5_completion_lock_changed") from None
    if identity != (lock.directory_device, lock.directory_inode):
        raise M5CompletionLockErrorV1("m5_completion_lock_changed")
    try:
        guard_metadata = os.fstat(lock.guard_descriptor)
        if not stat.S_ISSOCK(guard_metadata.st_mode):
            raise OSError
        with socket.fromfd(
            lock.guard_descriptor,
            socket.AF_UNIX,
            socket.SOCK_STREAM,
        ) as duplicate:
            if duplicate.getsockname() != lock.guard_address:
                raise OSError
    except OSError:
        raise M5CompletionLockErrorV1("m5_completion_lock_changed") from None


def acquire_m5_completion_lock_v1(
    final_receipt_path: Path,
) -> M5CompletionLockV1:
    """Acquire one receipt-scoped Linux guard across every owner data root."""

    directory_descriptor = -1
    guard_descriptor = -1
    guard: socket.socket | None = None
    try:
        if not final_receipt_path.is_absolute() or final_receipt_path.name in {
            "",
            ".",
            "..",
        }:
            raise OSError
        if (
            final_receipt_path.parent.name == _FIRST_USE_DIRECTORY_BASENAME
            and final_receipt_path.name == _FIRST_USE_RECEIPT_BASENAME
        ):
            try:
                os.mkdir(final_receipt_path.parent, mode=0o700)
            except FileExistsError:
                pass
        directory_descriptor = os.open(
            final_receipt_path.parent,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        directory_identity = _validate_receipt_directory_v1(
            final_receipt_path,
            directory_descriptor,
        )
        address = _guard_address_v1(final_receipt_path)
        guard = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        guard.set_inheritable(False)
        try:
            guard.bind(address)
        except OSError as error:
            if error.errno == errno.EADDRINUSE:
                raise M5CompletionLockErrorV1("m5_completion_lock_busy") from None
            raise M5CompletionLockErrorV1("m5_completion_lock_unavailable") from None
        guard_descriptor = guard.detach()
        guard = None
        try:
            fcntl.flock(directory_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            if error.errno in (errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK):
                raise M5CompletionLockErrorV1("m5_completion_lock_busy") from None
            raise M5CompletionLockErrorV1("m5_completion_lock_unavailable") from None
        result = M5CompletionLockV1(
            final_receipt_path,
            directory_descriptor,
            guard_descriptor,
            directory_identity[0],
            directory_identity[1],
            address,
        )
        validate_m5_completion_lock_v1(result)
        directory_descriptor = -1
        guard_descriptor = -1
        return result
    except M5CompletionLockErrorV1:
        raise
    except OSError:
        raise M5CompletionLockErrorV1("m5_completion_lock_invalid") from None
    finally:
        if guard is not None:
            guard.close()
        if guard_descriptor >= 0:
            os.close(guard_descriptor)
        if directory_descriptor >= 0:
            os.close(directory_descriptor)


def release_m5_completion_lock_v1(lock: M5CompletionLockV1) -> None:
    """Release the receipt-scope guard without unlinking filesystem state."""

    try:
        fcntl.flock(lock.directory_descriptor, fcntl.LOCK_UN)
    finally:
        try:
            os.close(lock.guard_descriptor)
        finally:
            os.close(lock.directory_descriptor)

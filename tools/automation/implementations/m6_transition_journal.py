"""Descriptor-relative durable transition journal operations."""

import ctypes
import json
import os
import secrets
import stat
from typing import Any

from tools.automation.implementations.m6_transition_lease import _TransitionLease


class TransitionJournalError(RuntimeError):
    """Fail closed if a transition journal changes unexpectedly."""


def _read_journal_at(
    transition: _TransitionLease,
) -> tuple[dict[str, Any], tuple[int, int]]:
    descriptor = os.open(
        ".m6-cutover-journal.json",
        os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
        dir_fd=transition.directory,
    )
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.getuid()
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_nlink != 1
            or before.st_size > 65536
        ):
            raise TransitionJournalError("migration_recovery_journal_invalid")
        chunks = bytearray()
        while len(chunks) <= 65536:
            part = os.read(descriptor, min(4096, 65537 - len(chunks)))
            if not part:
                break
            chunks.extend(part)
        after = os.fstat(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ) or len(chunks) != before.st_size:
            raise TransitionJournalError("migration_recovery_journal_changed")

        def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise TransitionJournalError("migration_recovery_journal_invalid")
                result[key] = value
            return result

        value = json.loads(chunks, object_pairs_hook=unique)
        if not isinstance(value, dict):
            raise TransitionJournalError("migration_recovery_journal_invalid")
        return value, (before.st_dev, before.st_ino)
    finally:
        os.close(descriptor)


def _replace_journal(
    transition: _TransitionLease,
    before: dict[str, Any],
    after: dict[str, Any],
) -> None:
    """Exchange through the pinned root and retain the displaced journal."""
    after = json.loads(json.dumps(after))
    observed, identity = _read_journal_at(transition)
    if observed != before:
        raise TransitionJournalError("migration_recovery_journal_changed")
    temporary = ".m6-recovery-" + secrets.token_hex(16)
    raw = json.dumps(after, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    if len(raw) > 65536:
        raise TransitionJournalError("migration_recovery_journal_invalid")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o600,
        dir_fd=transition.directory,
    )
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(raw)
            stream.flush()
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    transition.validate(transition.root)
    latest, current_identity = _read_journal_at(transition)
    if latest != before or current_identity != identity:
        raise TransitionJournalError("migration_recovery_journal_changed")
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = libc.renameat2
    renameat2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    renameat2.restype = ctypes.c_int
    if (
        renameat2(
            transition.directory,
            os.fsencode(temporary),
            transition.directory,
            b".m6-cutover-journal.json",
            2,
        )
        != 0
    ):
        raise TransitionJournalError("migration_recovery_exchange_failed")
    os.fsync(transition.directory)
    displaced = os.stat(temporary, dir_fd=transition.directory, follow_symlinks=False)
    actual, _ = _read_journal_at(transition)
    if (displaced.st_dev, displaced.st_ino) != identity or actual != after:
        raise TransitionJournalError("migration_recovery_journal_changed")

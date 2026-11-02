"""Cross-process, non-blocking lock for account credential operations."""

import fcntl
import os
import stat
from collections.abc import Iterator
from contextlib import contextmanager

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.registry.domain.credential_lock import credential_lock_name


@contextmanager
def exclusive_descriptor(descriptor: int) -> Iterator[int]:
    """Hold the kernel lock until the final inherited descriptor is closed."""
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise ValueError("credential_account_busy") from None
    # Never call LOCK_UN: inherited descriptors share the open file description.
    yield descriptor


@contextmanager
def account_credential_lock(
    reference: DatabaseRefV1, account_id: OpaqueIdV1
) -> Iterator[int]:
    """Keep a persistent owner-only inode; never unlink while it may be locked."""
    reference.validate()
    directory = os.open(
        reference._approved_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    )
    descriptor = None
    try:
        descriptor = os.open(
            credential_lock_name(account_id.value),
            os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=directory,
        )
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
        ):
            raise ValueError("credential_lock_unsafe")
        with exclusive_descriptor(descriptor):
            yield descriptor
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(directory)

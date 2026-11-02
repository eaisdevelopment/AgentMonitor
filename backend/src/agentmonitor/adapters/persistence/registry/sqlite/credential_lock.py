"""Cross-process, non-blocking lock for account credential operations."""

import fcntl
import os
import stat
from collections.abc import Iterator
from contextlib import contextmanager

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import AccountCredentialLockLeaseV1
from agentmonitor.modules.registry.domain.credential_lock import credential_lock_name


def _validate_lock_descriptor(
    descriptor: int, *, expected_device: int, expected_inode: int
) -> os.stat_result:
    if (
        type(descriptor) is not int
        or descriptor < 0
        or type(expected_device) is not int
        or expected_device < 0
        or type(expected_inode) is not int
        or expected_inode <= 0
    ):
        raise ValueError("credential_lock_invalid") from None
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_dev != expected_device
            or metadata.st_ino != expected_inode
        ):
            raise ValueError("credential_lock_invalid")
        # An inherited descriptor shares the locked open-file description. This
        # is a validation-only flock; AgentMonitor never explicitly unlocks it.
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise ValueError("credential_lock_invalid") from None
    except OSError:
        raise ValueError("credential_lock_invalid") from None
    return metadata


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
) -> Iterator[AccountCredentialLockLeaseV1]:
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
            root_metadata = os.fstat(directory)

            def validate_lock(
                requested_account_id: OpaqueIdV1,
            ) -> tuple[int, int, int, int, int, int]:
                if requested_account_id != account_id:
                    raise ValueError("credential_lock_invalid") from None
                _validate_lock_descriptor(
                    descriptor,
                    expected_device=metadata.st_dev,
                    expected_inode=metadata.st_ino,
                )
                try:
                    current_directory = os.fstat(directory)
                    current_root = os.stat(
                        reference._approved_root, follow_symlinks=False
                    )
                    current_entry = os.stat(
                        credential_lock_name(account_id.value),
                        dir_fd=directory,
                        follow_symlinks=False,
                    )
                except OSError:
                    raise ValueError("credential_lock_replaced") from None
                if (
                    not stat.S_ISDIR(current_directory.st_mode)
                    or current_directory.st_uid != os.getuid()
                    or stat.S_IMODE(current_directory.st_mode) != 0o700
                    or (current_directory.st_dev, current_directory.st_ino)
                    != (root_metadata.st_dev, root_metadata.st_ino)
                    or (current_root.st_dev, current_root.st_ino)
                    != (root_metadata.st_dev, root_metadata.st_ino)
                    or not stat.S_ISREG(current_entry.st_mode)
                    or current_entry.st_nlink != 1
                    or current_entry.st_uid != os.getuid()
                    or stat.S_IMODE(current_entry.st_mode) != 0o600
                    or (current_entry.st_dev, current_entry.st_ino)
                    != (metadata.st_dev, metadata.st_ino)
                ):
                    raise ValueError("credential_lock_replaced") from None
                return (
                    descriptor,
                    metadata.st_dev,
                    metadata.st_ino,
                    directory,
                    root_metadata.st_dev,
                    root_metadata.st_ino,
                )

            lease = AccountCredentialLockLeaseV1(
                account_id=account_id,
                validator=validate_lock,
            )
            lease.inherited_lock(account_id)
            try:
                yield lease
            finally:
                lease.invalidate()
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(directory)

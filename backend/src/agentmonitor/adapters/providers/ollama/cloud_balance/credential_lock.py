"""Provider-side validation of one inherited M02 credential-lock capability."""

import fcntl
import os
import stat

from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import InheritedAccountCredentialLockV1


def validated_credential_lock_descriptor(
    credential_lock: InheritedAccountCredentialLockV1,
    account_id: OpaqueIdV1,
) -> tuple[int, int]:
    """Validate the inherited lock and pinned directory entry after each hop."""
    if type(credential_lock) is not InheritedAccountCredentialLockV1 or not isinstance(
        account_id, OpaqueIdV1
    ):
        raise ValueError("credential_lock_invalid") from None
    descriptor, device, inode, directory, root_device, root_inode = (
        credential_lock.descriptor_identity(account_id)
    )
    try:
        metadata = os.fstat(descriptor)
        root_metadata = os.fstat(directory)
        entry_metadata = os.stat(
            credential_lock.lock_name(account_id),
            dir_fd=directory,
            follow_symlinks=False,
        )
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        raise ValueError("credential_lock_invalid") from None
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or (metadata.st_dev, metadata.st_ino) != (device, inode)
        or not stat.S_ISDIR(root_metadata.st_mode)
        or root_metadata.st_uid != os.getuid()
        or stat.S_IMODE(root_metadata.st_mode) != 0o700
        or (root_metadata.st_dev, root_metadata.st_ino) != (root_device, root_inode)
        or not stat.S_ISREG(entry_metadata.st_mode)
        or entry_metadata.st_nlink != 1
        or entry_metadata.st_uid != os.getuid()
        or stat.S_IMODE(entry_metadata.st_mode) != 0o600
        or (entry_metadata.st_dev, entry_metadata.st_ino) != (device, inode)
    ):
        raise ValueError("credential_lock_invalid") from None
    return descriptor, directory


def inherited_credential_lock_v1(
    *,
    account_id: OpaqueIdV1,
    descriptor: int,
    device: int,
    inode: int,
    directory_descriptor: int,
    root_device: int,
    root_inode: int,
) -> InheritedAccountCredentialLockV1:
    """Recreate and verify the exact two inherited filesystem descriptors."""
    credential_lock = InheritedAccountCredentialLockV1.from_inherited_identity(
        account_id=account_id,
        descriptor=descriptor,
        device=device,
        inode=inode,
        directory_descriptor=directory_descriptor,
        root_device=root_device,
        root_inode=root_inode,
    )
    validated_credential_lock_descriptor(credential_lock, account_id)
    return credential_lock

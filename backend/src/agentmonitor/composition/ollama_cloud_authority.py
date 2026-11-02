"""Non-secret local owner authorization for Ollama cloud access.

The marker is absent by default. It may be created only after the owner resolves
the key-use restriction and the worker/source review is complete. It contains no
key or other provider data. Every check reads its current non-secret digest.
"""

import os
import stat
from pathlib import Path

from agentmonitor.adapters.providers.ollama.cloud_balance.probe_descriptor import (
    ollama_cloud_probe_fingerprint,
)

_MARKER = ".ollama-cloud-access-authorized-v1"


def valid_authority_marker(
    mode: int, owner: int, expected_owner: int, size: int
) -> bool:
    return (
        stat.S_ISREG(mode)
        and owner == expected_owner
        and mode & 0o077 == 0
        and size == 64
    )


def cloud_access_authorized(data_root: Path | None) -> bool:
    """Fail closed without opening a provider profile or reading a credential."""
    if (
        data_root is None
        or not data_root.is_absolute()
        or data_root in {Path("/"), Path.home()}
    ):
        return False
    root_fd = None
    marker_fd = None
    try:
        root_fd = os.open(
            data_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        )
        root = os.fstat(root_fd)
        if root.st_uid != os.getuid() or stat.S_IMODE(root.st_mode) != 0o700:
            return False
        marker_fd = os.open(
            _MARKER, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=root_fd
        )
        marker = os.fstat(marker_fd)
        content = os.read(marker_fd, 65)
        current = os.stat(_MARKER, dir_fd=root_fd, follow_symlinks=False)
        current_root = os.stat(data_root, follow_symlinks=False)
        return (
            (root.st_dev, root.st_ino) == (current_root.st_dev, current_root.st_ino)
            and stat.S_ISDIR(current_root.st_mode)
            and current_root.st_uid == os.getuid()
            and stat.S_IMODE(current_root.st_mode) == 0o700
            and (marker.st_dev, marker.st_ino) == (current.st_dev, current.st_ino)
            and marker.st_nlink == 1
            and current.st_nlink == 1
            and content == ollama_cloud_probe_fingerprint().encode("ascii")
            and valid_authority_marker(
                marker.st_mode, marker.st_uid, os.getuid(), marker.st_size
            )
            and valid_authority_marker(
                current.st_mode, current.st_uid, os.getuid(), current.st_size
            )
        )
    except OSError:
        return False
    finally:
        if marker_fd is not None:
            os.close(marker_fd)
        if root_fd is not None:
            os.close(root_fd)


def set_cloud_access_authorization(data_root: Path, *, authorized: bool) -> None:
    """Atomically change the non-secret grant after the owner's decision.

    Revocation stops new dispatch; it does not interrupt an in-flight request.
    """
    import secrets

    if not data_root.is_absolute() or data_root in {Path("/"), Path.home()}:
        raise ValueError("ollama_cloud_authority_root_invalid")
    directory = os.open(
        data_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    temporary = ".ollama-cloud-authority-" + secrets.token_hex(16)
    try:
        root = os.fstat(directory)
        current = os.stat(data_root, follow_symlinks=False)
        if (
            root.st_uid != os.getuid()
            or stat.S_IMODE(root.st_mode) != 0o700
            or (root.st_dev, root.st_ino) != (current.st_dev, current.st_ino)
        ):
            raise ValueError("ollama_cloud_authority_root_invalid")
        if not authorized:
            try:
                os.unlink(_MARKER, dir_fd=directory)
            except FileNotFoundError:
                pass
            os.fsync(directory)
            return
        fd = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=directory,
        )
        try:
            data = ollama_cloud_probe_fingerprint().encode("ascii")
            if os.write(fd, data) != len(data):
                raise OSError("ollama_cloud_authority_write_failed")
            os.fsync(fd)
        finally:
            os.close(fd)
        current = os.stat(data_root, follow_symlinks=False)
        if (root.st_dev, root.st_ino) != (current.st_dev, current.st_ino):
            raise ValueError("ollama_cloud_authority_root_invalid")
        os.replace(temporary, _MARKER, src_dir_fd=directory, dst_dir_fd=directory)
        os.fsync(directory)
    finally:
        try:
            os.unlink(temporary, dir_fd=directory)
        except FileNotFoundError:
            pass
        os.close(directory)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Manage the non-secret Ollama cloud access grant"
    )
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("action", choices=("status", "authorize", "revoke"))
    args = parser.parse_args()
    if args.action == "status":
        print(
            "authorized" if cloud_access_authorized(args.data_root) else "unavailable"
        )
        return 0
    set_cloud_access_authorization(
        args.data_root, authorized=args.action == "authorize"
    )
    print("authorized" if args.action == "authorize" else "revoked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

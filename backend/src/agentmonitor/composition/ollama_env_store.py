"""Owner-only atomic updates of binding-scoped entries in the managed .env."""

import fcntl
import os
import secrets
import stat
from pathlib import Path

from agentmonitor.adapters.providers.ollama.cloud_balance.env_format import (
    credential_variable_name,
    edit_credential_entry,
    encode_credential_value,
)

_MAX_ENV_BYTES = 1024 * 1024


def _private_file(info: os.stat_result) -> bool:
    return (
        stat.S_ISREG(info.st_mode)
        and info.st_uid == os.getuid()
        and stat.S_IMODE(info.st_mode) == 0o600
        and info.st_nlink == 1
    )


def update_ollama_env(env_path: Path, binding_id: str, token: bytearray | None) -> None:
    """Set/remove one entry, retaining unrelated bytes and failing closed on races."""
    name = credential_variable_name(binding_id)
    encoded = encode_credential_value(token) if token is not None else None
    if not env_path.is_absolute() or env_path.name != ".env" or ".." in env_path.parts:
        raise ValueError("ollama_env_path_invalid")
    root_fd = os.open(env_path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    lock_fd = None
    temp_name = ".ollama-env-tmp-" + secrets.token_hex(16)
    temp_created = False
    try:
        root = os.fstat(root_fd)
        if root.st_uid != os.getuid() or root.st_mode & stat.S_IWOTH:
            raise ValueError("ollama_env_root_invalid")
        lock_fd = os.open(
            ".ollama-env.lock",
            os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
            0o600,
            dir_fd=root_fd,
        )
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock = os.fstat(lock_fd)
        lock_path = os.stat(".ollama-env.lock", dir_fd=root_fd, follow_symlinks=False)
        if (
            not _private_file(lock)
            or (lock.st_dev, lock.st_ino) != (lock_path.st_dev, lock_path.st_ino)
            or not _private_file(lock_path)
        ):
            raise ValueError("ollama_env_lock_invalid")
        try:
            source_fd = os.open(".env", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=root_fd)
        except FileNotFoundError:
            raise ValueError("ollama_env_file_missing") from None
        old_identity = None
        content = b""
        if source_fd is not None:
            try:
                old = os.fstat(source_fd)
                if not _private_file(old) or old.st_size > _MAX_ENV_BYTES:
                    raise ValueError("ollama_env_file_invalid")
                old_identity = (
                    old.st_dev,
                    old.st_ino,
                    old.st_size,
                    old.st_mtime_ns,
                    old.st_ctime_ns,
                )
                chunks = []
                length = 0
                while chunk := os.read(source_fd, 65536):
                    length += len(chunk)
                    if length > _MAX_ENV_BYTES:
                        raise ValueError("ollama_env_file_invalid")
                    chunks.append(chunk)
                content = b"".join(chunks)
            finally:
                os.close(source_fd)
        updated = edit_credential_entry(content, name, encoded)
        if len(updated) > _MAX_ENV_BYTES:
            raise ValueError("ollama_env_file_invalid")
        if updated == content:
            return
        temp_fd = os.open(
            temp_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=root_fd,
        )
        temp_created = True
        try:
            os.fchmod(temp_fd, 0o600)
            if not _private_file(os.fstat(temp_fd)):
                raise ValueError("ollama_env_file_invalid")
            view = memoryview(updated)
            while view:
                written = os.write(temp_fd, view)
                if written <= 0:
                    raise OSError("ollama_env_write_failed")
                view = view[written:]
            os.fsync(temp_fd)
        finally:
            os.close(temp_fd)
        current_root = os.stat(env_path.parent, follow_symlinks=False)
        current_lock = os.stat(
            ".ollama-env.lock", dir_fd=root_fd, follow_symlinks=False
        )
        if (
            (
                not stat.S_ISDIR(current_root.st_mode)
                or current_root.st_uid != os.getuid()
                or current_root.st_mode & stat.S_IWOTH
                or (root.st_dev, root.st_ino)
                != (current_root.st_dev, current_root.st_ino)
            )
            or (lock.st_dev, lock.st_ino) != (current_lock.st_dev, current_lock.st_ino)
            or not _private_file(current_lock)
        ):
            raise ValueError("ollama_env_lock_invalid")
        try:
            current = os.stat(".env", dir_fd=root_fd, follow_symlinks=False)
        except FileNotFoundError:
            if old_identity is not None:
                raise ValueError("ollama_env_file_changed") from None
        else:
            if not _private_file(current) or old_identity != (
                current.st_dev,
                current.st_ino,
                current.st_size,
                current.st_mtime_ns,
                current.st_ctime_ns,
            ):
                raise ValueError("ollama_env_file_changed")
        os.replace(temp_name, ".env", src_dir_fd=root_fd, dst_dir_fd=root_fd)
        temp_created = False
        os.fsync(root_fd)
    finally:
        if temp_created:
            try:
                os.unlink(temp_name, dir_fd=root_fd)
            except FileNotFoundError:
                pass
        if lock_fd is not None:
            os.close(lock_fd)
        os.close(root_fd)

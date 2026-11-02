"""Owner-only atomic updates of binding-scoped entries in the managed .env."""

import fcntl
import hashlib
import os
import re
import secrets
import stat
from pathlib import Path

from agentmonitor.adapters.providers.ollama.cloud_balance.env_capability import (
    require_safe_env_parent_metadata_v1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.env_format import (
    credential_variable_name,
    edit_credential_entry,
    encode_credential_value,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.env_policy import (
    ENV_AUTHORIZATION_POLICY_V1,
)

_MAX_ENV_BYTES = ENV_AUTHORIZATION_POLICY_V1.maximum_file_bytes
_STAGING_NAME = re.compile(r"\.ollama-env-tmp-[0-9a-f]{32}\Z")


def _private_file(info: os.stat_result) -> bool:
    return (
        stat.S_ISREG(info.st_mode)
        and info.st_uid == os.getuid()
        and stat.S_IMODE(info.st_mode) == 0o600
        and info.st_nlink == 1
    )


def _open_env_parent(env_path: Path) -> int:
    if not env_path.is_absolute() or env_path.name != ".env" or ".." in env_path.parts:
        raise ValueError("ollama_env_path_invalid")
    root_fd = os.open(env_path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in env_path.parent.parts[1:]:
            next_fd = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd
            )
            os.close(root_fd)
            root_fd = next_fd
    except BaseException:
        os.close(root_fd)
        raise
    root = os.fstat(root_fd)
    try:
        require_safe_env_parent_metadata_v1(
            directory=stat.S_ISDIR(root.st_mode),
            owner_uid=root.st_uid,
            current_uid=os.getuid(),
            mode=stat.S_IMODE(root.st_mode),
        )
    except BaseException:
        os.close(root_fd)
        raise
    return root_fd


def _remove_staging(root_fd: int, env_parent_fd: int) -> None:
    names = os.listdir(root_fd)
    if len(names) > 4096:
        raise ValueError("ollama_env_directory_too_large")
    removed = False
    for name in names:
        if _STAGING_NAME.fullmatch(name) is None:
            continue
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
            dir_fd=root_fd,
        )
        try:
            held = os.fstat(descriptor)
            entry = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
            valid = (
                stat.S_ISREG(held.st_mode)
                and held.st_uid == os.getuid()
                and stat.S_IMODE(held.st_mode) == 0o600
                and held.st_nlink in {1, 2}
            )
            if held.st_nlink == 2:
                installed = os.stat(".env", dir_fd=env_parent_fd, follow_symlinks=False)
                valid = valid and (installed.st_dev, installed.st_ino) == (
                    held.st_dev,
                    held.st_ino,
                )
            if not valid or (held.st_dev, held.st_ino) != (entry.st_dev, entry.st_ino):
                raise ValueError("ollama_env_staging_invalid")
            os.unlink(name, dir_fd=root_fd)
            removed = True
        finally:
            os.close(descriptor)
    if removed:
        os.fsync(root_fd)


def _open_staging_root(
    staging_root: Path, env_parent: os.stat_result, env_path: Path, *, create: bool
) -> int | None:
    fd = os.open(staging_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    metadata = os.fstat(fd)
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
        or metadata.st_dev != env_parent.st_dev
    ):
        os.close(fd)
        raise ValueError("ollama_env_staging_root_invalid")
    name = ".ollama-env-staging-" + hashlib.sha256(os.fsencode(env_path)).hexdigest()
    try:
        if create:
            try:
                os.mkdir(name, 0o700, dir_fd=fd)
                os.fsync(fd)
            except FileExistsError:
                pass
        try:
            child = os.open(
                name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd
            )
        except FileNotFoundError:
            return None
        entry = os.stat(name, dir_fd=fd, follow_symlinks=False)
        held = os.fstat(child)
        if (
            not stat.S_ISDIR(entry.st_mode)
            or entry.st_uid != os.getuid()
            or stat.S_IMODE(entry.st_mode) != 0o700
            or (entry.st_dev, entry.st_ino) != (held.st_dev, held.st_ino)
        ):
            os.close(child)
            raise ValueError("ollama_env_staging_root_invalid")
        return child
    finally:
        os.close(fd)


def recover_ollama_env_staging(env_path: Path, staging_root: Path) -> None:
    """Remove only abandoned owner-only staging files under the shared lock."""
    root_fd = _open_env_parent(env_path)
    staging_fd = None
    lock_fd = None
    try:
        try:
            lock_fd = os.open(
                ".ollama-env.lock",
                os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                dir_fd=root_fd,
            )
        except FileNotFoundError:
            return
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        held = os.fstat(lock_fd)
        entry = os.stat(".ollama-env.lock", dir_fd=root_fd, follow_symlinks=False)
        if (
            not _private_file(held)
            or not _private_file(entry)
            or (held.st_dev, held.st_ino) != (entry.st_dev, entry.st_ino)
        ):
            raise ValueError("ollama_env_lock_invalid")
        staging_fd = _open_staging_root(
            staging_root, os.fstat(root_fd), env_path, create=False
        )
        if staging_fd is not None:
            _remove_staging(staging_fd, root_fd)
    finally:
        if staging_fd is not None:
            os.close(staging_fd)
        if lock_fd is not None:
            os.close(lock_fd)
        os.close(root_fd)


def update_ollama_env(
    env_path: Path, binding_id: str, token: bytearray | None, *, staging_root: Path
) -> None:
    """Set/remove one entry, retaining unrelated bytes and failing closed on races."""
    name = credential_variable_name(binding_id)
    encoded = encode_credential_value(token) if token is not None else None
    root_fd = _open_env_parent(env_path)
    staging_fd = None
    lock_fd = None
    temp_fd = None
    temp_name = ".ollama-env-tmp-" + secrets.token_hex(16)
    temp_created = False
    try:
        root = os.fstat(root_fd)
        require_safe_env_parent_metadata_v1(
            directory=stat.S_ISDIR(root.st_mode),
            owner_uid=root.st_uid,
            current_uid=os.getuid(),
            mode=stat.S_IMODE(root.st_mode),
        )
        lock_fd = os.open(
            ".ollama-env.lock",
            os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
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
        os.fsync(root_fd)
        staging_fd = _open_staging_root(staging_root, root, env_path, create=True)
        if staging_fd is None:
            raise ValueError("ollama_env_staging_root_invalid")
        _remove_staging(staging_fd, root_fd)
        try:
            source_fd = os.open(
                ".env",
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                dir_fd=root_fd,
            )
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
            dir_fd=staging_fd,
        )
        temp_created = True
        os.fchmod(temp_fd, 0o600)
        staged = os.fstat(temp_fd)
        if not _private_file(staged):
            raise ValueError("ollama_env_file_invalid")
        view = memoryview(updated)
        while view:
            written = os.write(temp_fd, view)
            if written <= 0:
                raise OSError("ollama_env_write_failed")
            view = view[written:]
        os.fsync(temp_fd)
        current_root = os.stat(env_path.parent, follow_symlinks=False)
        current_lock = os.stat(
            ".ollama-env.lock", dir_fd=root_fd, follow_symlinks=False
        )
        if (
            (
                not stat.S_ISDIR(current_root.st_mode)
                or current_root.st_uid != os.getuid()
                or current_root.st_gid != root.st_gid
                or stat.S_IMODE(current_root.st_mode) != stat.S_IMODE(root.st_mode)
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
        staged_entry = os.stat(temp_name, dir_fd=staging_fd, follow_symlinks=False)
        if not _private_file(staged_entry) or (
            staged_entry.st_dev,
            staged_entry.st_ino,
        ) != (staged.st_dev, staged.st_ino):
            raise ValueError("ollama_env_file_changed")
        os.replace(temp_name, ".env", src_dir_fd=staging_fd, dst_dir_fd=root_fd)
        temp_created = False
        installed = os.stat(".env", dir_fd=root_fd, follow_symlinks=False)
        if not _private_file(installed) or (installed.st_dev, installed.st_ino) != (
            staged.st_dev,
            staged.st_ino,
        ):
            raise ValueError("ollama_env_file_changed")
        os.fsync(root_fd)
        os.fsync(staging_fd)
    finally:
        try:
            if temp_created and temp_fd is not None and staging_fd is not None:
                try:
                    held = os.fstat(temp_fd)
                    entry = os.stat(temp_name, dir_fd=staging_fd, follow_symlinks=False)
                    if _private_file(entry) and (entry.st_dev, entry.st_ino) == (
                        held.st_dev,
                        held.st_ino,
                    ):
                        os.unlink(temp_name, dir_fd=staging_fd)
                        os.fsync(staging_fd)
                except FileNotFoundError:
                    pass
        finally:
            for descriptor in (temp_fd, staging_fd, lock_fd, root_fd):
                if descriptor is not None:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass

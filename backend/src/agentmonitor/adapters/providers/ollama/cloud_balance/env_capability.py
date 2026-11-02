"""Sealed transient capability for the explicitly approved credential .env."""

from __future__ import annotations

import fcntl
import os
import stat
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal, NoReturn, SupportsIndex

from agentmonitor.adapters.providers.ollama.cloud_balance.env_policy import (
    ENV_AUTHORIZATION_POLICY_V1,
)

_ENV_NAME = ENV_AUTHORIZATION_POLICY_V1.file_name
_LOCK_NAME = ENV_AUTHORIZATION_POLICY_V1.global_lock_name
_ISSUER = object()

EnvCredentialFileFailureCode = Literal[
    "ollama_cloud_store_locked",
    "ollama_cloud_store_unavailable",
]
_ParentIdentity = tuple[int, int, int, int, int]
_FileIdentity = tuple[int, int, int, int, int]
_LockIdentity = tuple[int, int]
_DescriptorIdentity = tuple[
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
]


class EnvCredentialFileError(ValueError):
    """Sanitized capability failure with no path or credential detail."""

    def __init__(self, code: EnvCredentialFileFailureCode) -> None:
        self.code = code
        super().__init__(code)


def require_safe_env_parent_metadata_v1(
    *, directory: bool, owner_uid: int, current_uid: int, mode: int
) -> bool:
    """Admit the owner-approved parent policy and report group-write residual."""
    if (
        directory is not True
        or type(owner_uid) is not int
        or type(current_uid) is not int
        or owner_uid != current_uid
        or type(mode) is not int
        or mode not in {0o700, 0o750, 0o755, 0o770, 0o775}
    ):
        raise ValueError("ollama_env_parent_unsafe") from None
    return bool(mode & stat.S_IWGRP)


def require_safe_env_file_metadata_v1(
    *,
    regular: bool,
    owner_uid: int,
    current_uid: int,
    mode: int,
    link_count: int,
    size: int,
) -> None:
    """Require the bounded exact owner-only credential-file policy."""
    if (
        regular is not True
        or type(owner_uid) is not int
        or type(current_uid) is not int
        or owner_uid != current_uid
        or type(mode) is not int
        or mode != ENV_AUTHORIZATION_POLICY_V1.required_file_mode
        or type(link_count) is not int
        or link_count != ENV_AUTHORIZATION_POLICY_V1.required_link_count
        or type(size) is not int
        or not 0 <= size <= ENV_AUTHORIZATION_POLICY_V1.maximum_file_bytes
    ):
        raise ValueError("ollama_env_file_unsafe") from None


def require_safe_env_lock_metadata_v1(
    *, regular: bool, owner_uid: int, current_uid: int, mode: int, link_count: int
) -> None:
    """Require the exact persistent global writer/reader lock policy."""
    if (
        regular is not True
        or type(owner_uid) is not int
        or type(current_uid) is not int
        or owner_uid != current_uid
        or type(mode) is not int
        or mode != 0o600
        or type(link_count) is not int
        or link_count != 1
    ):
        raise ValueError("ollama_env_lock_unsafe") from None


def _parent_identity(metadata: os.stat_result) -> _ParentIdentity:
    require_safe_env_parent_metadata_v1(
        directory=stat.S_ISDIR(metadata.st_mode),
        owner_uid=metadata.st_uid,
        current_uid=os.getuid(),
        mode=stat.S_IMODE(metadata.st_mode),
    )
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_uid,
        metadata.st_gid,
        stat.S_IMODE(metadata.st_mode),
    )


def _file_identity(metadata: os.stat_result) -> _FileIdentity:
    require_safe_env_file_metadata_v1(
        regular=stat.S_ISREG(metadata.st_mode),
        owner_uid=metadata.st_uid,
        current_uid=os.getuid(),
        mode=stat.S_IMODE(metadata.st_mode),
        link_count=metadata.st_nlink,
        size=metadata.st_size,
    )
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _lock_identity(metadata: os.stat_result) -> _LockIdentity:
    require_safe_env_lock_metadata_v1(
        regular=stat.S_ISREG(metadata.st_mode),
        owner_uid=metadata.st_uid,
        current_uid=os.getuid(),
        mode=stat.S_IMODE(metadata.st_mode),
        link_count=metadata.st_nlink,
    )
    return metadata.st_dev, metadata.st_ino


def _require_path(path: Path) -> None:
    if (
        not isinstance(path, Path)
        or not path.is_absolute()
        or path.name != _ENV_NAME
        or ".." in path.parts
        or any(not part or "\x00" in part for part in path.parts[1:])
    ):
        raise ValueError("ollama_env_path_invalid") from None


def _open_parent(path: Path) -> int:
    _require_path(path)
    descriptor = os.open(
        path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    try:
        for part in path.parent.parts[1:]:
            child = os.open(
                part,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _same_entry(parent: int, name: str, identity: tuple[int, int]) -> bool:
    metadata = os.stat(name, dir_fd=parent, follow_symlinks=False)
    return (metadata.st_dev, metadata.st_ino) == identity


class EnvCredentialFileAuthorityV1:
    """Code-issued approved path identity; never serialize, persist, or log."""

    __slots__ = ("_issuer", "_parent_identity", "_path")

    def __init__(
        self, *, path: Path, parent_identity: _ParentIdentity, issuer: object
    ) -> None:
        if issuer is not _ISSUER:
            raise ValueError("ollama_env_authority_invalid") from None
        self._path = path
        self._parent_identity = parent_identity
        self._issuer = issuer

    def __repr__(self) -> str:
        return "<EnvCredentialFileAuthorityV1 approved>"

    __str__ = __repr__

    @property
    def parent_group_writable_residual(self) -> bool:
        """Expose only the owner-approved non-secret parent-risk category."""
        return bool(self._parent_identity[4] & stat.S_IWGRP)

    def __getstate__(self) -> NoReturn:
        raise TypeError("ollama_env_authority_not_serializable")

    def __reduce_ex__(self, protocol: SupportsIndex) -> NoReturn:
        raise TypeError("ollama_env_authority_not_serializable")


def approve_env_credential_file_v1(path: Path) -> EnvCredentialFileAuthorityV1:
    """Bind one explicit deployment-selected path without reading its content."""
    parent: int | None = None
    file_descriptor: int | None = None
    try:
        _require_path(path)
        parent = _open_parent(path)
        parent_identity = _parent_identity(os.fstat(parent))
        file_descriptor = os.open(
            _ENV_NAME,
            os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent,
        )
        file_identity = _file_identity(os.fstat(file_descriptor))
        if not _same_entry(parent, _ENV_NAME, file_identity[:2]):
            raise ValueError("ollama_env_file_replaced")
        return EnvCredentialFileAuthorityV1(
            path=path, parent_identity=parent_identity, issuer=_ISSUER
        )
    except (OSError, ValueError):
        raise EnvCredentialFileError("ollama_cloud_store_unavailable") from None
    finally:
        if file_descriptor is not None:
            os.close(file_descriptor)
        if parent is not None:
            os.close(parent)


class _EnvCredentialLeaseStateV1:
    __slots__ = ("active",)

    def __init__(self) -> None:
        self.active = True


class InheritedEnvCredentialFileV1:
    """Exact inherited descriptors for one isolated helper invocation."""

    __slots__ = ("_identity", "_state")

    def __init__(
        self, identity: _DescriptorIdentity, state: _EnvCredentialLeaseStateV1
    ) -> None:
        if type(state) is not _EnvCredentialLeaseStateV1:
            raise ValueError("ollama_env_lease_invalid") from None
        self._identity = identity
        self._state = state

    def descriptor_identity(self) -> _DescriptorIdentity:
        if type(self) is not InheritedEnvCredentialFileV1 or not self._state.active:
            raise ValueError("ollama_env_lease_invalid") from None
        return self._identity

    def subprocess_arguments(self) -> tuple[str, ...]:
        return tuple(str(value) for value in self.descriptor_identity())

    def subprocess_descriptors(self) -> tuple[int, int, int]:
        identity = self.descriptor_identity()
        return identity[0], identity[6], identity[9]

    def __repr__(self) -> str:
        return "<InheritedEnvCredentialFileV1 transient>"

    __str__ = __repr__

    def __getstate__(self) -> NoReturn:
        raise TypeError("ollama_env_lease_not_serializable")

    def __reduce_ex__(self, protocol: SupportsIndex) -> NoReturn:
        raise TypeError("ollama_env_lease_not_serializable")


class EnvCredentialFileLeaseV1:
    """Live approved-file capability held under the persistent global lock."""

    __slots__ = ("_state", "_validator")

    def __init__(
        self,
        validator: Callable[[], _DescriptorIdentity],
        state: _EnvCredentialLeaseStateV1,
    ) -> None:
        self._validator = validator
        self._state = state

    def inherited_file(self) -> InheritedEnvCredentialFileV1:
        if type(self) is not EnvCredentialFileLeaseV1 or not self._state.active:
            raise ValueError("ollama_env_lease_invalid") from None
        return InheritedEnvCredentialFileV1(self._validator(), self._state)

    def invalidate(self) -> None:
        self._state.active = False

    def __repr__(self) -> str:
        return "<EnvCredentialFileLeaseV1 transient>"

    __str__ = __repr__

    def __getstate__(self) -> NoReturn:
        raise TypeError("ollama_env_lease_not_serializable")

    def __reduce_ex__(self, protocol: SupportsIndex) -> NoReturn:
        raise TypeError("ollama_env_lease_not_serializable")


def _validated_descriptors(
    *,
    parent: int,
    parent_identity: tuple[int, int],
    file_descriptor: int,
    file_identity: _FileIdentity,
    lock_descriptor: int,
    lock_identity: _LockIdentity,
) -> _DescriptorIdentity:
    current_parent = _parent_identity(os.fstat(parent))
    current_file = _file_identity(os.fstat(file_descriptor))
    current_lock = _lock_identity(os.fstat(lock_descriptor))
    fcntl.flock(lock_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if (
        current_parent[:2] != parent_identity
        or current_file != file_identity
        or current_lock != lock_identity
        or not _same_entry(parent, _ENV_NAME, file_identity[:2])
        or not _same_entry(parent, _LOCK_NAME, lock_identity)
    ):
        raise ValueError("ollama_env_lease_invalid") from None
    return (
        file_descriptor,
        *file_identity,
        parent,
        parent_identity[0],
        parent_identity[1],
        lock_descriptor,
        lock_identity[0],
        lock_identity[1],
    )


def validated_inherited_env_file_v1(
    credential_file: InheritedEnvCredentialFileV1,
) -> int:
    """Validate all inherited identities and return only the credential-file FD."""
    if type(credential_file) is not InheritedEnvCredentialFileV1:
        raise ValueError("ollama_env_lease_invalid") from None
    identity = credential_file.descriptor_identity()
    try:
        validated = _validated_descriptors(
            file_descriptor=identity[0],
            file_identity=(
                identity[1],
                identity[2],
                identity[3],
                identity[4],
                identity[5],
            ),
            parent=identity[6],
            parent_identity=(identity[7], identity[8]),
            lock_descriptor=identity[9],
            lock_identity=(identity[10], identity[11]),
        )
    except (BlockingIOError, OSError, ValueError):
        raise ValueError("ollama_env_lease_invalid") from None
    return validated[0]


def inherited_env_credential_file_v1(
    *,
    file_descriptor: int,
    file_device: int,
    file_inode: int,
    file_size: int,
    file_mtime_ns: int,
    file_ctime_ns: int,
    parent_descriptor: int,
    parent_device: int,
    parent_inode: int,
    lock_descriptor: int,
    lock_device: int,
    lock_inode: int,
) -> InheritedEnvCredentialFileV1:
    """Recreate the exact inherited identity after exec and validate it."""
    values = (
        file_descriptor,
        file_device,
        file_inode,
        file_size,
        file_mtime_ns,
        file_ctime_ns,
        parent_descriptor,
        parent_device,
        parent_inode,
        lock_descriptor,
        lock_device,
        lock_inode,
    )
    if (
        any(type(value) is not int or value < 0 for value in values)
        or file_descriptor < 3
        or file_inode < 1
        or parent_descriptor < 3
        or parent_inode < 1
        or lock_descriptor < 3
        or lock_inode < 1
    ):
        raise ValueError("ollama_env_lease_invalid") from None
    result = InheritedEnvCredentialFileV1(values, _EnvCredentialLeaseStateV1())
    validated_inherited_env_file_v1(result)
    return result


@contextmanager
def env_credential_file_lease_v1(
    authority: EnvCredentialFileAuthorityV1,
) -> Iterator[EnvCredentialFileLeaseV1]:
    """Pin one current file under the adjacent global lock for a full request."""
    if (
        type(authority) is not EnvCredentialFileAuthorityV1
        or authority._issuer is not _ISSUER
    ):
        raise EnvCredentialFileError("ollama_cloud_store_unavailable") from None
    parent: int | None = None
    lock_descriptor: int | None = None
    file_descriptor: int | None = None
    state = _EnvCredentialLeaseStateV1()
    try:
        try:
            parent = _open_parent(authority._path)
            parent_identity = _parent_identity(os.fstat(parent))
            if parent_identity != authority._parent_identity:
                raise ValueError("ollama_env_parent_replaced")
            lock_descriptor = os.open(
                _LOCK_NAME,
                os.O_RDWR | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=parent,
            )
            lock_identity = _lock_identity(os.fstat(lock_descriptor))
            try:
                fcntl.flock(lock_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise EnvCredentialFileError("ollama_cloud_store_locked") from None
            file_descriptor = os.open(
                _ENV_NAME,
                os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=parent,
            )
            file_identity = _file_identity(os.fstat(file_descriptor))
        except EnvCredentialFileError:
            raise
        except (BlockingIOError, OSError, ValueError):
            raise EnvCredentialFileError("ollama_cloud_store_unavailable") from None
        parent_fd = parent
        lock_fd = lock_descriptor
        file_fd = file_descriptor

        def validate() -> _DescriptorIdentity:
            current_parent: int | None = None
            try:
                current_parent = _open_parent(authority._path)
                if _parent_identity(os.fstat(current_parent)) != parent_identity:
                    raise ValueError("ollama_env_parent_replaced")
            finally:
                if current_parent is not None:
                    os.close(current_parent)
            return _validated_descriptors(
                parent=parent_fd,
                parent_identity=parent_identity[:2],
                file_descriptor=file_fd,
                file_identity=file_identity,
                lock_descriptor=lock_fd,
                lock_identity=lock_identity,
            )

        lease = EnvCredentialFileLeaseV1(validate, state)
        lease.inherited_file()
        try:
            yield lease
        finally:
            lease.invalidate()
    finally:
        state.active = False
        if file_descriptor is not None:
            os.close(file_descriptor)
        if lock_descriptor is not None:
            os.close(lock_descriptor)
        if parent is not None:
            os.close(parent)

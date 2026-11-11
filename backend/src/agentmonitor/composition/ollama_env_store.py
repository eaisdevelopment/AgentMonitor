"""Owner-only atomic updates of binding-scoped entries in the managed .env."""

import fcntl
import hashlib
import os
import re
import secrets
import stat
from collections.abc import Callable
from pathlib import Path

from agentmonitor.adapters.credential_env.format import (
    MANAGED_VARIABLE_PREFIXES,
    CredentialProviderKey,
    credential_variable_name,
    edit_credential_entry,
    encode_credential_value,
    parse_managed_entry_name,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_guard import (
    acquire_credential_staging_guard,
    validate_credential_staging_guard,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.env_capability import (
    require_safe_env_parent_metadata_v1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.env_policy import (
    ENV_AUTHORIZATION_POLICY_V1,
)

_MAX_ENV_BYTES = ENV_AUTHORIZATION_POLICY_V1.maximum_file_bytes
_STAGING_NAME = re.compile(r"\.ollama-env-tmp-[0-9a-f]{32}\Z")
_LOCATION_STAGING_NAME = re.compile(r"\.ollama-env-location-tmp-[0-9a-f]{32}\Z")
_LOCATION_NAME = ".ollama-env-location"
_IMPORT_NAME = re.compile(rb"[A-Z_][A-Z0-9_]{0,127}\Z")
_MANAGED_PREFIXES = MANAGED_VARIABLE_PREFIXES


def _import_name_bytes(variable_name: str) -> bytes:
    try:
        name = variable_name.encode("ascii")
    except (AttributeError, UnicodeError):
        raise ValueError("ollama_env_import_name_invalid") from None
    if (
        type(variable_name) is not str
        or _IMPORT_NAME.fullmatch(name) is None
        or name.startswith(_MANAGED_PREFIXES)
    ):
        raise ValueError("ollama_env_import_name_invalid")
    return name


def validate_ollama_env_import_variable(variable_name: str) -> None:
    """Validate a literal source name without reading the credential file."""
    _import_name_bytes(variable_name)


def read_literal_env_value(content: bytes | bytearray, variable_name: str) -> bytearray:
    """Select one canonical literal value from an already-bounded snapshot."""
    name = _import_name_bytes(variable_name)
    if (
        type(content) not in {bytes, bytearray}
        or len(content) > ENV_AUTHORIZATION_POLICY_V1.maximum_file_bytes
    ):
        raise ValueError("ollama_env_import_stream_invalid")
    selected: bytearray | None = None
    try:
        for line in content.splitlines():
            candidate = line.lstrip()
            if candidate.startswith(b"export "):
                candidate = candidate[7:].lstrip()
            if candidate.split(b"=", 1)[0].strip() != name:
                continue
            if selected is not None:
                raise ValueError("ollama_env_import_entry_ambiguous") from None
            if not line.startswith(name + b"="):
                raise ValueError("ollama_env_import_entry_invalid") from None
            selected = bytearray(line[len(name) + 1 :])
        if selected is None:
            raise ValueError("ollama_env_import_entry_missing") from None
        if (
            len(selected) >= 2
            and selected[0] in {0x22, 0x27}
            and selected[-1] == selected[0]
        ):
            del selected[-1]
            del selected[0]
        elif selected.startswith((b'"', b"'")) or selected.endswith((b'"', b"'")):
            raise ValueError("ollama_env_import_value_invalid") from None
        if not 1 <= len(
            selected
        ) <= ENV_AUTHORIZATION_POLICY_V1.maximum_token_bytes or any(
            item < 0x21 or item > 0x7E for item in selected
        ):
            raise ValueError("ollama_env_import_value_invalid") from None
        result = selected
        selected = None
        return result
    finally:
        if selected is not None:
            selected[:] = b"\0" * len(selected)


def _private_file(info: os.stat_result) -> bool:
    return (
        stat.S_ISREG(info.st_mode)
        and info.st_uid == os.getuid()
        and stat.S_IMODE(info.st_mode) == 0o600
        and info.st_nlink == 1
    )


def _remove_location_staging(root: int, staging_root: Path, lock: int) -> None:
    names = os.listdir(root)
    if len(names) > 4096:
        raise ValueError("ollama_env_directory_too_large")
    removed = False
    for name in names:
        if _LOCATION_STAGING_NAME.fullmatch(name) is None:
            continue
        descriptor = os.open(
            name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root
        )
        try:
            held = os.fstat(descriptor)
            entry = os.stat(name, dir_fd=root, follow_symlinks=False)
            if (
                not _private_file(held)
                or not _private_file(entry)
                or (held.st_dev, held.st_ino) != (entry.st_dev, entry.st_ino)
            ):
                raise ValueError("ollama_env_staging_invalid")
            validate_credential_staging_guard(staging_root, root, lock)
            os.unlink(name, dir_fd=root)
            removed = True
        finally:
            os.close(descriptor)
    if removed:
        os.fsync(root)


def _acquire_staging_guard(staging_root: Path) -> tuple[int, int]:
    root, lock = acquire_credential_staging_guard(staging_root)
    try:
        _remove_location_staging(root, staging_root, lock)
        return root, lock
    except BaseException:
        os.close(lock)
        os.close(root)
        raise


def _location_bytes(env_path: Path) -> bytes:
    value = os.fsencode(env_path)
    if (
        not env_path.is_absolute()
        or env_path.name != ".env"
        or len(value) > 4096
        or b"\n" in value
    ):
        raise ValueError("ollama_env_path_invalid")
    return value


def _location_matches(
    root_fd: int,
    env_path: Path,
    *,
    create: bool,
    validate_publish: Callable[[], None] | None = None,
) -> bool:
    expected = _location_bytes(env_path)
    try:
        descriptor = os.open(
            _LOCATION_NAME, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root_fd
        )
    except FileNotFoundError:
        if not create:
            return False
        if validate_publish is None:
            raise ValueError("ollama_env_staging_lock_invalid") from None
        validate_publish()
        temporary = ".ollama-env-location-tmp-" + secrets.token_hex(16)
        descriptor = os.open(
            temporary,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=root_fd,
        )
        try:
            os.fchmod(descriptor, 0o600)
            if os.write(descriptor, expected) != len(expected):
                raise OSError("ollama_env_location_write_failed")
            os.fsync(descriptor)
            validate_publish()
            held = os.fstat(descriptor)
            entry = os.stat(temporary, dir_fd=root_fd, follow_symlinks=False)
            if (
                not _private_file(held)
                or not _private_file(entry)
                or (held.st_dev, held.st_ino) != (entry.st_dev, entry.st_ino)
            ):
                raise ValueError("ollama_env_location_invalid")
            os.replace(
                temporary, _LOCATION_NAME, src_dir_fd=root_fd, dst_dir_fd=root_fd
            )
            entry = os.stat(_LOCATION_NAME, dir_fd=root_fd, follow_symlinks=False)
            os.lseek(descriptor, 0, os.SEEK_SET)
            if (
                not _private_file(entry)
                or (held.st_dev, held.st_ino) != (entry.st_dev, entry.st_ino)
                or os.read(descriptor, 4097) != expected
            ):
                raise ValueError("ollama_env_location_invalid")
            validate_publish()
            os.fsync(root_fd)
            return True
        finally:
            os.close(descriptor)
    try:
        held = os.fstat(descriptor)
        entry = os.stat(_LOCATION_NAME, dir_fd=root_fd, follow_symlinks=False)
        if (
            not _private_file(held)
            or not _private_file(entry)
            or held.st_size > 4096
            or (held.st_dev, held.st_ino) != (entry.st_dev, entry.st_ino)
        ):
            raise ValueError("ollama_env_location_invalid")
        matches = os.read(descriptor, 4097) == expected
        final = os.stat(_LOCATION_NAME, dir_fd=root_fd, follow_symlinks=False)
        if not _private_file(final) or (held.st_dev, held.st_ino) != (
            final.st_dev,
            final.st_ino,
        ):
            raise ValueError("ollama_env_location_invalid")
        return matches
    finally:
        os.close(descriptor)


def env_location_matches(staging_root: Path, env_path: Path) -> bool:
    """Match configured path to durable non-secret binding-location provenance."""
    root, lock = _acquire_staging_guard(staging_root)
    try:
        result = _location_matches(root, env_path, create=False)
        validate_credential_staging_guard(staging_root, root, lock)
        return result
    finally:
        os.close(lock)
        os.close(root)


def _read_location_at(root: int) -> Path:
    descriptor = None
    try:
        descriptor = os.open(
            _LOCATION_NAME,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=root,
        )
        held = os.fstat(descriptor)
        entry = os.stat(_LOCATION_NAME, dir_fd=root, follow_symlinks=False)
        if (
            not _private_file(held)
            or not _private_file(entry)
            or held.st_size > 4096
            or (held.st_dev, held.st_ino) != (entry.st_dev, entry.st_ino)
        ):
            raise ValueError("ollama_env_location_invalid")
        raw = os.read(descriptor, 4097)
        final = os.stat(_LOCATION_NAME, dir_fd=root, follow_symlinks=False)
        if not _private_file(final) or (held.st_dev, held.st_ino) != (
            final.st_dev,
            final.st_ino,
        ):
            raise ValueError("ollama_env_location_invalid")
        path = Path(os.fsdecode(raw))
        if _location_bytes(path) != raw:
            raise ValueError("ollama_env_location_invalid")
        return path
    finally:
        if descriptor is not None:
            os.close(descriptor)


def read_env_location(staging_root: Path) -> Path:
    """Read the non-secret retained location for offline credential cleanup."""
    root, lock = _acquire_staging_guard(staging_root)
    try:
        result = _read_location_at(root)
        validate_credential_staging_guard(staging_root, root, lock)
        return result
    finally:
        os.close(lock)
        os.close(root)


def _managed_entries(
    env_path: Path,
) -> tuple[tuple[CredentialProviderKey, str], ...]:
    """Scan entry names only; never retain, return or print credential values."""
    root = _open_env_parent(env_path)
    parent_identity = os.fstat(root)
    lock = None
    source = None
    try:
        lock = os.open(
            ".ollama-env.lock",
            os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
            0o600,
            dir_fd=root,
        )
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        held = os.fstat(lock)
        entry = os.stat(".ollama-env.lock", dir_fd=root, follow_symlinks=False)
        if (
            not _private_file(held)
            or not _private_file(entry)
            or (held.st_dev, held.st_ino) != (entry.st_dev, entry.st_ino)
        ):
            raise ValueError("ollama_env_lock_invalid")
        source = os.open(
            ".env", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root
        )
        metadata = os.fstat(source)
        if not _private_file(metadata) or metadata.st_size > _MAX_ENV_BYTES:
            raise ValueError("ollama_env_file_invalid")
        bindings: list[tuple[CredentialProviderKey, str]] = []
        name = bytearray()
        in_value = False
        while byte := os.read(source, 1):
            if byte == b"\n":
                name.clear()
                in_value = False
            elif not in_value and byte == b"=":
                candidate = bytes(name).strip()
                if candidate.startswith(b"export "):
                    candidate = candidate[7:].lstrip()
                try:
                    managed = parse_managed_entry_name(candidate)
                except ValueError:
                    raise ValueError("ollama_env_entry_name_invalid") from None
                if managed is not None:
                    if len(bindings) >= 1000:
                        raise ValueError("ollama_env_entry_name_invalid")
                    bindings.append(managed)
                name.clear()
                in_value = True
            elif not in_value:
                if len(name) >= 256:
                    raise ValueError("ollama_env_entry_name_invalid")
                name.extend(byte)
        entry = os.stat(".env", dir_fd=root, follow_symlinks=False)
        current_parent = os.stat(env_path.parent, follow_symlinks=False)
        if (
            not _private_file(entry)
            or (
                entry.st_dev,
                entry.st_ino,
                entry.st_size,
                entry.st_mtime_ns,
                entry.st_ctime_ns,
            )
            != (
                metadata.st_dev,
                metadata.st_ino,
                metadata.st_size,
                metadata.st_mtime_ns,
                metadata.st_ctime_ns,
            )
            or (
                current_parent.st_dev,
                current_parent.st_ino,
                current_parent.st_uid,
                current_parent.st_gid,
                stat.S_IMODE(current_parent.st_mode),
            )
            != (
                parent_identity.st_dev,
                parent_identity.st_ino,
                parent_identity.st_uid,
                parent_identity.st_gid,
                stat.S_IMODE(parent_identity.st_mode),
            )
        ):
            raise ValueError("ollama_env_file_changed")
        held_lock = os.fstat(lock)
        lock_entry = os.stat(".ollama-env.lock", dir_fd=root, follow_symlinks=False)
        if (
            not _private_file(held_lock)
            or not _private_file(lock_entry)
            or (held_lock.st_dev, held_lock.st_ino)
            != (lock_entry.st_dev, lock_entry.st_ino)
        ):
            raise ValueError("ollama_env_lock_invalid")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if len(set(bindings)) != len(bindings):
            raise ValueError("ollama_env_entry_ambiguous")
        return tuple(bindings)
    finally:
        for descriptor in (source, lock, root):
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass


def _require_no_staging_files(
    staging_root: Path, env_path: Path, root: int, lock: int
) -> None:
    """Retain the location while any staged copy needs separate recovery."""
    validate_credential_staging_guard(staging_root, root, lock)
    name = ".ollama-env-staging-" + hashlib.sha256(os.fsencode(env_path)).hexdigest()
    try:
        child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
    except FileNotFoundError:
        return
    try:
        held = os.fstat(child)
        entry = os.stat(name, dir_fd=root, follow_symlinks=False)
        if (
            not stat.S_ISDIR(held.st_mode)
            or held.st_uid != os.getuid()
            or stat.S_IMODE(held.st_mode) != 0o700
            or (held.st_dev, held.st_ino) != (entry.st_dev, entry.st_ino)
        ):
            raise ValueError("ollama_env_staging_root_invalid")
        if os.listdir(child):
            raise ValueError("ollama_env_staging_recovery_required")
        _validate_staging_child(staging_root, env_path, root, lock, child)
    finally:
        os.close(child)


def release_env_location_if_unused(
    staging_root: Path, env_path: Path, *, has_unfinished_bindings: Callable[[], bool]
) -> None:
    """Permit a later deployment path only after all bindings are cleaned."""
    recover_ollama_env_staging(env_path, staging_root)
    root, lock = _acquire_staging_guard(staging_root)
    try:
        if not _location_matches(root, env_path, create=False):
            return
        if has_unfinished_bindings() or _managed_entries(env_path):
            return
        _require_no_staging_files(staging_root, env_path, root, lock)
        validate_credential_staging_guard(staging_root, root, lock)
        if not _location_matches(root, env_path, create=False):
            raise ValueError("ollama_env_location_mismatch")
        os.unlink(_LOCATION_NAME, dir_fd=root)
        os.fsync(root)
    finally:
        os.close(lock)
        os.close(root)


def recover_env_location_if_unused(
    staging_root: Path, *, has_unfinished_bindings: Callable[[], bool]
) -> None:
    """Clear stale or interrupted location metadata only when no binding remains."""
    root, lock = _acquire_staging_guard(staging_root)
    try:
        if has_unfinished_bindings():
            return
        try:
            entry = os.stat(_LOCATION_NAME, dir_fd=root, follow_symlinks=False)
        except FileNotFoundError:
            return
        if not _private_file(entry):
            raise ValueError("ollama_env_location_invalid")
        retained = _read_location_at(root)
        if _managed_entries(retained):
            return
        _require_no_staging_files(staging_root, retained, root, lock)
        validate_credential_staging_guard(staging_root, root, lock)
        if not _location_matches(root, retained, create=False):
            raise ValueError("ollama_env_location_mismatch")
        os.unlink(_LOCATION_NAME, dir_fd=root)
        os.fsync(root)
    finally:
        os.close(lock)
        os.close(root)


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


def _remove_staging(
    root_fd: int, env_parent_fd: int, *, validate_guard: Callable[[], None]
) -> None:
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
            validate_guard()
            os.unlink(name, dir_fd=root_fd)
            removed = True
        finally:
            os.close(descriptor)
    if removed:
        os.fsync(root_fd)


def _validate_staging_child(
    staging_root: Path, env_path: Path, root: int, lock: int, child: int
) -> None:
    validate_credential_staging_guard(staging_root, root, lock)
    name = ".ollama-env-staging-" + hashlib.sha256(os.fsencode(env_path)).hexdigest()
    held = os.fstat(child)
    entry = os.stat(name, dir_fd=root, follow_symlinks=False)
    if (
        not stat.S_ISDIR(entry.st_mode)
        or entry.st_uid != os.getuid()
        or stat.S_IMODE(entry.st_mode) != 0o700
        or (held.st_dev, held.st_ino) != (entry.st_dev, entry.st_ino)
    ):
        raise ValueError("ollama_env_staging_root_invalid")


def _open_staging_root(
    staging_root: Path,
    env_parent: os.stat_result,
    env_path: Path,
    *,
    guard_root: int,
    create: bool,
) -> int | None:
    fd = os.open(staging_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    metadata = os.fstat(fd)
    pinned = os.fstat(guard_root)
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
        or metadata.st_dev != env_parent.st_dev
        or (metadata.st_dev, metadata.st_ino) != (pinned.st_dev, pinned.st_ino)
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
    guard_root, guard_lock = _acquire_staging_guard(staging_root)
    try:
        if not _location_matches(guard_root, env_path, create=False):
            os.close(guard_lock)
            os.close(guard_root)
            return
        root_fd = _open_env_parent(env_path)
        validate_credential_staging_guard(staging_root, guard_root, guard_lock)
    except BaseException:
        os.close(guard_lock)
        os.close(guard_root)
        raise
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
            staging_root,
            os.fstat(root_fd),
            env_path,
            guard_root=guard_root,
            create=False,
        )
        if staging_fd is not None:
            _remove_staging(
                staging_fd,
                root_fd,
                validate_guard=lambda: _validate_staging_child(
                    staging_root, env_path, guard_root, guard_lock, staging_fd
                ),
            )
    finally:
        if staging_fd is not None:
            os.close(staging_fd)
        if lock_fd is not None:
            os.close(lock_fd)
        os.close(root_fd)
        os.close(guard_lock)
        os.close(guard_root)


def _update_managed_env(
    env_path: Path,
    binding_id: str,
    token: bytearray | None,
    *,
    provider_key: CredentialProviderKey,
    staging_root: Path,
    _held_guard: tuple[int, int] | None = None,
    _import_variable: str | None = None,
) -> None:
    """Set/remove one entry, retaining unrelated bytes and failing closed on races."""
    name = credential_variable_name(binding_id, provider_key=provider_key)
    if token is not None and _import_variable is not None:
        raise ValueError("ollama_env_import_invalid")
    if _import_variable is not None:
        validate_ollama_env_import_variable(_import_variable)
    encoded = encode_credential_value(token) if token is not None else None
    owns_guard = _held_guard is None
    if _held_guard is None:
        guard_root, guard_lock = _acquire_staging_guard(staging_root)
    else:
        guard_root, guard_lock = _held_guard
    try:
        validate_credential_staging_guard(staging_root, guard_root, guard_lock)
        if not _location_matches(
            guard_root,
            env_path,
            create=True,
            validate_publish=lambda: validate_credential_staging_guard(
                staging_root, guard_root, guard_lock
            ),
        ):
            raise ValueError("ollama_env_location_mismatch")
        root_fd = _open_env_parent(env_path)
        validate_credential_staging_guard(staging_root, guard_root, guard_lock)
    except BaseException:
        if owns_guard:
            os.close(guard_lock)
            os.close(guard_root)
        raise
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
        staging_fd = _open_staging_root(
            staging_root, root, env_path, guard_root=guard_root, create=True
        )
        if staging_fd is None:
            raise ValueError("ollama_env_staging_root_invalid")
        _remove_staging(
            staging_fd,
            root_fd,
            validate_guard=lambda: _validate_staging_child(
                staging_root, env_path, guard_root, guard_lock, staging_fd
            ),
        )
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
        if _import_variable is not None:
            imported = read_literal_env_value(content, _import_variable)
            try:
                encoded = encode_credential_value(imported)
            finally:
                imported[:] = b"\0" * len(imported)
        updated = edit_credential_entry(content, name, encoded)
        if len(updated) > _MAX_ENV_BYTES:
            raise ValueError("ollama_env_file_invalid")
        if updated == content:
            return
        _validate_staging_child(
            staging_root, env_path, guard_root, guard_lock, staging_fd
        )
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
            _validate_staging_child(
                staging_root, env_path, guard_root, guard_lock, staging_fd
            )
            written = os.write(temp_fd, view)
            if written <= 0:
                raise OSError("ollama_env_write_failed")
            view = view[written:]
        os.fsync(temp_fd)
        _validate_staging_child(
            staging_root, env_path, guard_root, guard_lock, staging_fd
        )
        current_root = os.stat(env_path.parent, follow_symlinks=False)
        current_staging_root = os.stat(staging_root, follow_symlinks=False)
        pinned_staging_root = os.fstat(guard_root)
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
            or (current_staging_root.st_dev, current_staging_root.st_ino)
            != (pinned_staging_root.st_dev, pinned_staging_root.st_ino)
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
        validate_credential_staging_guard(staging_root, guard_root, guard_lock)
        if not _private_file(staged_entry) or (
            staged_entry.st_dev,
            staged_entry.st_ino,
        ) != (staged.st_dev, staged.st_ino):
            raise ValueError("ollama_env_file_changed")
        validate_credential_staging_guard(staging_root, guard_root, guard_lock)
        _validate_staging_child(
            staging_root, env_path, guard_root, guard_lock, staging_fd
        )
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
                        # Remove the exact inode even if its directory was renamed.
                        os.unlink(temp_name, dir_fd=staging_fd)
                        os.fsync(staging_fd)
                except FileNotFoundError:
                    pass
        finally:
            descriptors: tuple[int | None, ...] = (
                temp_fd,
                staging_fd,
                lock_fd,
                root_fd,
            )
            if owns_guard:
                descriptors += (guard_lock, guard_root)
            for descriptor in descriptors:
                if descriptor is not None:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass


def update_managed_env(
    env_path: Path,
    binding_id: str,
    token: bytearray | None,
    *,
    provider_key: CredentialProviderKey,
    staging_root: Path,
) -> None:
    """Set/remove one provider-namespaced entry using the existing shared locks."""
    _update_managed_env(
        env_path,
        binding_id,
        token,
        provider_key=provider_key,
        staging_root=staging_root,
    )


def import_managed_env_variable(
    env_path: Path,
    binding_id: str,
    variable_name: str,
    *,
    provider_key: CredentialProviderKey,
    staging_root: Path,
) -> None:
    """Copy one literal entry into the selected provider's managed namespace."""
    _update_managed_env(
        env_path,
        binding_id,
        None,
        provider_key=provider_key,
        staging_root=staging_root,
        _import_variable=variable_name,
    )


def update_ollama_env(
    env_path: Path,
    binding_id: str,
    token: bytearray | None,
    *,
    staging_root: Path,
    _held_guard: tuple[int, int] | None = None,
    _import_variable: str | None = None,
) -> None:
    """Compatibility wrapper retaining Ollama names and internal guard callers."""
    try:
        _update_managed_env(
            env_path,
            binding_id,
            token,
            provider_key="ollama",
            staging_root=staging_root,
            _held_guard=_held_guard,
            _import_variable=_import_variable,
        )
    except ValueError as error:
        raise ValueError(str(error).replace("credential_env_", "ollama_env_")) from None


def import_ollama_env_variable(
    env_path: Path,
    binding_id: str,
    variable_name: str,
    *,
    staging_root: Path,
) -> None:
    """Copy one literal source entry into one managed binding entry atomically."""
    update_ollama_env(
        env_path,
        binding_id,
        None,
        staging_root=staging_root,
        _import_variable=variable_name,
    )


def cleanup_untracked_env_entries(
    staging_root: Path, env_path: Path, *, has_unfinished_bindings: Callable[[], bool]
) -> None:
    """Clean reserved orphan entries under the binding-creation/writer guard."""
    recover_ollama_env_staging(env_path, staging_root)
    root, lock = _acquire_staging_guard(staging_root)
    try:
        if has_unfinished_bindings():
            raise ValueError("credential_binding_cleanup_busy")
        if not _location_matches(
            root,
            env_path,
            create=True,
            validate_publish=lambda: validate_credential_staging_guard(
                staging_root, root, lock
            ),
        ):
            raise ValueError("ollama_env_location_mismatch")
        for provider_key, binding_id in _managed_entries(env_path):
            _update_managed_env(
                env_path,
                binding_id,
                None,
                staging_root=staging_root,
                _held_guard=(root, lock),
                provider_key=provider_key,
            )
        if has_unfinished_bindings() or _managed_entries(env_path):
            raise ValueError("credential_binding_cleanup_busy")
        _require_no_staging_files(staging_root, env_path, root, lock)
        validate_credential_staging_guard(staging_root, root, lock)
        if not _location_matches(root, env_path, create=False):
            raise ValueError("ollama_env_location_mismatch")
        os.unlink(_LOCATION_NAME, dir_fd=root)
        os.fsync(root)
    finally:
        os.close(lock)
        os.close(root)

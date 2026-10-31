"""Versioned owner-only settings; no provider telemetry or SQLite mutation."""

import fcntl
import json
import os
import secrets
import stat
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from threading import RLock

from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.runtime_observation_v1 import (
    OwnerProcessAccountAssociationV1,
    ProcessIdentityV1,
)
from agentmonitor.modules.runtime_observation.application.ports import (
    OwnerAssociationErrorV1,
    owner_association_key,
)

SETTINGS_NAME = "owner-process-account-associations-v1.json"
LOCK_NAME = ".owner-process-account-associations-v1.lock"
FORMAT = "owner-process-account-associations.v1"
MAX_BYTES = 1024 * 1024
MAX_RECORDS = 2048


def _unavailable() -> OwnerAssociationErrorV1:
    return OwnerAssociationErrorV1("observation_repository_unavailable")


def _closed_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _unavailable()
        result[key] = value
    return result


def _safe_file(fd: int) -> None:
    info = os.fstat(fd)
    if (
        not stat.S_ISREG(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_uid != os.getuid()
        or info.st_nlink != 1
    ):
        raise _unavailable()


def _decode(value: object) -> OwnerProcessAccountAssociationV1:
    if not isinstance(value, dict) or set(value) != {
        "identity",
        "provider_key",
        "account_id",
        "principal_id",
        "confirmed_at",
        "record_version",
        "executable_identity",
    }:
        raise _unavailable()
    identity = value["identity"]
    if not isinstance(identity, dict) or set(identity) != {
        "platform_source",
        "platform_scope_id",
        "pid",
        "start_time_ticks",
    }:
        raise _unavailable()
    if (
        type(identity["platform_source"]) is not str
        or type(identity["platform_scope_id"]) is not str
        or type(identity["pid"]) is not int
        or type(identity["start_time_ticks"]) is not int
        or type(value["provider_key"]) is not str
        or type(value["principal_id"]) is not str
        or type(value["confirmed_at"]) is not str
        or type(value["record_version"]) is not int
        or type(value["executable_identity"]) is not str
        or (value["account_id"] is not None and type(value["account_id"]) is not str)
    ):
        raise _unavailable()
    return OwnerProcessAccountAssociationV1(
        ProcessIdentityV1(
            identity["platform_source"],
            identity["platform_scope_id"],
            identity["pid"],
            identity["start_time_ticks"],
        ),
        value["provider_key"],
        OpaqueIdV1(value["account_id"]) if value["account_id"] is not None else None,
        OpaqueIdV1(value["principal_id"]),
        datetime.fromisoformat(value["confirmed_at"]),
        value["record_version"],
        value["executable_identity"],
    )


def _encode(record: OwnerProcessAccountAssociationV1) -> dict[str, object]:
    return {
        "identity": {
            "platform_source": record.identity.platform_source,
            "platform_scope_id": record.identity.platform_scope_id,
            "pid": record.identity.pid,
            "start_time_ticks": record.identity.start_time_ticks,
        },
        "provider_key": record.provider_key,
        "account_id": record.account_id.value if record.account_id else None,
        "principal_id": record.principal_id.value,
        "confirmed_at": record.confirmed_at.isoformat(),
        "record_version": record.record_version,
        "executable_identity": record.executable_identity,
    }


class OwnerAssociationSettingsRepositoryV1:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._thread_lock = RLock()

    @contextmanager
    def _directory(self) -> Iterator[int]:
        try:
            fd = os.open(
                self._root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
            )
            try:
                info = os.fstat(fd)
                if (
                    not stat.S_ISDIR(info.st_mode)
                    or stat.S_IMODE(info.st_mode) != 0o700
                    or info.st_uid != os.getuid()
                ):
                    raise _unavailable()
                yield fd
            finally:
                os.close(fd)
        except (OSError, ValueError, TypeError):
            raise _unavailable() from None

    def _load(self, directory: int) -> dict[str, OwnerProcessAccountAssociationV1]:
        try:
            fd = os.open(
                SETTINGS_NAME,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
                dir_fd=directory,
            )
        except FileNotFoundError:
            return {}
        try:
            _safe_file(fd)
            with os.fdopen(fd, "rb", closefd=False) as stream:
                raw = stream.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise _unavailable()
            document = json.loads(raw, object_pairs_hook=_closed_object)
            if (
                not isinstance(document, dict)
                or set(document) != {"format", "records"}
                or document["format"] != FORMAT
            ):
                raise _unavailable()
            values = document["records"]
            if not isinstance(values, dict) or len(values) > MAX_RECORDS:
                raise _unavailable()
            records = {key: _decode(value) for key, value in values.items()}
            if any(
                owner_association_key(record.identity, record.executable_identity)
                != key
                for key, record in records.items()
            ):
                raise _unavailable()
            return records
        finally:
            os.close(fd)

    def records(self) -> dict[str, OwnerProcessAccountAssociationV1]:
        try:
            with self._directory() as directory:
                return self._load(directory)
        except (OSError, ValueError, TypeError, KeyError):
            raise _unavailable() from None

    def update(
        self,
        key: str,
        transition: Callable[
            [OwnerProcessAccountAssociationV1 | None], OwnerProcessAccountAssociationV1
        ],
    ) -> OwnerProcessAccountAssociationV1:
        try:
            with self._thread_lock, self._directory() as directory:
                lock = os.open(
                    LOCK_NAME,
                    os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC,
                    0o600,
                    dir_fd=directory,
                )
                try:
                    _safe_file(lock)
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    records = self._load(directory)
                    current = records.get(key)
                    updated = transition(current)
                    if updated == current:
                        return updated
                    if (
                        owner_association_key(
                            updated.identity, updated.executable_identity
                        )
                        != key
                    ):
                        raise _unavailable()
                    records[key] = updated
                    raw = json.dumps(
                        {
                            "format": FORMAT,
                            "records": {k: _encode(v) for k, v in records.items()},
                        },
                        separators=(",", ":"),
                        sort_keys=True,
                    ).encode("utf-8")
                    if len(records) > MAX_RECORDS or len(raw) > MAX_BYTES:
                        raise _unavailable()
                    temporary = ".owner-association-" + secrets.token_hex(16)
                    fd = os.open(
                        temporary,
                        os.O_WRONLY
                        | os.O_CREAT
                        | os.O_EXCL
                        | os.O_NOFOLLOW
                        | os.O_CLOEXEC,
                        0o600,
                        dir_fd=directory,
                    )
                    try:
                        with os.fdopen(fd, "wb", closefd=False) as stream:
                            stream.write(raw)
                            stream.flush()
                        os.fsync(fd)
                        os.replace(
                            temporary,
                            SETTINGS_NAME,
                            src_dir_fd=directory,
                            dst_dir_fd=directory,
                        )
                        os.fsync(directory)
                    finally:
                        os.close(fd)
                        try:
                            os.unlink(temporary, dir_fd=directory)
                        except FileNotFoundError:
                            pass
                    return updated
                finally:
                    os.close(lock)
        except (OSError, ValueError, TypeError, KeyError):
            raise _unavailable() from None

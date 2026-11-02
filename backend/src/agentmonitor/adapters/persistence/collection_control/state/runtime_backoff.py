"""Owner-only durable backoff for the optional local Ollama collector."""

from __future__ import annotations

import json
import os
import secrets
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

_STATE_NAME = ".ollama-runtime-collector-v1.json"
_FORMAT = "ollama-runtime-collector-backoff.v1"
_MAXIMUM_BYTES = 256


class OllamaRuntimeBackoffStoreErrorV1(RuntimeError):
    """The private collector state cannot be trusted or updated safely."""


def _unavailable() -> OllamaRuntimeBackoffStoreErrorV1:
    return OllamaRuntimeBackoffStoreErrorV1("ollama_runtime_backoff_store_unavailable")


def _safe_file(descriptor: int) -> None:
    info = os.fstat(descriptor)
    if (
        not stat.S_ISREG(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_uid != os.getuid()
        or info.st_nlink != 1
        or info.st_size > _MAXIMUM_BYTES
    ):
        raise _unavailable()


def _utc_text(value: datetime) -> str:
    if value.utcoffset() != timedelta(0):
        raise _unavailable()
    return (
        value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )


def _utc_value(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or not 1 <= len(value) <= 40:
        raise _unavailable()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise _unavailable() from None
    if parsed.utcoffset() != timedelta(0):
        raise _unavailable()
    return parsed.astimezone(UTC)


class OllamaRuntimeBackoffStoreV1:
    """Persist one sanitized deadline without depending on an available database."""

    def __init__(self, root: Path) -> None:
        self._root = root

    @contextmanager
    def _directory(self) -> Iterator[int]:
        try:
            descriptor = os.open(
                self._root,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            )
            try:
                info = os.fstat(descriptor)
                if (
                    not stat.S_ISDIR(info.st_mode)
                    or stat.S_IMODE(info.st_mode) != 0o700
                    or info.st_uid != os.getuid()
                ):
                    raise _unavailable()
                yield descriptor
            finally:
                os.close(descriptor)
        except OllamaRuntimeBackoffStoreErrorV1:
            raise
        except (OSError, TypeError, ValueError):
            raise _unavailable() from None

    @staticmethod
    def _load(directory: int) -> datetime | None:
        try:
            descriptor = os.open(
                _STATE_NAME,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
                dir_fd=directory,
            )
        except FileNotFoundError:
            return None
        try:
            _safe_file(descriptor)
            with os.fdopen(descriptor, "rb", closefd=False) as stream:
                raw = stream.read(_MAXIMUM_BYTES + 1)
            if len(raw) > _MAXIMUM_BYTES:
                raise _unavailable()
            try:
                document = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise _unavailable() from None
            if (
                not isinstance(document, dict)
                or set(document) != {"format", "not_before_at"}
                or document["format"] != _FORMAT
            ):
                raise _unavailable()
            return _utc_value(document["not_before_at"])
        finally:
            os.close(descriptor)

    def not_before_at(self) -> datetime | None:
        """Read the exact persisted retry deadline, if one exists."""

        try:
            with self._directory() as directory:
                return self._load(directory)
        except OllamaRuntimeBackoffStoreErrorV1:
            raise
        except (OSError, TypeError, ValueError, KeyError):
            raise _unavailable() from None

    def write(self, not_before_at: datetime | None) -> None:
        """Atomically replace the private state after validating any prior file."""

        raw = json.dumps(
            {
                "format": _FORMAT,
                "not_before_at": (
                    _utc_text(not_before_at) if not_before_at is not None else None
                ),
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
        if len(raw) > _MAXIMUM_BYTES:
            raise _unavailable()
        temporary = ".ollama-runtime-collector-" + secrets.token_hex(16)
        try:
            with self._directory() as directory:
                self._load(directory)
                descriptor = os.open(
                    temporary,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                    0o600,
                    dir_fd=directory,
                )
                try:
                    view = memoryview(raw)
                    written = 0
                    while written < len(view):
                        count = os.write(descriptor, view[written:])
                        if count <= 0:
                            raise _unavailable()
                        written += count
                    os.fsync(descriptor)
                    os.replace(
                        temporary,
                        _STATE_NAME,
                        src_dir_fd=directory,
                        dst_dir_fd=directory,
                    )
                    os.fsync(directory)
                finally:
                    os.close(descriptor)
                    try:
                        os.unlink(temporary, dir_fd=directory)
                    except FileNotFoundError:
                        pass
        except OllamaRuntimeBackoffStoreErrorV1:
            raise
        except (OSError, TypeError, ValueError, KeyError):
            raise _unavailable() from None

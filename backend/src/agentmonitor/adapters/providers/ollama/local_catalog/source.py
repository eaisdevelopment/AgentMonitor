"""Bounded read-only Ollama 0.24.0 local catalog observation.

Only explicitly allowed metadata leaves this boundary. No raw responses,
provider profiles, account credentials, inference, or model writes are used.
"""

from __future__ import annotations

import json
import re
import socket
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

SOURCE_ID = "ollama.local.catalog.v1"
ADMITTED_VERSION = "0.24.0"
MAX_BYTES = 256 * 1024
MAX_MODELS = 512
TIMEOUT_SECONDS = 3
OPERATION_TIMEOUT_SECONDS = 12
_COLLECTION_LOCK = threading.Lock()
_ROUTES = frozenset({"/api/version", "/api/tags", "/api/ps"})
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z")
_MAX_HEADERS = 16 * 1024
_MAX_CHUNK_LINE = 1024
_MAX_FRAMING = 64 * 1024
_HEADER_NAME = re.compile(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")

Outcome = Literal[
    "success",
    "partial",
    "provider_unavailable",
    "unverified_provider_version",
    "invalid_provider_data",
    "deadline_exceeded",
]
SourceState = Literal["available", "unavailable"]
SourceReason = Literal[
    "source_available",
    "source_unavailable",
    "invalid_provider_data",
    "unverified_provider_version",
    "collection_in_progress",
    "operation_deadline_exceeded",
]


@dataclass(frozen=True, slots=True)
class Model:
    """Only a bounded Ollama model identifier, never its details or content."""

    name: str


@dataclass(frozen=True, slots=True)
class CatalogResult:
    """Two independently observed inventories; missing is distinct from empty."""

    outcome: Outcome
    daemon_version: str | None
    source: str
    observed_at: datetime
    installed_state: SourceState
    installed: tuple[Model, ...] | None
    installed_reason: SourceReason
    installed_observed_at: datetime | None
    loaded_state: SourceState
    loaded: tuple[Model, ...] | None
    loaded_reason: SourceReason
    loaded_observed_at: datetime | None


def safe_model_name(value: object) -> str:
    """Reject names that cannot be safely displayed as a bounded identifier."""
    if type(value) is not str or _NAME.fullmatch(value) is None:
        raise ValueError("model_name_invalid")
    return value


def version_consistent(initial: object, final: object) -> bool:
    """Admit observations only when both version readings match the exact version."""
    return initial == ADMITTED_VERSION and final == ADMITTED_VERSION


def request_deadline(now: float, operation_deadline: float) -> float:
    """Limit one request to its own budget and the whole operation budget."""
    if now >= operation_deadline:
        raise TimeoutError("operation_deadline_exceeded")
    return min(now + TIMEOUT_SECONDS, operation_deadline)


def _read_chunked_body(sock: socket.socket, initial: bytes, deadline: float) -> bytes:
    """Decode bounded HTTP/1.1 chunk framing under the caller's deadline."""
    pending = bytearray(initial)
    result = bytearray()
    framing = 0

    def receive() -> None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("source_deadline_exceeded")
        sock.settimeout(remaining)
        data = sock.recv(8192)
        if not data:
            raise ValueError("body_incomplete")
        pending.extend(data)

    def line(limit: int) -> bytes:
        nonlocal framing
        while True:
            end = pending.find(b"\r\n")
            if end >= 0:
                if end > limit:
                    raise ValueError("chunk_framing_invalid")
                value = bytes(pending[:end])
                del pending[: end + 2]
                framing += end + 2
                if framing > _MAX_FRAMING:
                    raise ValueError("chunk_framing_too_large")
                return value
            if len(pending) > limit + 1:
                raise ValueError("chunk_framing_invalid")
            receive()

    while True:
        header = line(_MAX_CHUNK_LINE)
        size, separator, extension = header.partition(b";")
        if (
            not size
            or len(size) > 8
            or re.fullmatch(rb"[0-9A-Fa-f]+", size) is None
            or (
                separator
                and (not extension or any(c < 32 or c > 126 for c in extension))
            )
        ):
            raise ValueError("chunk_size_invalid")
        count = int(size, 16)
        if count > MAX_BYTES - len(result):
            raise ValueError("response_too_large")
        if count == 0:
            trailer_size = 0
            while True:
                trailer = line(_MAX_HEADERS)
                trailer_size += len(trailer) + 2
                if trailer_size > _MAX_HEADERS:
                    raise ValueError("trailers_too_large")
                if not trailer:
                    if pending:
                        raise ValueError("body_trailing_data")
                    return bytes(result)
                name, separator, value = trailer.partition(b":")
                if (
                    not separator
                    or _HEADER_NAME.fullmatch(name) is None
                    or name.lower() in {b"content-length", b"transfer-encoding"}
                    or any(c < 32 and c != 9 or c == 127 for c in value)
                ):
                    raise ValueError("trailer_invalid")
        while len(pending) < count + 2:
            receive()
        result.extend(pending[:count])
        if pending[count : count + 2] != b"\r\n":
            raise ValueError("chunk_terminator_invalid")
        del pending[: count + 2]
        framing += 2
        if framing > _MAX_FRAMING:
            raise ValueError("chunk_framing_too_large")


def _read_json(
    route: str, *, operation_deadline: float | None = None
) -> dict[str, object]:
    if route not in _ROUTES:
        raise ValueError("source_not_allowed")
    now = time.monotonic()
    deadline = request_deadline(
        now,
        operation_deadline if operation_deadline is not None else now + TIMEOUT_SECONDS,
    )
    connect_timeout = deadline - time.monotonic()
    if connect_timeout <= 0:
        raise TimeoutError("operation_deadline_exceeded")
    with socket.create_connection(
        ("127.0.0.1", 11434), timeout=connect_timeout
    ) as sock:

        def remaining() -> float:
            value = deadline - time.monotonic()
            if value <= 0:
                raise TimeoutError("source_deadline_exceeded")
            return value

        sock.settimeout(remaining())
        sock.sendall(
            f"GET {route} HTTP/1.1\r\nHost: 127.0.0.1:11434\r\n"
            "Accept: application/json\r\nConnection: close\r\n\r\n".encode("ascii")
        )
        data = bytearray()
        while b"\r\n\r\n" not in data:
            sock.settimeout(remaining())
            chunk = sock.recv(8192)
            if not chunk:
                raise ValueError("headers_incomplete")
            data.extend(chunk)
            if len(data) > _MAX_HEADERS + MAX_BYTES:
                raise ValueError("response_too_large")
        raw_headers, body = bytes(data).split(b"\r\n\r\n", 1)
        if len(raw_headers) > _MAX_HEADERS:
            raise ValueError("headers_too_large")
        lines = raw_headers.split(b"\r\n")
        status = lines[0].split(b" ", 2)
        if len(status) < 2 or status[0] != b"HTTP/1.1" or status[1] != b"200":
            raise ValueError("response_status_invalid")
        headers: dict[bytes, bytes] = {}
        for line in lines[1:]:
            name, separator, value = line.partition(b":")
            name = name.strip().lower()
            if not separator or not name or name in headers:
                raise ValueError("headers_invalid")
            headers[name] = value.strip()
        content_type = headers.get(b"content-type", b"").split(b";", 1)[0].lower()
        if content_type != b"application/json":
            raise ValueError("content_type_invalid")
        transfer_encoding = headers.get(b"transfer-encoding")
        length_bytes = headers.get(b"content-length", b"")
        if transfer_encoding is not None:
            if transfer_encoding.lower() != b"chunked" or b"content-length" in headers:
                raise ValueError("transfer_encoding_invalid")
            response_body = _read_chunked_body(sock, body, deadline)
        else:
            if not length_bytes.isdigit():
                raise ValueError("content_length_invalid")
            length = int(length_bytes)
            if length > MAX_BYTES or len(body) > length:
                raise ValueError("response_too_large")
            result = bytearray(body)
            while len(result) < length:
                sock.settimeout(remaining())
                chunk = sock.recv(min(16384, length - len(result)))
                if not chunk:
                    raise ValueError("body_incomplete")
                result.extend(chunk)
            response_body = bytes(result)
    parsed = json.loads(response_body)
    if type(parsed) is not dict:
        raise ValueError("object_required")
    return parsed


def _read_models(
    route: str, operation_deadline: float
) -> tuple[tuple[Model, ...] | None, SourceReason, datetime]:
    try:
        values = _read_json(route, operation_deadline=operation_deadline).get("models")
        if type(values) is not list or len(values) > MAX_MODELS:
            raise ValueError("model_list_invalid")
        result: list[Model] = []
        seen: set[str] = set()
        for value in values:
            if type(value) is not dict:
                raise ValueError("model_invalid")
            name = safe_model_name(value.get("name"))
            if name in seen:
                raise ValueError("model_duplicate")
            seen.add(name)
            result.append(Model(name=name))
        return tuple(result), "source_available", datetime.now(UTC)
    except (ValueError, UnicodeError, RecursionError):
        return None, "invalid_provider_data", datetime.now(UTC)
    except (OSError, TimeoutError):
        return None, "source_unavailable", datetime.now(UTC)


def _unavailable(outcome: Outcome, reason: SourceReason) -> CatalogResult:
    return CatalogResult(
        outcome=outcome,
        daemon_version=None,
        source=SOURCE_ID,
        observed_at=datetime.now(UTC),
        installed_state="unavailable",
        installed=None,
        installed_reason=reason,
        installed_observed_at=None,
        loaded_state="unavailable",
        loaded=None,
        loaded_reason=reason,
        loaded_observed_at=None,
    )


def read_local_catalog() -> CatalogResult:
    """Observe the admitted local daemon without altering its state."""
    operation_deadline = time.monotonic() + OPERATION_TIMEOUT_SECONDS
    if not _COLLECTION_LOCK.acquire(blocking=False):
        return _unavailable("provider_unavailable", "collection_in_progress")
    try:
        result = _read_local_catalog(operation_deadline)
        if time.monotonic() >= operation_deadline:
            return _unavailable("deadline_exceeded", "operation_deadline_exceeded")
        return result
    finally:
        _COLLECTION_LOCK.release()


def _read_local_catalog(operation_deadline: float) -> CatalogResult:
    try:
        version = _read_json("/api/version", operation_deadline=operation_deadline).get(
            "version"
        )
        if type(version) is not str or not re.fullmatch(
            r"[0-9]+\.[0-9]+\.[0-9]+", version
        ):
            raise ValueError("version_invalid")
    except (ValueError, UnicodeError, RecursionError):
        return _unavailable("invalid_provider_data", "invalid_provider_data")
    except (OSError, TimeoutError):
        return _unavailable("provider_unavailable", "source_unavailable")
    if version != ADMITTED_VERSION:
        return _unavailable(
            "unverified_provider_version", "unverified_provider_version"
        )

    installed, installed_reason, installed_at = _read_models(
        "/api/tags", operation_deadline
    )
    loaded, loaded_reason, loaded_at = _read_models("/api/ps", operation_deadline)
    try:
        final_version = _read_json(
            "/api/version", operation_deadline=operation_deadline
        ).get("version")
        if type(final_version) is not str or not re.fullmatch(
            r"[0-9]+\.[0-9]+\.[0-9]+", final_version
        ):
            raise ValueError("version_invalid")
    except (ValueError, UnicodeError, RecursionError):
        return _unavailable("invalid_provider_data", "invalid_provider_data")
    except (OSError, TimeoutError):
        return _unavailable("provider_unavailable", "source_unavailable")
    if not version_consistent(version, final_version):
        return _unavailable(
            "unverified_provider_version", "unverified_provider_version"
        )
    if installed is not None and loaded is not None:
        outcome: Outcome = "success"
    elif installed is not None or loaded is not None:
        outcome = "partial"
    elif "invalid_provider_data" in {installed_reason, loaded_reason}:
        outcome = "invalid_provider_data"
    else:
        outcome = "provider_unavailable"
    return CatalogResult(
        outcome=outcome,
        daemon_version=version,
        source=SOURCE_ID,
        observed_at=datetime.now(UTC),
        installed_state="available" if installed is not None else "unavailable",
        installed=installed,
        installed_reason=installed_reason,
        installed_observed_at=installed_at,
        loaded_state="available" if loaded is not None else "unavailable",
        loaded=loaded,
        loaded_reason=loaded_reason,
        loaded_observed_at=loaded_at,
    )

"""Bounded local JSONL transport for the exact admitted Codex app server."""

from __future__ import annotations

import errno
import json
import math
import os
import pwd
import selectors
import signal
import stat
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Final, Literal

from agentmonitor.adapters.providers.codex.installation import (
    CodexInstallationUnavailable,
    CodexInstallationV1,
)
from agentmonitor.adapters.providers.codex.manifest import CODEX_PROVIDER_VERSION

CodexAppServerMethodV1 = Literal[
    "account/read",
    "account/rateLimits/read",
]

_MAX_REQUEST_BYTES: Final = 4096
_MAX_JSON_DEPTH: Final = 24
_ALLOWED_METHODS: Final = ("account/read", "account/rateLimits/read")
_SUPPRESSED_STARTUP_NOTIFICATIONS: Final = (
    "account/updated",
    "configWarning",
    "remoteControl/status/changed",
)


class CodexAppServerFailure(RuntimeError):
    """A sanitized local source failure; provider text is never retained."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class _InvalidJsonValue(ValueError):
    pass


def _request_parameters_v1(
    method: CodexAppServerMethodV1,
) -> dict[str, object]:
    if method == "account/read":
        return {"refreshToken": False}
    if method == "account/rateLimits/read":
        return {
            "excludeResetCreditDetails": True,
            "supportsLunaReserve": False,
        }
    raise CodexAppServerFailure("codex_app_server_request_invalid")


def _lexical_absolute(path: Path) -> Path:
    if not isinstance(path, Path) or not path.is_absolute():
        raise CodexAppServerFailure("codex_managed_profile_unsafe")
    normalized = Path(os.path.normpath(os.fspath(path)))
    if path != normalized or any(part == ".." for part in path.parts):
        raise CodexAppServerFailure("codex_managed_profile_unsafe")
    return normalized


def _lstat_directory(path: Path) -> os.stat_result:
    try:
        info = path.lstat()
    except OSError:
        raise CodexAppServerFailure("codex_managed_profile_unavailable") from None
    if stat.S_ISLNK(info.st_mode):
        raise CodexAppServerFailure("codex_managed_profile_unsafe")
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) & 0o077
    ):
        raise CodexAppServerFailure("codex_managed_profile_unsafe")
    return info


def _reject_symlink_components(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            info = current.lstat()
        except OSError:
            raise CodexAppServerFailure("codex_managed_profile_unavailable") from None
        if stat.S_ISLNK(info.st_mode):
            raise CodexAppServerFailure("codex_managed_profile_unsafe")


def _protected_default_roots() -> tuple[Path, ...]:
    default_root = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".codex"
    roots = [default_root]
    configured = os.environ.get("CODEX_HOME")
    if configured:
        configured_path = Path(configured).expanduser()
        if not configured_path.is_absolute():
            configured_path = Path.cwd() / configured_path
        configured_path = Path(os.path.normpath(os.fspath(configured_path)))
        roots.append(configured_path)
        if not _is_within(configured_path, default_root):
            try:
                target = configured_path.readlink()
            except OSError as error:
                if error.errno not in {errno.ENOENT, errno.EINVAL}:
                    raise CodexAppServerFailure(
                        "codex_managed_profile_unsafe"
                    ) from None
            else:
                if not target.is_absolute():
                    target = configured_path.parent / target
                roots.append(Path(os.path.normpath(os.fspath(target))))
    return tuple(
        dict.fromkeys(Path(os.path.normpath(os.fspath(root))) for root in roots)
    )


def _is_within(candidate: Path, parent: Path) -> bool:
    return candidate == parent or parent in candidate.parents


def validate_codex_managed_profile_root_v1(
    *,
    managed_profiles_root: Path,
    managed_profile_root: Path,
) -> Path:
    """Validate one private managed profile below its explicit private root."""
    profiles_root = _lexical_absolute(managed_profiles_root)
    profile_root = _lexical_absolute(managed_profile_root)
    try:
        relative = profile_root.relative_to(profiles_root)
    except ValueError:
        raise CodexAppServerFailure("codex_managed_profile_unsafe") from None
    if relative == Path(".") or not relative.parts:
        raise CodexAppServerFailure("codex_managed_profile_unsafe")
    for protected in _protected_default_roots():
        if _is_within(profiles_root, protected) or _is_within(profile_root, protected):
            raise CodexAppServerFailure("codex_managed_profile_unsafe")

    _reject_symlink_components(profiles_root)
    _lstat_directory(profiles_root)
    current = profiles_root
    for part in relative.parts:
        current /= part
        _lstat_directory(current)
    try:
        resolved_profiles = profiles_root.resolve(strict=True)
        resolved_profile = profile_root.resolve(strict=True)
    except OSError:
        raise CodexAppServerFailure("codex_managed_profile_unavailable") from None
    if not _is_within(resolved_profile, resolved_profiles) or (
        resolved_profile == resolved_profiles
    ):
        raise CodexAppServerFailure("codex_managed_profile_unsafe")
    for protected in _protected_default_roots():
        if _is_within(resolved_profiles, protected) or _is_within(
            resolved_profile, protected
        ):
            raise CodexAppServerFailure("codex_managed_profile_unsafe")
    return resolved_profile


def validate_codex_managed_auth_store_v1(
    root: Path,
    *,
    required: bool,
) -> None:
    """Validate only safe credential-store metadata before or after provider use."""
    auth_store = root / "auth.json"
    try:
        info = auth_store.lstat()
    except FileNotFoundError:
        if required:
            raise CodexAppServerFailure(
                "codex_managed_authentication_required"
            ) from None
        return
    except OSError:
        raise CodexAppServerFailure("codex_managed_profile_unavailable") from None
    if (
        stat.S_ISLNK(info.st_mode)
        or not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_nlink != 1
        or stat.S_IMODE(info.st_mode) & 0o077
        or not 1 <= info.st_size <= 1024 * 1024
    ):
        raise CodexAppServerFailure("codex_managed_profile_unsafe")


class _JsonLineFramerV1:
    """Pure bounded byte framing; constructed bytes are safe unit-test inputs."""

    MAX_LINE_BYTES: Final = 256 * 1024
    MAX_TOTAL_BYTES: Final = 1024 * 1024
    MAX_MESSAGES: Final = 8

    def __init__(self) -> None:
        self._buffer = bytearray()
        self._total_bytes = 0
        self._messages = 0

    def append(self, chunk: bytes) -> None:
        if type(chunk) is not bytes or not chunk:
            raise CodexAppServerFailure("codex_app_server_protocol_invalid")
        self._total_bytes += len(chunk)
        if self._total_bytes > self.MAX_TOTAL_BYTES:
            raise CodexAppServerFailure("codex_app_server_output_too_large")
        self._buffer.extend(chunk)
        newline = self._buffer.find(b"\n")
        if (newline < 0 and len(self._buffer) > self.MAX_LINE_BYTES) or (
            newline > self.MAX_LINE_BYTES
        ):
            raise CodexAppServerFailure("codex_app_server_output_too_large")

    def next_line(self) -> bytes | None:
        newline = self._buffer.find(b"\n")
        if newline < 0:
            if len(self._buffer) > self.MAX_LINE_BYTES:
                raise CodexAppServerFailure("codex_app_server_output_too_large")
            return None
        if newline > self.MAX_LINE_BYTES:
            raise CodexAppServerFailure("codex_app_server_output_too_large")
        raw = bytes(self._buffer[:newline])
        del self._buffer[: newline + 1]
        if not raw:
            raise CodexAppServerFailure("codex_app_server_protocol_invalid")
        self._messages += 1
        if self._messages > self.MAX_MESSAGES:
            raise CodexAppServerFailure("codex_app_server_message_limit_exceeded")
        return raw


def _validate_json_depth(raw: bytes) -> None:
    depth = 0
    in_string = False
    escaped = False
    for value in raw:
        if in_string:
            if escaped:
                escaped = False
            elif value == 0x5C:
                escaped = True
            elif value == 0x22:
                in_string = False
            continue
        if value == 0x22:
            in_string = True
        elif value in (0x7B, 0x5B):
            depth += 1
            if depth > _MAX_JSON_DEPTH:
                raise CodexAppServerFailure("codex_app_server_json_depth_exceeded")
        elif value in (0x7D, 0x5D):
            depth -= 1
            if depth < 0:
                raise CodexAppServerFailure("codex_app_server_protocol_invalid")


def _closed_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise _InvalidJsonValue
        value[key] = item
    return value


def _reject_json_constant(_value: str) -> object:
    raise _InvalidJsonValue


def _decode_codex_response_line_v1(
    raw: bytes,
    *,
    request_id: int,
) -> dict[str, object]:
    """Decode one exact response envelope and reject all notifications."""
    if (
        type(raw) is not bytes
        or not raw
        or len(raw) > _JsonLineFramerV1.MAX_LINE_BYTES
        or type(request_id) is not int
        or request_id < 1
    ):
        raise CodexAppServerFailure("codex_app_server_protocol_invalid")
    _validate_json_depth(raw)
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_closed_json_object,
            parse_constant=_reject_json_constant,
            parse_float=_reject_json_constant,
        )
    except (
        UnicodeDecodeError,
        ValueError,
        RecursionError,
    ):
        raise CodexAppServerFailure("codex_app_server_protocol_invalid") from None
    if type(value) is not dict:
        raise CodexAppServerFailure("codex_app_server_protocol_invalid")
    response_id = value.get("id")
    if response_id is None:
        raise CodexAppServerFailure("codex_app_server_notification_rejected")
    if type(response_id) is not int or response_id != request_id:
        raise CodexAppServerFailure("codex_app_server_unexpected_response")
    keys = set(value)
    if keys == {"id", "error"}:
        raise CodexAppServerFailure("codex_app_server_request_failed")
    if keys != {"id", "result"} or type(value.get("result")) is not dict:
        raise CodexAppServerFailure("codex_app_server_protocol_invalid")
    result = value["result"]
    assert isinstance(result, dict)
    return result


def _bounded_text(value: object, *, maximum: int) -> bool:
    return (
        type(value) is str
        and 1 <= len(value) <= maximum
        and value.isprintable()
        and not any(character.isspace() and character != " " for character in value)
    )


def _validate_initialize_result_v1(
    result: dict[str, object],
    *,
    expected_root: Path,
    provider_version: str,
) -> None:
    expected_keys = {"userAgent", "codexHome", "platformFamily", "platformOs"}
    user_agent = result.get("userAgent")
    if (
        type(result) is not dict
        or set(result) != expected_keys
        or not _bounded_text(user_agent, maximum=512)
        or not isinstance(user_agent, str)
        or not user_agent.startswith(f"agentmonitor/{provider_version} ")
        or result.get("codexHome") != str(expected_root)
        or result.get("platformFamily") != "unix"
        or result.get("platformOs") != "linux"
    ):
        raise CodexAppServerFailure("codex_app_server_initialize_invalid")


def _terminate_owned_process(process: subprocess.Popen[bytes]) -> bool:
    try:
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except OSError:
                pass
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except OSError:
                    pass
                try:
                    process.wait(timeout=2)
                except (OSError, subprocess.TimeoutExpired):
                    pass
        return process.poll() is not None
    except (OSError, ValueError):
        return False


class _JsonLineReader:
    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        if process.stdout is None:
            raise CodexAppServerFailure("codex_app_server_pipe_unavailable")
        self._process = process
        self._stream = process.stdout
        self._selector = selectors.DefaultSelector()
        try:
            self._selector.register(self._stream, selectors.EVENT_READ)
        except (OSError, ValueError):
            self._selector.close()
            raise CodexAppServerFailure("codex_app_server_pipe_unavailable") from None
        self._framer = _JsonLineFramerV1()

    def close(self) -> None:
        try:
            self._selector.close()
        except (OSError, ValueError):
            pass

    def response(self, request_id: int, *, deadline: float) -> dict[str, object]:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise CodexAppServerFailure("codex_app_server_deadline_exceeded")
            raw = self._framer.next_line()
            if raw is not None:
                result = _decode_codex_response_line_v1(raw, request_id=request_id)
                if time.monotonic() >= deadline:
                    result.clear()
                    raise CodexAppServerFailure("codex_app_server_deadline_exceeded")
                return result
            try:
                events = self._selector.select(min(remaining, 0.25))
            except (OSError, ValueError):
                raise CodexAppServerFailure("codex_app_server_unavailable") from None
            if not events:
                if self._process.poll() is not None:
                    raise CodexAppServerFailure("codex_app_server_unavailable")
                continue
            try:
                chunk = os.read(self._stream.fileno(), 65_536)
            except OSError:
                raise CodexAppServerFailure("codex_app_server_unavailable") from None
            if not chunk:
                raise CodexAppServerFailure("codex_app_server_unavailable")
            self._framer.append(chunk)


def _write_message(process: subprocess.Popen[bytes], value: dict[str, object]) -> None:
    if process.stdin is None:
        raise CodexAppServerFailure("codex_app_server_pipe_unavailable")
    encoded = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    if len(encoded) > _MAX_REQUEST_BYTES:
        raise CodexAppServerFailure("codex_app_server_request_invalid")
    try:
        process.stdin.write(encoded + b"\n")
        process.stdin.flush()
    except (BrokenPipeError, OSError):
        raise CodexAppServerFailure("codex_app_server_unavailable") from None


def _cleanup_process(
    process: subprocess.Popen[bytes],
    reader: _JsonLineReader | None,
) -> bool:
    if reader is not None:
        reader.close()
    if process.stdin is not None:
        try:
            process.stdin.close()
        except (OSError, ValueError):
            pass
    terminated = _terminate_owned_process(process)
    if process.stdout is not None:
        try:
            process.stdout.close()
        except (OSError, ValueError):
            pass
    return terminated


def invoke_codex_app_server_v1[ResultT](
    installation: CodexInstallationV1,
    *,
    managed_profiles_root: Path,
    managed_profile_root: Path,
    method: CodexAppServerMethodV1,
    deadline_monotonic: float,
    parse_result: Callable[[dict[str, object]], ResultT],
) -> ResultT:
    """Run one allowlisted query with approved managed-auth maintenance."""
    if method not in _ALLOWED_METHODS or not callable(parse_result):
        raise CodexAppServerFailure("codex_app_server_request_invalid")
    if type(deadline_monotonic) is not float or not math.isfinite(deadline_monotonic):
        raise CodexAppServerFailure("codex_app_server_request_invalid")
    remaining = deadline_monotonic - time.monotonic()
    if remaining > 30.0:
        raise CodexAppServerFailure("codex_app_server_request_invalid")
    if remaining <= 0:
        raise CodexAppServerFailure("codex_app_server_deadline_exceeded")
    root = validate_codex_managed_profile_root_v1(
        managed_profiles_root=managed_profiles_root,
        managed_profile_root=managed_profile_root,
    )
    validate_codex_managed_auth_store_v1(root, required=True)
    if (
        installation.provider_version != CODEX_PROVIDER_VERSION
        or installation.platform_id != "linux-x86_64"
    ):
        raise CodexAppServerFailure("codex_executable_changed")
    try:
        executable = installation.executable_for_launch()
    except CodexInstallationUnavailable:
        raise CodexAppServerFailure("codex_executable_changed") from None
    arguments = [
        str(executable),
        "-c",
        'cli_auth_credentials_store="file"',
        "-c",
        "analytics.enabled=false",
        "-c",
        'otel.exporter="none"',
        "-c",
        'otel.trace_exporter="none"',
        "-c",
        'otel.metrics_exporter="none"',
        "-c",
        "otel.log_user_prompt=false",
        "app-server",
        "--listen",
        "stdio://",
    ]
    environment = {
        "HOME": str(root),
        "CODEX_HOME": str(root),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "NO_COLOR": "1",
    }
    try:
        process = subprocess.Popen(  # noqa: S603 - retained exact executable
            arguments,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=root,
            env=environment,
            shell=False,
            start_new_session=True,
        )
    except OSError:
        raise CodexAppServerFailure("codex_app_server_unavailable") from None

    reader: _JsonLineReader | None = None
    try:
        reader = _JsonLineReader(process)
        _write_message(
            process,
            {
                "id": 1,
                "method": "initialize",
                "params": {
                    "capabilities": {
                        "experimentalApi": False,
                        "optOutNotificationMethods": list(
                            _SUPPRESSED_STARTUP_NOTIFICATIONS
                        ),
                    },
                    "clientInfo": {"name": "agentmonitor", "version": "1.0.0"},
                },
            },
        )
        initialize_result = reader.response(1, deadline=deadline_monotonic)
        try:
            _validate_initialize_result_v1(
                initialize_result,
                expected_root=root,
                provider_version=installation.provider_version,
            )
        finally:
            initialize_result.clear()
        _write_message(process, {"method": "initialized"})
        _write_message(
            process,
            {"id": 2, "method": method, "params": _request_parameters_v1(method)},
        )
        raw_result = reader.response(2, deadline=deadline_monotonic)
        try:
            parsed = parse_result(raw_result)
        finally:
            raw_result.clear()
        if time.monotonic() >= deadline_monotonic:
            raise CodexAppServerFailure("codex_app_server_deadline_exceeded")
    except BaseException:
        _cleanup_process(process, reader)
        validate_codex_managed_auth_store_v1(root, required=True)
        raise
    cleaned_up = _cleanup_process(process, reader)
    validate_codex_managed_auth_store_v1(root, required=True)
    if not cleaned_up:
        raise CodexAppServerFailure("codex_app_server_cleanup_failed")
    return parsed

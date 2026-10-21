"""Authenticated M5 Codex managed-profile filesystem containment evidence.

The verifier runs the production identity and subscription-quota operations
under the real system ``strace``.  Provider stdout stays inside the production
transport and the outer verifier sends all driver output to ``/dev/null``.
Only a selector-bound digest and aggregate syscall counts leave this module.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import pwd
import re
import shutil
import signal
import stat
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, cast

ROOT = Path(__file__).resolve().parents[3]
BACKEND_SOURCE = ROOT / "backend/src"
_BACKEND_PYTHON = ROOT / "backend/.venv/bin/python"
_STRACE = Path("/usr/bin/strace")
_INPUT_FD_ENV = "AGENTMONITOR_M5_CONTAINMENT_INPUT_FD"
_RESULT_FD_ENV = "AGENTMONITOR_M5_CONTAINMENT_RESULT_FD"
_INPUT_SCHEMA = "agentmonitor.m5-codex-containment-input.v1"
_RESULT_SCHEMA = "agentmonitor.m5-codex-containment-result.v1"
_DIGEST_SCHEMA = "agentmonitor.m5-codex-containment-evidence.v1"
_INPUT_LIMIT_BYTES = 16 * 1024
_RESULT_LIMIT_BYTES = 4096
_TRACE_LIMIT_BYTES = 16 * 1024 * 1024
_ACCOUNT_ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_REVISION = re.compile(r"[0-9a-f]{40}\Z")
_TRACE_LINE = re.compile(
    r"^(?P<pid>[1-9][0-9]*)\s+(?P<call>[A-Za-z0-9_]+)"
    r"\((?P<arguments>.*)\)\s+=\s+(?P<result>.+)$"
)
_TRACE_UNFINISHED = re.compile(
    r"^(?P<pid>[1-9][0-9]*)\s+(?P<call>[A-Za-z0-9_]+)"
    r"\((?P<arguments>.*)\s+<unfinished \.\.\.>$"
)
_TRACE_RESUMED = re.compile(
    r"^(?P<pid>[1-9][0-9]*)\s+<\.\.\.\s+(?P<call>[A-Za-z0-9_]+)"
    r" resumed>(?P<arguments>.*)\)\s+=\s+(?P<result>.+)$"
)
_TRACE_QUOTED = re.compile(r'"((?:[^"\\]|\\.)*)"')
_TRACE_ESCAPE = re.compile(r"\\(?:[0-7]{3}|\\|\")")
_TRACE_RESULT_DESCRIPTOR = re.compile(r"^[0-9]+<(?P<path>.*)>$")
_TRACE_AT_FDCWD = re.compile(r"(?:^|,\s*)AT_FDCWD(?:<[^>]*>)?(?=,)")
_WRITE_FLAGS = (
    "O_WRONLY",
    "O_RDWR",
    "O_CREAT",
    "O_TRUNC",
    "O_APPEND",
    "O_TMPFILE",
)
_WRITE_CALLS = frozenset(
    {
        "chmod",
        "chown",
        "creat",
        "fchmodat",
        "fchmodat2",
        "fchownat",
        "lchown",
        "link",
        "linkat",
        "mkdir",
        "mkdirat",
        "mknod",
        "mknodat",
        "mount",
        "move_mount",
        "open_tree",
        "pivot_root",
        "rename",
        "renameat",
        "renameat2",
        "rmdir",
        "symlink",
        "symlinkat",
        "truncate",
        "unlink",
        "unlinkat",
        "umount",
        "umount2",
        "utime",
        "utimensat",
        "utimes",
    }
)
_METADATA_CALLS = frozenset(
    {
        "access",
        "faccessat",
        "faccessat2",
        "lstat",
        "newfstatat",
        "readlink",
        "readlinkat",
        "stat",
        "statx",
    }
)
_CHILD_CALLS = frozenset({"clone", "clone3", "fork", "vfork"})
_EXIT_CALLS = frozenset({"exit", "exit_group"})
_OPEN_CALLS = frozenset({"creat", "open", "openat", "openat2"})
_DIRFD_COUNTS = {
    "execveat": 1,
    "faccessat": 1,
    "faccessat2": 1,
    "fchmodat": 1,
    "fchmodat2": 1,
    "fchownat": 1,
    "linkat": 2,
    "mkdirat": 1,
    "mknodat": 1,
    "newfstatat": 1,
    "openat": 1,
    "openat2": 1,
    "readlinkat": 1,
    "renameat": 2,
    "renameat2": 2,
    "statx": 1,
    "symlinkat": 1,
    "unlinkat": 1,
    "utimensat": 1,
}
_LINK_CALLS = frozenset({"link", "linkat", "symlink", "symlinkat"})
_FD_ONLY_MUTATORS = frozenset({"fallocate", "fchmod", "fchown", "ftruncate"})
_PATH_FOLLOWING_MUTATORS = frozenset(
    {
        "chmod",
        "chown",
        "fchmodat",
        "fchmodat2",
        "fchownat",
        "mount",
        "move_mount",
        "open_tree",
        "pivot_root",
        "truncate",
        "umount",
        "umount2",
        "utime",
        "utimensat",
        "utimes",
    }
)
_DRIVER_TIMEOUT_SECONDS: Final = 90


class M5CodexContainmentErrorV1(RuntimeError):
    """One sanitized deterministic containment or identity failure."""


class M5CodexContainmentUnavailableV1(M5CodexContainmentErrorV1):
    """A missing real prerequisite that blocks containment verification."""


@dataclass(frozen=True, slots=True)
class M5CodexContainmentEvidenceV1:
    """Only sanitized digest and count evidence safe for the M5 receipt."""

    evidence_digest: str
    provider_access_count: int
    provider_write_count: int
    default_profile_access_count: int
    default_profile_write_count: int


@dataclass(frozen=True, slots=True)
class M5CodexTraceSummaryV1:
    """Pure trace-policy result; no path or provider value survives."""

    provider_execution_count: int
    provider_access_count: int
    provider_write_count: int
    default_profile_access_count: int
    default_profile_write_count: int


@dataclass(frozen=True, slots=True)
class _TraceRecordV1:
    pid: int
    call: str
    arguments: str
    result: str


@dataclass(frozen=True, slots=True)
class _SelectionV1:
    owner_data_root: Path
    account_id: str
    managed_profiles_root: Path
    managed_profile_root: Path
    revision: str
    service_pid: int
    service_start_time_ticks: int


@dataclass(frozen=True, slots=True)
class _ExecutableV1:
    path: Path
    launcher_directory: Path
    identity: tuple[int, int, int, int, int, int, int, int]


@dataclass(frozen=True, slots=True)
class _PythonRuntimeV1:
    path: Path
    launcher_identity: tuple[int, int, int, int]
    target_identity: tuple[int, int, int, int, int, int, int, int]


type _InodeIdentityV1 = tuple[int, int]


def _is_within(candidate: Path, parent: Path) -> bool:
    return candidate == parent or parent in candidate.parents


def _normalized_absolute(path: Path, code: str) -> Path:
    if not isinstance(path, Path) or not path.is_absolute():
        raise M5CodexContainmentErrorV1(code)
    normalized = Path(os.path.normpath(os.fspath(path)))
    if normalized != path or any(part == ".." for part in path.parts):
        raise M5CodexContainmentErrorV1(code)
    return normalized


def _private_directory(path: Path, code: str) -> os.stat_result:
    try:
        info = path.lstat()
        resolved = path.resolve(strict=True)
    except OSError:
        raise M5CodexContainmentErrorV1(code) from None
    if (
        resolved != path
        or stat.S_ISLNK(info.st_mode)
        or not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o700
    ):
        raise M5CodexContainmentErrorV1(code)
    return info


def _process_start_ticks(pid: int) -> int:
    try:
        process = Path(f"/proc/{pid}")
        if process.stat().st_uid != os.getuid():
            raise OSError
        raw = (process / "stat").read_bytes()
        if not 1 <= len(raw) <= 8192:
            raise OSError
        fields = raw.rsplit(b") ", 1)[1].split()
        value = int(fields[19])
        if value < 1:
            raise ValueError
        return value
    except (IndexError, OSError, ValueError):
        raise M5CodexContainmentUnavailableV1(
            "m5_codex_containment_service_unavailable"
        ) from None


def _validate_selection(
    *,
    owner_data_root: Path,
    account_id: str,
    managed_profiles_root: Path,
    managed_profile_root: Path,
    revision: str,
    service_pid: int,
    service_start_time_ticks: int,
) -> _SelectionV1:
    owner = _normalized_absolute(
        owner_data_root, "m5_codex_containment_selection_invalid"
    )
    profiles = _normalized_absolute(
        managed_profiles_root, "m5_codex_containment_selection_invalid"
    )
    profile = _normalized_absolute(
        managed_profile_root, "m5_codex_containment_selection_invalid"
    )
    if (
        type(account_id) is not str
        or _ACCOUNT_ID.fullmatch(account_id) is None
        or type(revision) is not str
        or _REVISION.fullmatch(revision) is None
        or type(service_pid) is not int
        or not 1 <= service_pid <= 2**31 - 1
        or type(service_start_time_ticks) is not int
        or not 1 <= service_start_time_ticks <= 2**63 - 1
        or profiles != owner / "profiles" / "codex"
        or profile != profiles / hashlib.sha256(account_id.encode("utf-8")).hexdigest()
    ):
        raise M5CodexContainmentErrorV1("m5_codex_containment_selection_invalid")
    _private_directory(owner, "m5_codex_containment_selection_invalid")
    _private_directory(profiles, "m5_codex_containment_selection_invalid")
    _private_directory(profile, "m5_codex_containment_selection_invalid")
    observed_ticks = _process_start_ticks(service_pid)
    if observed_ticks != service_start_time_ticks:
        raise M5CodexContainmentUnavailableV1("m5_codex_containment_service_mismatch")
    return _SelectionV1(
        owner,
        account_id,
        profiles,
        profile,
        revision,
        service_pid,
        service_start_time_ticks,
    )


def _executable_identity(
    executable: Path,
) -> tuple[int, int, int, int, int, int, int, int]:
    try:
        info = executable.lstat()
    except OSError:
        raise M5CodexContainmentUnavailableV1(
            "m5_codex_containment_executable_unavailable"
        ) from None
    if (
        executable.name != "codex"
        or not stat.S_ISREG(info.st_mode)
        or info.st_uid not in {0, os.getuid()}
        or info.st_mode & 0o022
        or not os.access(executable, os.X_OK)
    ):
        raise M5CodexContainmentErrorV1("m5_codex_containment_executable_invalid")
    return (
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
        info.st_uid,
        info.st_gid,
        stat.S_IMODE(info.st_mode),
    )


def _resolve_executable(
    *,
    system_name: str | None = None,
    machine_name: str | None = None,
    search_path: str | None = None,
) -> _ExecutableV1:
    selected_system = platform.system() if system_name is None else system_name
    selected_machine = platform.machine() if machine_name is None else machine_name
    if selected_system != "Linux" or selected_machine != "x86_64":
        raise M5CodexContainmentUnavailableV1(
            "m5_codex_containment_platform_unverified"
        )
    found = shutil.which("codex", path=search_path)
    if found is None or not Path(found).is_absolute():
        raise M5CodexContainmentUnavailableV1(
            "m5_codex_containment_executable_unavailable"
        )
    launcher = Path(found)
    try:
        executable = launcher.resolve(strict=True)
    except OSError:
        raise M5CodexContainmentUnavailableV1(
            "m5_codex_containment_executable_unavailable"
        ) from None
    return _ExecutableV1(
        executable,
        executable.parent,
        _executable_identity(executable),
    )


def _resolve_python_runtime() -> _PythonRuntimeV1:
    try:
        launcher = _BACKEND_PYTHON.lstat()
        target = _BACKEND_PYTHON.resolve(strict=True)
        target_info = target.lstat()
    except OSError:
        raise M5CodexContainmentUnavailableV1(
            "m5_codex_containment_runtime_unavailable"
        ) from None
    if (
        not (stat.S_ISLNK(launcher.st_mode) or stat.S_ISREG(launcher.st_mode))
        or launcher.st_uid not in {0, os.getuid()}
        or not stat.S_ISREG(target_info.st_mode)
        or target_info.st_uid not in {0, os.getuid()}
        or target_info.st_mode & 0o022
        or not os.access(_BACKEND_PYTHON, os.X_OK)
    ):
        raise M5CodexContainmentUnavailableV1(
            "m5_codex_containment_runtime_unavailable"
        )
    return _PythonRuntimeV1(
        _BACKEND_PYTHON,
        (
            launcher.st_dev,
            launcher.st_ino,
            launcher.st_mtime_ns,
            launcher.st_ctime_ns,
        ),
        (
            target_info.st_dev,
            target_info.st_ino,
            target_info.st_size,
            target_info.st_mtime_ns,
            target_info.st_ctime_ns,
            target_info.st_uid,
            target_info.st_gid,
            stat.S_IMODE(target_info.st_mode),
        ),
    )


def _validate_strace_executable(path: Path) -> None:
    try:
        info = path.lstat()
    except OSError:
        raise M5CodexContainmentUnavailableV1(
            "m5_codex_containment_strace_unavailable"
        ) from None
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != 0
        or info.st_mode & 0o022
        or not os.access(path, os.X_OK)
    ):
        raise M5CodexContainmentUnavailableV1("m5_codex_containment_strace_unavailable")


def _default_codex_roots(owner_data_root: Path) -> tuple[Path, ...]:
    roots = [Path(pwd.getpwuid(os.getuid()).pw_dir) / ".codex"]
    configured = os.environ.get("CODEX_HOME")
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        candidate = Path(os.path.normpath(os.fspath(candidate)))
        if not _is_within(candidate, owner_data_root):
            roots.append(candidate)
    return tuple(dict.fromkeys(roots))


def _raise_walk_error(error: OSError) -> None:
    raise error


def _managed_profile_tree_digest(root: Path) -> str:
    """Digest bounded metadata enclosed by one exact owner-only root."""

    try:
        root_info = _private_directory(
            root,
            "m5_codex_containment_profile_tree_invalid",
        )
        root_identity = (root_info.st_dev, root_info.st_ino)
        records: list[dict[str, object]] = []
        entry_count = 0
        for current_raw, directory_names, file_names in os.walk(
            root,
            topdown=True,
            onerror=_raise_walk_error,
            followlinks=False,
        ):
            directory_names.sort(key=os.fsencode)
            file_names.sort(key=os.fsencode)
            current = Path(current_raw)
            for name in (*directory_names, *file_names):
                entry_count += 1
                if entry_count > 10_000:
                    raise OSError
                path = current / name
                relative = path.relative_to(root)
                encoded_relative = os.fsencode(relative)
                if not encoded_relative or len(encoded_relative) > 4096:
                    raise OSError
                metadata = path.lstat()
                is_directory = stat.S_ISDIR(metadata.st_mode)
                is_regular = stat.S_ISREG(metadata.st_mode)
                mode = stat.S_IMODE(metadata.st_mode)
                if (
                    stat.S_ISLNK(metadata.st_mode)
                    or (not is_directory and not is_regular)
                    or metadata.st_uid != os.getuid()
                    or metadata.st_dev != root_info.st_dev
                    or mode & 0o7000
                    or (is_directory and mode & 0o500 != 0o500)
                    or (is_regular and metadata.st_nlink != 1)
                ):
                    raise OSError
                records.append(
                    {
                        "path_digest": hashlib.sha256(encoded_relative).hexdigest(),
                        "kind": "directory" if is_directory else "file",
                        "device": metadata.st_dev,
                        "inode": metadata.st_ino,
                        "mode": mode,
                        "links": metadata.st_nlink,
                        "size": metadata.st_size,
                        "modified_ns": metadata.st_mtime_ns,
                        "changed_ns": metadata.st_ctime_ns,
                    }
                )
        current_root = root.lstat()
        if (
            (current_root.st_dev, current_root.st_ino) != root_identity
            or not stat.S_ISDIR(current_root.st_mode)
            or current_root.st_uid != os.getuid()
            or stat.S_IMODE(current_root.st_mode) != 0o700
        ):
            raise OSError
        return hashlib.sha256(
            _canonical_json(
                {
                    "schema": "agentmonitor.m5-codex-profile-tree.v1",
                    "root_device": root_info.st_dev,
                    "root_inode": root_info.st_ino,
                    "entries": records,
                }
            )
        ).hexdigest()
    except (OSError, RuntimeError, ValueError):
        raise M5CodexContainmentErrorV1(
            "m5_codex_containment_profile_tree_invalid"
        ) from None


def _inode_identity(info: os.stat_result) -> _InodeIdentityV1:
    return info.st_dev, info.st_ino


def _validate_private_channel(
    descriptor: int,
    *,
    expected_identity: _InodeIdentityV1 | None = None,
) -> _InodeIdentityV1:
    metadata = os.fstat(descriptor)
    identity = _inode_identity(metadata)
    if (
        not stat.S_ISFIFO(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_nlink != 1
        or (expected_identity is not None and identity != expected_identity)
    ):
        raise OSError
    return identity


def _open_private_channel() -> tuple[int, int]:
    """Create one owner-only anonymous inherited channel."""

    reader = -1
    writer = -1
    try:
        reader, writer = os.pipe2(os.O_CLOEXEC)
        identity = _validate_private_channel(reader)
        _validate_private_channel(writer, expected_identity=identity)
        return reader, writer
    except OSError:
        if reader >= 0:
            os.close(reader)
        if writer >= 0:
            os.close(writer)
        raise M5CodexContainmentUnavailableV1(
            "m5_codex_containment_private_channel_unavailable"
        ) from None


def _write_private_channel(descriptor: int, payload: bytes, *, maximum: int) -> None:
    """Write one bounded payload without creating a filesystem artifact."""

    try:
        if type(payload) is not bytes or not 1 <= len(payload) <= maximum:
            raise OSError
        identity = _validate_private_channel(descriptor)
        written = 0
        while written < len(payload):
            count = os.write(descriptor, payload[written:])
            if count <= 0:
                raise OSError
            written += count
        _validate_private_channel(descriptor, expected_identity=identity)
    except OSError:
        raise M5CodexContainmentErrorV1(
            "m5_codex_containment_private_channel_invalid"
        ) from None


def _read_private_channel(
    descriptor: int,
    *,
    maximum: int,
    minimum: int = 1,
) -> bytes:
    """Read one bounded channel through EOF and retain no pathname."""

    try:
        identity = _validate_private_channel(descriptor)
        payload = bytearray()
        while len(payload) <= maximum:
            chunk = os.read(descriptor, min(65_536, maximum + 1 - len(payload)))
            if not chunk:
                break
            payload.extend(chunk)
        _validate_private_channel(descriptor, expected_identity=identity)
        if not minimum <= len(payload) <= maximum:
            raise OSError
        return bytes(payload)
    except OSError:
        raise M5CodexContainmentErrorV1(
            "m5_codex_containment_private_channel_invalid"
        ) from None


def _write_and_close_private_channel(
    descriptor: int,
    payload: bytes,
    *,
    maximum: int,
) -> None:
    try:
        _write_private_channel(descriptor, payload, maximum=maximum)
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass


def _validate_private_directory_handle(
    path: Path,
    descriptor: int,
    *,
    expected_identity: _InodeIdentityV1 | None = None,
) -> _InodeIdentityV1:
    metadata = os.fstat(descriptor)
    path_metadata = path.lstat()
    identity = _inode_identity(metadata)
    if (
        not path.is_absolute()
        or path.resolve(strict=True) != path
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
        or _inode_identity(path_metadata) != identity
        or (expected_identity is not None and identity != expected_identity)
    ):
        raise OSError
    return identity


def _open_private_directory(
    path: Path, *, expected_identity: _InodeIdentityV1 | None = None
) -> tuple[int, _InodeIdentityV1]:
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        identity = _validate_private_directory_handle(
            path,
            descriptor,
            expected_identity=expected_identity,
        )
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor, identity


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _decode_json_object(payload: bytes) -> dict[str, object]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeError, ValueError):
        raise M5CodexContainmentErrorV1(
            "m5_codex_containment_private_channel_invalid"
        ) from None
    if type(value) is not dict:
        raise M5CodexContainmentErrorV1("m5_codex_containment_private_channel_invalid")
    return cast(dict[str, object], value)


def _decode_trace_string(value: str) -> str:
    if "\\" not in value:
        return value
    position = 0
    decoded: list[str] = []
    for match in _TRACE_ESCAPE.finditer(value):
        segment = value[position : match.start()]
        if "\\" in segment:
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        decoded.append(segment)
        token = match.group(0)[1:]
        if token == "\\":
            decoded.append("\\")
        elif token == '"':
            decoded.append('"')
        else:
            decoded.append(chr(int(token, 8)))
        position = match.end()
    tail = value[position:]
    if "\\" in tail:
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    decoded.append(tail)
    return "".join(decoded)


def _trace_records(trace: str) -> tuple[_TraceRecordV1, ...]:
    if type(trace) is not str or not trace:
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    records: list[_TraceRecordV1 | None] = []
    pending: dict[tuple[int, str], tuple[str, int]] = {}
    for line in trace.splitlines():
        match = _TRACE_LINE.fullmatch(line)
        if match is not None:
            records.append(
                _TraceRecordV1(
                    int(match.group("pid")),
                    match.group("call"),
                    match.group("arguments"),
                    match.group("result"),
                )
            )
            continue
        unfinished = _TRACE_UNFINISHED.fullmatch(line)
        if unfinished is not None:
            key = (int(unfinished.group("pid")), unfinished.group("call"))
            if key in pending:
                raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
            pending[key] = (unfinished.group("arguments"), len(records))
            records.append(None)
            continue
        resumed = _TRACE_RESUMED.fullmatch(line)
        if resumed is None:
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        key = (int(resumed.group("pid")), resumed.group("call"))
        pending_record = pending.pop(key, None)
        if pending_record is None:
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        first, index = pending_record
        records[index] = _TraceRecordV1(
            key[0],
            key[1],
            first + resumed.group("arguments"),
            resumed.group("result"),
        )
    if pending or any(record is None for record in records):
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    return tuple(cast(_TraceRecordV1, record) for record in records)


def _quoted_arguments(record: _TraceRecordV1) -> tuple[str, ...]:
    return tuple(
        _decode_trace_string(value) for value in _TRACE_QUOTED.findall(record.arguments)
    )


def _successful(record: _TraceRecordV1) -> bool:
    return not record.result.startswith("-1 ")


def _child_pid(record: _TraceRecordV1) -> int | None:
    if record.call not in _CHILD_CALLS or not _successful(record):
        return None
    match = re.match(r"([1-9][0-9]*)", record.result)
    return None if match is None else int(match.group(1))


def _operation_role(record: _TraceRecordV1) -> Literal["version", "app_server"]:
    quoted = _quoted_arguments(record)
    if "--version" in quoted:
        return "version"
    if "app-server" in quoted and "stdio://" in quoted:
        return "app_server"
    raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")


def _trace_paths(record: _TraceRecordV1, *, working_root: Path) -> tuple[Path, ...]:
    quoted = _quoted_arguments(record)
    if record.call in {"execve", "execveat"}:
        quoted = quoted[:1]
    relative_count = sum(
        1 for value in quoted if value and not Path(value).is_absolute()
    )
    required_dirfds = _DIRFD_COUNTS.get(record.call)
    if (
        relative_count
        and required_dirfds is not None
        and len(_TRACE_AT_FDCWD.findall(record.arguments)) < required_dirfds
    ):
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    candidates: list[Path] = []
    for value in quoted:
        if not value:
            continue
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = working_root / candidate
        candidates.append(Path(os.path.normpath(os.fspath(candidate))))
    if record.call in _OPEN_CALLS and _successful(record):
        match = _TRACE_RESULT_DESCRIPTOR.fullmatch(record.result)
        if match is None:
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        resolved = _decode_trace_string(match.group("path"))
        if resolved.endswith(" (deleted)"):
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        resolved_path = Path(resolved)
        if not resolved_path.is_absolute():
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        candidates.append(Path(os.path.normpath(os.fspath(resolved_path))))
    return tuple(dict.fromkeys(candidates))


def _trace_is_write(record: _TraceRecordV1) -> bool:
    return record.call in _WRITE_CALLS or any(
        flag in record.arguments for flag in _WRITE_FLAGS
    )


def _installation_release_root(executable: Path, default_root: Path) -> Path | None:
    try:
        relative = executable.relative_to(default_root)
    except ValueError:
        return None
    parts = relative.parts
    if (
        len(parts) != 6
        or parts[:3] != ("packages", "standalone", "releases")
        or parts[-2:] != ("bin", "codex")
    ):
        return None
    return default_root.joinpath(*parts[:4])


def evaluate_codex_trace_policy_v1(
    trace: str,
    *,
    provider_executable: Path,
    managed_profile_root: Path,
    default_codex_roots: tuple[Path, ...],
) -> M5CodexTraceSummaryV1:
    """Pure fail-closed policy over a bounded file/process syscall trace."""

    executable = _normalized_absolute(
        provider_executable, "m5_codex_containment_trace_invalid"
    )
    managed = _normalized_absolute(
        managed_profile_root, "m5_codex_containment_trace_invalid"
    )
    defaults = tuple(
        _normalized_absolute(root, "m5_codex_containment_trace_invalid")
        for root in default_codex_roots
    )
    if not defaults or len(set(defaults)) != len(defaults):
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    records = _trace_records(trace)

    provider_exec_roles: dict[int, Literal["version", "app_server"]] = {}
    execution_count = 0
    for record in records:
        if record.call not in {"execve", "execveat"} or not _successful(record):
            continue
        quoted = _quoted_arguments(record)
        if not quoted:
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        invoked = Path(os.path.normpath(quoted[0]))
        if invoked != executable:
            continue
        if record.pid in provider_exec_roles:
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        provider_exec_roles[record.pid] = _operation_role(record)
        execution_count += 1
    if (
        execution_count != 3
        or tuple(provider_exec_roles.values()).count("version") != 1
        or tuple(provider_exec_roles.values()).count("app_server") != 2
    ):
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")

    release_roots = {
        root: _installation_release_root(executable, root) for root in defaults
    }
    accesses = 0
    writes = 0
    default_accesses = 0
    default_writes = 0
    active_roles: dict[int, Literal["version", "app_server"]] = {}
    for record in records:
        exact_provider_exec = False
        if record.call in {"execve", "execveat"} and _successful(record):
            quoted = _quoted_arguments(record)
            if not quoted:
                raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
            invoked = Path(os.path.normpath(quoted[0]))
            if invoked == executable:
                if record.pid in active_roles:
                    raise M5CodexContainmentErrorV1(
                        "m5_codex_containment_trace_invalid"
                    )
                active_roles[record.pid] = provider_exec_roles[record.pid]
                exact_provider_exec = True
        paths = _trace_paths(record, working_root=managed)
        is_write = _trace_is_write(record)
        for candidate in paths:
            for default_root in defaults:
                if not _is_within(candidate, default_root):
                    continue
                if is_write:
                    default_writes += 1
                    continue
                release_root = release_roots[default_root]
                release_read = release_root is not None and _is_within(
                    candidate, release_root
                )
                release_ancestor_metadata = (
                    release_root is not None
                    and candidate in release_root.parents
                    and _is_within(candidate, default_root)
                    and record.call in _METADATA_CALLS
                )
                if not (release_read or release_ancestor_metadata):
                    default_accesses += 1
        role = active_roles.get(record.pid)
        if role is None:
            continue
        child = _child_pid(record)
        if child is not None:
            if child in active_roles:
                raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
            active_roles[child] = role
        if _successful(record) and record.call == "fchdir":
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_working_directory_escape"
            )
        if _successful(record) and record.call in _FD_ONLY_MUTATORS:
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_fd_write_unverifiable"
            )
        if _successful(record) and record.call in _LINK_CALLS:
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_link_operation_rejected"
            )
        if _successful(record) and record.call in _PATH_FOLLOWING_MUTATORS:
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_path_mutator_unverifiable"
            )
        if paths:
            accesses += 1
        if is_write:
            if not paths:
                raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
            writes += 1
            if role != "app_server" or any(
                not _is_within(path, managed) for path in paths
            ):
                raise M5CodexContainmentErrorV1("m5_codex_managed_profile_write_escape")
        if record.call == "chdir" and _successful(record):
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_working_directory_escape"
            )
        if record.call in _EXIT_CALLS and _successful(record):
            active_roles.pop(record.pid, None)
        if exact_provider_exec and record.pid not in provider_exec_roles:
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    if default_accesses or default_writes:
        raise M5CodexContainmentErrorV1("m5_codex_default_profile_access_detected")
    return M5CodexTraceSummaryV1(
        execution_count,
        accesses,
        writes,
        default_accesses,
        default_writes,
    )


def _driver_selection(descriptor: int) -> _SelectionV1:
    value = _decode_json_object(
        _read_private_channel(descriptor, maximum=_INPUT_LIMIT_BYTES)
    )
    expected = {
        "schema",
        "owner_data_root",
        "account_id",
        "managed_profiles_root",
        "managed_profile_root",
        "revision",
        "service_pid",
        "service_start_time_ticks",
    }
    if set(value) != expected or value.get("schema") != _INPUT_SCHEMA:
        raise M5CodexContainmentErrorV1("m5_codex_containment_private_channel_invalid")
    try:
        return _validate_selection(
            owner_data_root=Path(cast(str, value["owner_data_root"])),
            account_id=cast(str, value["account_id"]),
            managed_profiles_root=Path(cast(str, value["managed_profiles_root"])),
            managed_profile_root=Path(cast(str, value["managed_profile_root"])),
            revision=cast(str, value["revision"]),
            service_pid=cast(int, value["service_pid"]),
            service_start_time_ticks=cast(int, value["service_start_time_ticks"]),
        )
    except (KeyError, TypeError, ValueError):
        raise M5CodexContainmentErrorV1(
            "m5_codex_containment_private_channel_invalid"
        ) from None


def _write_driver_result(
    descriptor: int,
    *,
    state: Literal["passed", "unavailable", "failed"],
    identity_binding_digest: str | None = None,
    quota_bucket_count: int = 0,
    quota_window_count: int = 0,
) -> None:
    _write_private_channel(
        descriptor,
        _canonical_json(
            {
                "schema": _RESULT_SCHEMA,
                "state": state,
                "identity_operation_count": 1 if state == "passed" else 0,
                "quota_operation_count": 1 if state == "passed" else 0,
                "identity_binding_digest": identity_binding_digest,
                "quota_bucket_count": quota_bucket_count,
                "quota_window_count": quota_window_count,
            }
        ),
        maximum=_RESULT_LIMIT_BYTES,
    )


def _inherited_descriptor(name: str) -> int:
    raw = os.environ.get(name)
    if raw is None or re.fullmatch(r"[3-9][0-9]{0,5}", raw) is None:
        raise M5CodexContainmentErrorV1("m5_codex_containment_private_channel_invalid")
    descriptor = int(raw)
    try:
        os.fstat(descriptor)
    except OSError:
        raise M5CodexContainmentErrorV1(
            "m5_codex_containment_private_channel_invalid"
        ) from None
    return descriptor


def _driver_main() -> int:
    try:
        input_descriptor = _inherited_descriptor(_INPUT_FD_ENV)
        result_descriptor = _inherited_descriptor(_RESULT_FD_ENV)
    except M5CodexContainmentErrorV1:
        return 2
    try:
        selection = _driver_selection(input_descriptor)
        from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
            DatabaseRefV1,
        )
        from agentmonitor.adapters.persistence.registry.sqlite.repository import (
            RegistryRepositoryErrorV1,
            SqliteRegistryRepositoryV1,
        )
        from agentmonitor.adapters.providers.codex.authentication.identity import (
            CodexIdentityFailure,
            read_managed_profile_identity_v1,
        )
        from agentmonitor.adapters.providers.codex.installation import (
            CodexInstallationUnavailable,
            discover_default_installation,
        )
        from agentmonitor.adapters.providers.codex.subscription.source import (
            CodexRateLimitsFailure,
            collect_rate_limits_once_v1,
        )
        from agentmonitor.adapters.providers.codex.transport import (
            CodexAppServerFailure,
        )
        from agentmonitor.composition.codex_managed_connection import (
            managed_identity_matches_account_v1,
        )
        from agentmonitor.contracts.common_v1 import OpaqueIdV1

        try:
            installation = discover_default_installation()
            identity = read_managed_profile_identity_v1(
                installation,
                managed_profiles_root=selection.managed_profiles_root,
                managed_profile_root=selection.managed_profile_root,
            )
            if identity is None:
                raise M5CodexContainmentUnavailableV1(
                    "m5_codex_containment_provider_unavailable"
                )
            repository = SqliteRegistryRepositoryV1(
                DatabaseRefV1(
                    selection.owner_data_root / "agentmonitor.db",
                    selection.owner_data_root,
                )
            )
            if not managed_identity_matches_account_v1(
                repository,
                OpaqueIdV1(selection.account_id),
                identity,
            ):
                raise M5CodexContainmentErrorV1(
                    "m5_codex_containment_identity_mismatch"
                )
            quota = collect_rate_limits_once_v1(
                installation,
                managed_profiles_root=selection.managed_profiles_root,
                managed_profile_root=selection.managed_profile_root,
                expected_identity_fingerprint=identity.fingerprint,
            )
        except CodexInstallationUnavailable as error:
            code = str(error)
            unavailable = code in {
                "codex_platform_unverified",
                "codex_executable_unavailable",
                "codex_version_unavailable",
                "codex_version_deadline_exceeded",
            }
            if unavailable:
                raise M5CodexContainmentUnavailableV1(
                    "m5_codex_containment_provider_unavailable"
                ) from None
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_operation_failed"
            ) from None
        except CodexAppServerFailure as error:
            unavailable = error.code in {
                "codex_app_server_deadline_exceeded",
                "codex_app_server_unavailable",
                "codex_managed_authentication_required",
                "codex_managed_profile_unavailable",
            }
            if unavailable:
                raise M5CodexContainmentUnavailableV1(
                    "m5_codex_containment_provider_unavailable"
                ) from None
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_operation_failed"
            ) from None
        except RegistryRepositoryErrorV1:
            raise M5CodexContainmentUnavailableV1(
                "m5_codex_containment_registry_unavailable"
            ) from None
        except (CodexIdentityFailure, CodexRateLimitsFailure):
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_operation_failed"
            ) from None

        windows = sum(1 + (bucket.secondary is not None) for bucket in quota.buckets)
        identity_binding_digest = hashlib.sha256(
            _canonical_json(
                {
                    "schema": "agentmonitor.m5-codex-identity-binding.v1",
                    "account_id": selection.account_id,
                    "identity_fingerprint": identity.fingerprint,
                }
            )
        ).hexdigest()
        _write_driver_result(
            result_descriptor,
            state="passed",
            identity_binding_digest=identity_binding_digest,
            quota_bucket_count=len(quota.buckets),
            quota_window_count=windows,
        )
        return 0
    except M5CodexContainmentUnavailableV1:
        try:
            _write_driver_result(result_descriptor, state="unavailable")
        except M5CodexContainmentErrorV1:
            pass
        return 3
    except (ImportError, OSError, RuntimeError, TypeError, ValueError):
        try:
            _write_driver_result(result_descriptor, state="failed")
        except M5CodexContainmentErrorV1:
            pass
        return 2


def _validated_driver_result(
    payload: bytes,
    returncode: int,
) -> dict[str, object]:
    value = _decode_json_object(payload)
    expected = {
        "schema",
        "state",
        "identity_operation_count",
        "quota_operation_count",
        "identity_binding_digest",
        "quota_bucket_count",
        "quota_window_count",
    }
    if set(value) != expected or value.get("schema") != _RESULT_SCHEMA:
        raise M5CodexContainmentErrorV1("m5_codex_containment_result_invalid")
    state = value.get("state")
    identity_binding_digest = value.get("identity_binding_digest")
    counts = tuple(
        value.get(key)
        for key in (
            "identity_operation_count",
            "quota_operation_count",
            "quota_bucket_count",
            "quota_window_count",
        )
    )
    if not all(type(item) is int and item >= 0 for item in counts):
        raise M5CodexContainmentErrorV1("m5_codex_containment_result_invalid")
    if returncode == 3 and state == "unavailable" and identity_binding_digest is None:
        raise M5CodexContainmentUnavailableV1(
            "m5_codex_containment_provider_unavailable"
        )
    if (
        returncode != 0
        or state != "passed"
        or counts[:2] != (1, 1)
        or type(identity_binding_digest) is not str
        or _SHA256.fullmatch(identity_binding_digest) is None
    ):
        raise M5CodexContainmentErrorV1("m5_codex_containment_operation_failed")
    if cast(int, counts[2]) < 1 or cast(int, counts[3]) < 1:
        raise M5CodexContainmentErrorV1("m5_codex_containment_result_invalid")
    return value


def _start_traced_driver(
    *,
    working_directory: Path,
    working_directory_identity: _InodeIdentityV1,
    input_descriptor: int,
    result_descriptor: int,
    trace_descriptor: int,
    executable: _ExecutableV1,
    python_runtime: _PythonRuntimeV1,
    default_roots: tuple[Path, ...],
) -> subprocess.Popen[bytes]:
    environment = {
        _INPUT_FD_ENV: str(input_descriptor),
        _RESULT_FD_ENV: str(result_descriptor),
        "CODEX_HOME": os.fspath(default_roots[0]),
        "HOME": pwd.getpwuid(os.getuid()).pw_dir,
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "NO_COLOR": "1",
        "PATH": os.pathsep.join(
            (os.fspath(executable.launcher_directory), "/usr/bin", "/bin")
        ),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": os.pathsep.join((os.fspath(ROOT), os.fspath(BACKEND_SOURCE))),
    }
    command = [
        os.fspath(_STRACE),
        "--kill-on-exit",
        "-f",
        "-yy",
        "-qq",
        "-s",
        "4096",
        "-e",
        "trace=%file,process,fchdir,fchmod,fchown,ftruncate,fallocate",
        "-e",
        "signal=none",
        "-o",
        f"/proc/self/fd/{trace_descriptor}",
        "--",
        os.fspath(python_runtime.path),
        "-m",
        "tools.automation.implementations.m5_codex_containment",
        "--driver",
    ]
    directory_descriptor, _identity = _open_private_directory(
        working_directory,
        expected_identity=working_directory_identity,
    )
    try:
        return _start_containment_process(
            command,
            cwd=Path(f"/proc/self/fd/{directory_descriptor}"),
            environment=environment,
            pass_fds=(
                input_descriptor,
                result_descriptor,
                trace_descriptor,
                directory_descriptor,
            ),
        )
    finally:
        os.close(directory_descriptor)


def _start_containment_process(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    pass_fds: tuple[int, ...],
) -> subprocess.Popen[bytes]:
    try:
        return subprocess.Popen(
            command,
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            pass_fds=pass_fds,
            shell=False,
            start_new_session=True,
        )
    except OSError:
        raise M5CodexContainmentUnavailableV1(
            "m5_codex_containment_driver_unavailable"
        ) from None


def _wait_driver(process: subprocess.Popen[bytes]) -> int:
    try:
        return process.wait(timeout=_DRIVER_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            pass
        try:
            process.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            pass
        raise M5CodexContainmentUnavailableV1(
            "m5_codex_containment_driver_deadline_exceeded"
        ) from None


def _collect_driver_channels(
    process: subprocess.Popen[bytes],
    *,
    input_descriptor: int,
    input_payload: bytes,
    result_descriptor: int,
    trace_descriptor: int,
) -> tuple[int, bytes, bytes]:
    """Drain both bounded anonymous outputs while the traced driver runs."""

    with ThreadPoolExecutor(max_workers=3) as executor:
        input_future = executor.submit(
            _write_and_close_private_channel,
            input_descriptor,
            input_payload,
            maximum=_INPUT_LIMIT_BYTES,
        )
        result_future = executor.submit(
            _read_private_channel,
            result_descriptor,
            maximum=_RESULT_LIMIT_BYTES,
        )
        trace_future = executor.submit(
            _read_private_channel,
            trace_descriptor,
            maximum=_TRACE_LIMIT_BYTES,
        )
        returncode = _wait_driver(process)
        try:
            input_future.result(timeout=5)
            result = result_future.result(timeout=5)
            trace = trace_future.result(timeout=5)
        except TimeoutError:
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_private_channel_invalid"
            ) from None
    return returncode, result, trace


def verify_codex_managed_profile_containment_v1(
    *,
    owner_data_root: Path,
    account_id: str,
    managed_profiles_root: Path,
    managed_profile_root: Path,
    revision: str,
    service_pid: int,
    service_start_time_ticks: int,
) -> M5CodexContainmentEvidenceV1:
    """Run real production identity/quota calls and return digest-only evidence."""

    selection = _validate_selection(
        owner_data_root=owner_data_root,
        account_id=account_id,
        managed_profiles_root=managed_profiles_root,
        managed_profile_root=managed_profile_root,
        revision=revision,
        service_pid=service_pid,
        service_start_time_ticks=service_start_time_ticks,
    )
    _validate_strace_executable(_STRACE)
    executable = _resolve_executable()
    python_runtime = _resolve_python_runtime()
    default_roots = _default_codex_roots(selection.owner_data_root)
    owner_info = _private_directory(
        selection.owner_data_root,
        "m5_codex_containment_selection_invalid",
    )
    owner_identity = _inode_identity(owner_info)
    profiles_identity = _inode_identity(
        _private_directory(
            selection.managed_profiles_root,
            "m5_codex_containment_selection_invalid",
        )
    )
    profile_identity = _inode_identity(
        _private_directory(
            selection.managed_profile_root,
            "m5_codex_containment_selection_invalid",
        )
    )
    profile_tree_before = _managed_profile_tree_digest(selection.managed_profile_root)
    selection_payload = _canonical_json(
        {
            "schema": _INPUT_SCHEMA,
            "owner_data_root": os.fspath(selection.owner_data_root),
            "account_id": selection.account_id,
            "managed_profiles_root": os.fspath(selection.managed_profiles_root),
            "managed_profile_root": os.fspath(selection.managed_profile_root),
            "revision": selection.revision,
            "service_pid": selection.service_pid,
            "service_start_time_ticks": selection.service_start_time_ticks,
        }
    )
    input_reader = -1
    input_writer = -1
    result_reader = -1
    result_writer = -1
    trace_reader = -1
    trace_writer = -1
    try:
        input_reader, input_writer = _open_private_channel()
        result_reader, result_writer = _open_private_channel()
        trace_reader, trace_writer = _open_private_channel()
        process = _start_traced_driver(
            working_directory=selection.managed_profile_root,
            working_directory_identity=profile_identity,
            input_descriptor=input_reader,
            result_descriptor=result_writer,
            trace_descriptor=trace_writer,
            executable=executable,
            python_runtime=python_runtime,
            default_roots=default_roots,
        )
        os.close(input_reader)
        input_reader = -1
        os.close(result_writer)
        result_writer = -1
        os.close(trace_writer)
        trace_writer = -1
        owned_input_writer = input_writer
        input_writer = -1
        returncode, result_payload, trace_payload = _collect_driver_channels(
            process,
            input_descriptor=owned_input_writer,
            input_payload=selection_payload,
            result_descriptor=result_reader,
            trace_descriptor=trace_reader,
        )
        result = _validated_driver_result(result_payload, returncode)
        try:
            trace = trace_payload.decode("utf-8")
        except UnicodeError:
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_trace_invalid"
            ) from None
        summary = evaluate_codex_trace_policy_v1(
            trace,
            provider_executable=executable.path,
            managed_profile_root=selection.managed_profile_root,
            default_codex_roots=default_roots,
        )
        profile_tree_after = _managed_profile_tree_digest(
            selection.managed_profile_root
        )
        if _process_start_ticks(selection.service_pid) != (
            selection.service_start_time_ticks
        ):
            raise M5CodexContainmentUnavailableV1(
                "m5_codex_containment_service_mismatch"
            )
        if (
            owner_identity
            != _inode_identity(
                _private_directory(
                    selection.owner_data_root,
                    "m5_codex_containment_selection_changed",
                )
            )
            or profiles_identity
            != _inode_identity(
                _private_directory(
                    selection.managed_profiles_root,
                    "m5_codex_containment_selection_changed",
                )
            )
            or profile_identity
            != _inode_identity(
                _private_directory(
                    selection.managed_profile_root,
                    "m5_codex_containment_selection_changed",
                )
            )
        ):
            raise M5CodexContainmentErrorV1("m5_codex_containment_selection_changed")
        if _executable_identity(executable.path) != executable.identity:
            raise M5CodexContainmentErrorV1("m5_codex_containment_executable_changed")
        try:
            current_runtime = _resolve_python_runtime()
        except M5CodexContainmentUnavailableV1:
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_runtime_changed"
            ) from None
        if current_runtime != python_runtime:
            raise M5CodexContainmentErrorV1("m5_codex_containment_runtime_changed")
        binding = {
            "schema": _DIGEST_SCHEMA,
            "revision": selection.revision,
            "service_pid": selection.service_pid,
            "service_start_time_ticks": selection.service_start_time_ticks,
            "account_id": selection.account_id,
            "owner_data_root": os.fspath(selection.owner_data_root),
            "managed_profile_root": os.fspath(selection.managed_profile_root),
            "owner_identity": owner_identity,
            "managed_profiles_identity": profiles_identity,
            "managed_profile_identity": profile_identity,
            "identity_binding_digest": result["identity_binding_digest"],
            "profile_tree_before_digest": profile_tree_before,
            "profile_tree_after_digest": profile_tree_after,
            "executable_identity": executable.identity,
            "runtime_launcher_identity": python_runtime.launcher_identity,
            "runtime_target_identity": python_runtime.target_identity,
            "trace_digest": hashlib.sha256(trace_payload).hexdigest(),
            "identity_operation_count": result["identity_operation_count"],
            "quota_operation_count": result["quota_operation_count"],
            "quota_bucket_count": result["quota_bucket_count"],
            "quota_window_count": result["quota_window_count"],
            "provider_execution_count": summary.provider_execution_count,
            "provider_access_count": summary.provider_access_count,
            "provider_write_count": summary.provider_write_count,
            "default_profile_access_count": summary.default_profile_access_count,
            "default_profile_write_count": summary.default_profile_write_count,
        }
        return M5CodexContainmentEvidenceV1(
            evidence_digest=hashlib.sha256(_canonical_json(binding)).hexdigest(),
            provider_access_count=summary.provider_access_count,
            provider_write_count=summary.provider_write_count,
            default_profile_access_count=summary.default_profile_access_count,
            default_profile_write_count=summary.default_profile_write_count,
        )
    finally:
        for descriptor in (
            input_reader,
            input_writer,
            result_reader,
            result_writer,
            trace_reader,
            trace_writer,
        ):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass


if __name__ == "__main__":
    if sys.argv == [sys.argv[0], "--driver"]:
        raise SystemExit(_driver_main())
    raise SystemExit(2)

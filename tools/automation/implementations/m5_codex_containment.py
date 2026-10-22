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
import select
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import CancelledError, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal, cast

if TYPE_CHECKING:
    from agentmonitor.adapters.providers.codex.installation import (
        CodexInstallationV1,
    )

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
_TRACE_STRING_TOKEN_V1 = r'"(?:[^"\\]|\\(?:[0-7]{3}|\\|\"))*"'
_TRACE_EXECVE_ARGUMENTS_V1 = re.compile(
    rf"^(?P<path>{_TRACE_STRING_TOKEN_V1}), "
    rf"\[(?P<argv>{_TRACE_STRING_TOKEN_V1}"
    rf"(?:, {_TRACE_STRING_TOKEN_V1})*)\], .+$"
)
_TRACE_RESULT_DESCRIPTOR = re.compile(r"^[0-9]+<(?P<path>.*)>$")
_TRACE_AT_FDCWD = re.compile(r"(?:^|,\s*)AT_FDCWD(?:<[^>]*>)?(?=,)")
_TRACE_CHMOD_ARGUMENTS_V1 = re.compile(
    r'^"(?P<path>(?:[^"\\]|\\(?:[0-7]{3}|\\|"))+)", 0700$'
)
_TRACE_CHDIR_ARGUMENTS_V1 = re.compile(rf"^(?P<path>{_TRACE_STRING_TOKEN_V1})$")
_TRACE_FAILED_RESULT_V1 = re.compile(r"^-1 [A-Z][A-Z0-9_]* \(.+\)$")
_TRACE_FTRUNCATE_ARGUMENTS_V1 = re.compile(
    r"^(?P<descriptor>(?:[3-9]|[1-9][0-9]{1,5}))"
    r"<(?P<path>[^<>\\\x00\r\n]+)>, "
    r"(?P<length>0|[1-9][0-9]{0,18})$"
)
_TRACE_FTRUNCATE_MISSING_PATH_V1 = re.compile(
    r"^(?P<descriptor>(?:[3-9]|[1-9][0-9]{1,5})), "
    r"(?P<length>0|[1-9][0-9]{0,18})$"
)
_TRACE_FTRUNCATE_FAILED_RESULT_V1 = re.compile(
    r"^-1 [A-Z][A-Z0-9_]{0,31} \([^()<>\\\x00-\x1f\x7f]{1,160}\)$"
)
_TRACE_DIRFD_ANNOTATION_PATH_V1 = r"[^<>\\\x00-\x1f\x7f]+"
_TRACE_UNLINKAT_ARGUMENTS_V1 = re.compile(
    rf"^(?P<dirfd>"
    rf"(?:AT_FDCWD|(?:0|[1-9][0-9]{{0,5}}))"
    rf"(?:<(?P<annotation>{_TRACE_DIRFD_ANNOTATION_PATH_V1})>)?"
    rf"), (?P<path>{_TRACE_STRING_TOKEN_V1}), "
    rf"(?P<flags>0|AT_REMOVEDIR)$"
)
_TRACE_SYMLINK_ARGUMENTS_V1 = re.compile(
    rf"^(?P<payload>{_TRACE_STRING_TOKEN_V1}), "
    rf"(?P<linkpath>{_TRACE_STRING_TOKEN_V1})$"
)
_ARG0_SESSION_V1 = re.compile(r"codex-arg0[A-Za-z0-9]{6}\Z")
_ARG0_ALIASES_V1: Final = (
    "apply_patch",
    "applypatch",
    "codex-linux-sandbox",
    "codex-execve-wrapper",
)
_TRACE_NUMERIC_DIRFD_V1 = re.compile(r"(?:[3-9]|[1-9][0-9]{1,5})\Z")
_TRACE_NONNEGATIVE_RESULT_V1 = re.compile(r"^(?:0|[1-9][0-9]*)$")
_TRACE_DESCRIPTOR_RESULT_V1 = re.compile(r"^(?:0|[1-9][0-9]*)<[^>\r\n]+>$")
_TRACE_FLAGS_V1 = re.compile(r"(?:^|[{,]\s*)flags=(?P<flags>[^,}]+)")
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
        "fremovexattr",
        "fsetxattr",
        "futimesat",
        "lchown",
        "link",
        "linkat",
        "lremovexattr",
        "lsetxattr",
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
        "removexattr",
        "rmdir",
        "setxattr",
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
    "futimesat": 1,
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
_FD_ONLY_MUTATORS = frozenset(
    {
        "fallocate",
        "fchmod",
        "fchown",
        "fremovexattr",
        "fsetxattr",
        "ftruncate",
    }
)
_PATH_FOLLOWING_MUTATORS = frozenset(
    {
        "chmod",
        "chown",
        "fchmodat",
        "fchmodat2",
        "fchownat",
        "futimesat",
        "lchown",
        "lremovexattr",
        "lsetxattr",
        "mount",
        "move_mount",
        "open_tree",
        "pivot_root",
        "removexattr",
        "setxattr",
        "truncate",
        "umount",
        "umount2",
        "utime",
        "utimensat",
        "utimes",
    }
)
_NAMESPACE_CALLS = frozenset(
    {
        "chroot",
        "fsconfig",
        "fsmount",
        "fsopen",
        "fspick",
        "mount",
        "mount_setattr",
        "move_mount",
        "open_tree",
        "pivot_root",
        "setns",
        "umount",
        "umount2",
    }
)
_TARGET_NAMESPACE_CALLS = frozenset(
    {
        "rename",
        "renameat",
        "renameat2",
        "rmdir",
        "unlink",
        "unlinkat",
    }
)
_RAW_GLOBAL_CALLS = frozenset(
    {
        "fremovexattr",
        "fsetxattr",
        "ioctl",
        "io_uring_enter",
        "io_uring_register",
        "io_uring_setup",
    }
)
_STRACE_SELECTOR_V1: Final = (
    "trace=%file,%process,chdir,fchdir,fchmod,fchown,ftruncate,fallocate,"
    "fsetxattr,fremovexattr,ioctl,io_uring_setup,io_uring_enter,"
    "io_uring_register,clone,clone3,setns,unshare,chroot,pivot_root,mount,"
    "umount,umount2,open_tree,move_mount,fsopen,fsconfig,fsmount,fspick,"
    "mount_setattr"
)
_STRACE_RAW_V1: Final = (
    "raw=fsetxattr,fremovexattr,ioctl,io_uring_setup,io_uring_enter,io_uring_register"
)
_TRUE = Path("/usr/bin/true")
_CLONE_FS: Final = 0x00000200
_CLONE_NEWNS: Final = 0x00020000
_CLONE_THREAD: Final = 0x00010000
_CLONE_UNTRACED: Final = 0x00800000
_PROVIDER_APP_SERVER_ARGUMENTS: Final = (
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
)
_DRIVER_TIMEOUT_SECONDS: Final = 90
_CHANNEL_SETTLEMENT_SECONDS: Final = 5.0
_CHANNEL_POLL_SECONDS: Final = 0.01
_PROC_MOUNTINFO_LIMIT_BYTES: Final = 1024 * 1024
_PROC_MOUNTINFO_MAX_ROWS: Final = 4096
_PROC_MOUNT_FIELD_LIMIT_BYTES: Final = 4096
_PROC_MOUNTINFO_PSEUDO_ROOT_V1 = re.compile(
    rb"[a-z][a-z0-9_-]{0,31}:\[[1-9][0-9]{0,19}\]\Z"
)


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
    invoked_at: int
    completed_at: int


@dataclass(frozen=True, slots=True)
class _SelectionV1:
    owner_data_root: Path
    profiles_root: Path
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


@dataclass(frozen=True, slots=True)
class _DirectoryIdentityV1:
    relative_parts: tuple[str, ...]
    device: int
    inode: int
    owner_uid: int
    mode: int
    changed_ns: int


@dataclass(frozen=True, slots=True)
class _ProfileTreeSnapshotV1:
    digest: str
    directories: tuple[_DirectoryIdentityV1, ...]


@dataclass(frozen=True, slots=True)
class _MountRecordV1:
    mount_id: int
    parent_id: int
    device_major: int
    device_minor: int
    root: Path
    mount_point: Path


@dataclass(frozen=True, slots=True)
class _MountInfoViewV1:
    covering_mount: _MountRecordV1


@dataclass(frozen=True, slots=True)
class _MountTopologySnapshotV1:
    namespace_identity: _InodeIdentityV1
    covering_mount: _MountRecordV1


@dataclass(slots=True)
class _OwnedDriverProcessV1:
    process: subprocess.Popen[bytes]
    pidfd: int
    start_time_ticks: int


@dataclass(frozen=True, slots=True)
class _OperationV1:
    sequence: int
    kind: Literal["version", "identity", "quota"]
    root_pid: int


@dataclass(frozen=True, slots=True)
class _Arg0CreationV1:
    operation: _OperationV1
    record_index: int
    path: Path
    session: Path
    alias: str


@dataclass(frozen=True, slots=True)
class _TraceEvaluationV1:
    summary: M5CodexTraceSummaryV1
    admitted_chmod_relative_parts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _InputChannelOutcomeV1:
    state: Literal["complete", "invalid", "late"]


@dataclass(frozen=True, slots=True)
class _OutputChannelOutcomeV1:
    state: Literal["payload", "empty", "invalid", "late"]
    payload: bytes | None = None


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


def _mount_topology_error() -> M5CodexContainmentErrorV1:
    return M5CodexContainmentErrorV1("m5_codex_containment_mount_topology_unverifiable")


def _decode_mountinfo_path_v1(
    value: bytes,
    *,
    require_absolute: bool = True,
) -> Path:
    if type(value) is not bytes or not 1 <= len(value) <= _PROC_MOUNT_FIELD_LIMIT_BYTES:
        raise ValueError
    decoded = bytearray()
    position = 0
    escapes = {
        b"040": 0x20,
        b"011": 0x09,
        b"012": 0x0A,
        b"134": 0x5C,
    }
    while position < len(value):
        current = value[position]
        if current != 0x5C:
            decoded.append(current)
            position += 1
            continue
        token = value[position + 1 : position + 4]
        replacement = escapes.get(token)
        if replacement is None:
            raise ValueError
        decoded.append(replacement)
        position += 4
    raw = bytes(decoded)
    if any(member < 0x20 or member == 0x7F for member in raw):
        raise ValueError
    if require_absolute and (
        not raw.startswith(b"/")
        or raw.startswith(b"//")
        or os.path.normpath(raw) != raw
    ):
        raise ValueError
    return Path(os.fsdecode(raw))


def _canonical_mount_integer_v1(value: bytes, *, positive: bool) -> int:
    expression = rb"[1-9][0-9]*" if positive else rb"(?:0|[1-9][0-9]*)"
    if re.fullmatch(expression, value) is None:
        raise ValueError
    parsed = int(value)
    if parsed > 2**31 - 1:
        raise ValueError
    return parsed


def _decode_mountinfo_root_v1(value: bytes) -> Path:
    """Accept canonical paths and bounded kernel namespace pseudo roots only."""

    try:
        return _decode_mountinfo_path_v1(value)
    except ValueError:
        pseudo_root = _decode_mountinfo_path_v1(value, require_absolute=False)
        if _PROC_MOUNTINFO_PSEUDO_ROOT_V1.fullmatch(os.fsencode(pseudo_root)) is None:
            raise ValueError from None
        return pseudo_root


def _parse_mountinfo_v1(
    payload: bytes,
    *,
    managed_profile_root: Path,
) -> _MountInfoViewV1:
    """Parse one bounded Linux mount table and exclude profile aliases."""

    try:
        managed = _normalized_absolute(
            managed_profile_root,
            "m5_codex_containment_mount_topology_unverifiable",
        )
        if (
            type(payload) is not bytes
            or not 1 <= len(payload) <= _PROC_MOUNTINFO_LIMIT_BYTES
            or not payload.endswith(b"\n")
            or b"\r" in payload
        ):
            raise ValueError
        lines = payload.splitlines()
        if not 1 <= len(lines) <= _PROC_MOUNTINFO_MAX_ROWS:
            raise ValueError
        records: list[_MountRecordV1] = []
        mount_ids: set[int] = set()
        for line in lines:
            if not line or any(member < 0x20 or member == 0x7F for member in line):
                raise ValueError
            fields = line.split(b" ")
            if any(not field for field in fields) or fields.count(b"-") != 1:
                raise ValueError
            separator = fields.index(b"-")
            before = fields[:separator]
            after = fields[separator + 1 :]
            if len(before) < 6 or len(after) != 3:
                raise ValueError
            mount_id = _canonical_mount_integer_v1(before[0], positive=True)
            # The initial mount namespace can expose parent ID 0 for its
            # hidden initramfs parent.  Preserve that canonical Linux value.
            parent_id = _canonical_mount_integer_v1(before[1], positive=False)
            device = before[2].split(b":")
            if len(device) != 2:
                raise ValueError
            major = _canonical_mount_integer_v1(device[0], positive=False)
            minor = _canonical_mount_integer_v1(device[1], positive=False)
            root = _decode_mountinfo_root_v1(before[3])
            mount_point = _decode_mountinfo_path_v1(before[4])
            if (
                (not root.is_absolute() and after[0] != b"nsfs")
                or mount_id in mount_ids
                or any(
                    not 1 <= len(field) <= _PROC_MOUNT_FIELD_LIMIT_BYTES
                    for field in (*before[5:], *after)
                )
            ):
                raise ValueError
            mount_ids.add(mount_id)
            records.append(
                _MountRecordV1(
                    mount_id,
                    parent_id,
                    major,
                    minor,
                    root,
                    mount_point,
                )
            )
        covering: list[_MountRecordV1] = []
        for record in records:
            point = record.mount_point
            if point == managed or managed in point.parents:
                raise ValueError
            if point in managed.parents:
                covering.append(record)
        if not covering:
            raise ValueError
        deepest = max(len(record.mount_point.parts) for record in covering)
        candidates = tuple(
            record for record in covering if len(record.mount_point.parts) == deepest
        )
        if len(candidates) != 1:
            raise ValueError
        selected = candidates[0]
        if not selected.root.is_absolute() or os.path.normpath(
            os.fspath(selected.root)
        ) != os.fspath(selected.root):
            raise ValueError
        return _MountInfoViewV1(selected)
    except (M5CodexContainmentErrorV1, OSError, TypeError, ValueError):
        raise _mount_topology_error() from None


def _read_bounded_proc_file_v1(path: Path) -> bytes:
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise OSError
        chunks: list[bytes] = []
        total = 0
        while total <= _PROC_MOUNTINFO_LIMIT_BYTES:
            chunk = os.read(
                descriptor,
                min(64 * 1024, _PROC_MOUNTINFO_LIMIT_BYTES + 1 - total),
            )
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
        if not 1 <= total <= _PROC_MOUNTINFO_LIMIT_BYTES:
            raise OSError
        return b"".join(chunks)
    except OSError:
        raise _mount_topology_error() from None
    finally:
        if descriptor >= 0:
            active_error = sys.exc_info()[0] is not None
            try:
                os.close(descriptor)
            except OSError:
                if not active_error:
                    raise _mount_topology_error() from None


def _mount_namespace_identity_v1(path: Path) -> _InodeIdentityV1:
    try:
        metadata = path.stat()
        identity = _inode_identity(metadata)
        if identity[0] <= 0 or identity[1] <= 0:
            raise OSError
        return identity
    except OSError:
        raise _mount_topology_error() from None


def _mount_topology_snapshot_v1(
    managed_profile_root: Path,
    *,
    process_id: int | None = None,
    expected_process_start_time_ticks: int | None = None,
) -> _MountTopologySnapshotV1:
    """Capture the selected root's real mount view without retaining its table."""

    pid = os.getpid() if process_id is None else process_id
    if type(pid) is not int or not 1 <= pid <= 2**31 - 1:
        raise _mount_topology_error()
    if expected_process_start_time_ticks is not None and (
        type(expected_process_start_time_ticks) is not int
        or not 1 <= expected_process_start_time_ticks <= 2**63 - 1
    ):
        raise _mount_topology_error()
    process_root = Path("/proc") / str(pid)
    try:
        if process_root.stat().st_uid != os.getuid():
            raise OSError
    except OSError:
        raise _mount_topology_error() from None
    try:
        start_ticks_before = _process_start_ticks(pid)
    except M5CodexContainmentUnavailableV1:
        raise _mount_topology_error() from None
    if (
        expected_process_start_time_ticks is not None
        and start_ticks_before != expected_process_start_time_ticks
    ):
        raise _mount_topology_error()
    namespace_path = process_root / "ns" / "mnt"
    before_identity = _mount_namespace_identity_v1(namespace_path)
    payload = _read_bounded_proc_file_v1(process_root / "mountinfo")
    after_identity = _mount_namespace_identity_v1(namespace_path)
    try:
        start_ticks_after = _process_start_ticks(pid)
    except M5CodexContainmentUnavailableV1:
        raise _mount_topology_error() from None
    if (
        before_identity != after_identity
        or start_ticks_before != start_ticks_after
        or (
            expected_process_start_time_ticks is not None
            and start_ticks_after != expected_process_start_time_ticks
        )
    ):
        raise _mount_topology_error()
    view = _parse_mountinfo_v1(
        payload,
        managed_profile_root=managed_profile_root,
    )
    return _MountTopologySnapshotV1(before_identity, view.covering_mount)


def _require_same_mount_topology_v1(
    expected: _MountTopologySnapshotV1,
    observed: _MountTopologySnapshotV1,
) -> None:
    if (
        type(expected) is not _MountTopologySnapshotV1
        or type(observed) is not _MountTopologySnapshotV1
        or observed != expected
    ):
        raise _mount_topology_error()


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
    profiles_root = owner / "profiles"
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
    _private_directory(profiles_root, "m5_codex_containment_selection_invalid")
    _private_directory(profiles, "m5_codex_containment_selection_invalid")
    _private_directory(profile, "m5_codex_containment_selection_invalid")
    observed_ticks = _process_start_ticks(service_pid)
    if observed_ticks != service_start_time_ticks:
        raise M5CodexContainmentUnavailableV1("m5_codex_containment_service_mismatch")
    return _SelectionV1(
        owner,
        profiles_root,
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


def _validate_root_executable(path: Path, code: str) -> None:
    try:
        info = path.lstat()
    except OSError:
        raise M5CodexContainmentUnavailableV1(code) from None
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != 0
        or info.st_mode & 0o022
        or not os.access(path, os.X_OK)
    ):
        raise M5CodexContainmentUnavailableV1(code)


def _validate_strace_selector_v1() -> None:
    """Prove the installed root-owned tracer accepts the exact selector."""

    _validate_strace_executable(_STRACE)
    _validate_root_executable(
        _TRUE,
        "m5_codex_containment_trace_selector_unavailable",
    )
    try:
        process = subprocess.Popen(
            [
                os.fspath(_STRACE),
                "--kill-on-exit",
                "-f",
                "-qq",
                "-e",
                _STRACE_SELECTOR_V1,
                "-e",
                _STRACE_RAW_V1,
                "-e",
                "signal=none",
                "-o",
                os.devnull,
                "--",
                os.fspath(_TRUE),
            ],
            cwd=Path("/"),
            env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PATH": "/usr/bin:/bin"},
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
            start_new_session=True,
        )
    except OSError:
        raise M5CodexContainmentUnavailableV1(
            "m5_codex_containment_trace_selector_unavailable"
        ) from None
    try:
        returncode = process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            pass
        try:
            process.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            pass
        raise M5CodexContainmentUnavailableV1(
            "m5_codex_containment_trace_selector_unavailable"
        ) from None
    if returncode != 0:
        raise M5CodexContainmentUnavailableV1(
            "m5_codex_containment_trace_selector_unavailable"
        )


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


def _directory_identity(
    relative_parts: tuple[str, ...], metadata: os.stat_result
) -> _DirectoryIdentityV1:
    return _DirectoryIdentityV1(
        relative_parts=relative_parts,
        device=metadata.st_dev,
        inode=metadata.st_ino,
        owner_uid=metadata.st_uid,
        mode=stat.S_IMODE(metadata.st_mode),
        changed_ns=metadata.st_ctime_ns,
    )


def _managed_profile_tree_snapshot(
    root: Path,
    *,
    expected_root_identity: _InodeIdentityV1 | None = None,
) -> _ProfileTreeSnapshotV1:
    """Capture bounded digest metadata and private directory identities."""

    try:
        root_info = _private_directory(
            root,
            "m5_codex_containment_profile_tree_invalid",
        )
        root_identity = (root_info.st_dev, root_info.st_ino)
        if (
            expected_root_identity is not None
            and root_identity != expected_root_identity
        ):
            raise OSError
        records: list[dict[str, object]] = []
        directories = [_directory_identity((), root_info)]
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
                if is_directory:
                    directories.append(
                        _directory_identity(tuple(relative.parts), metadata)
                    )
        current_root = root.lstat()
        if (
            (current_root.st_dev, current_root.st_ino) != root_identity
            or not stat.S_ISDIR(current_root.st_mode)
            or current_root.st_uid != os.getuid()
            or stat.S_IMODE(current_root.st_mode) != 0o700
        ):
            raise OSError
        digest = hashlib.sha256(
            _canonical_json(
                {
                    "schema": "agentmonitor.m5-codex-profile-tree.v1",
                    "root_device": root_info.st_dev,
                    "root_inode": root_info.st_ino,
                    "entries": records,
                }
            )
        ).hexdigest()
        return _ProfileTreeSnapshotV1(digest, tuple(directories))
    except (OSError, RuntimeError, ValueError):
        raise M5CodexContainmentErrorV1(
            "m5_codex_containment_profile_tree_invalid"
        ) from None


def _managed_profile_tree_digest(root: Path) -> str:
    """Digest bounded metadata enclosed by one exact owner-only root."""

    return _managed_profile_tree_snapshot(root).digest


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


class _OwnedPrivateChannelV1:
    """Serialize nonblocking descriptor access and close it exactly once."""

    def __init__(self, descriptor: int) -> None:
        self._descriptor = descriptor
        self._identity: _InodeIdentityV1 | None = None
        self._close_failed = False
        self._lock = threading.Lock()

    def prepare_nonblocking(self) -> None:
        with self._lock:
            if self._descriptor < 0:
                raise OSError
            identity = _validate_private_channel(self._descriptor)
            os.set_blocking(self._descriptor, False)
            _validate_private_channel(
                self._descriptor,
                expected_identity=identity,
            )
            self._identity = identity

    def read(self, maximum: int) -> bytes:
        with self._lock:
            if self._descriptor < 0 or self._identity is None:
                raise OSError
            return os.read(self._descriptor, maximum)

    def write(self, payload: memoryview) -> int:
        with self._lock:
            if self._descriptor < 0 or self._identity is None:
                raise OSError
            return os.write(self._descriptor, payload)

    def revalidate(self) -> None:
        with self._lock:
            if self._descriptor < 0 or self._identity is None:
                raise OSError
            _validate_private_channel(
                self._descriptor,
                expected_identity=self._identity,
            )

    def close(self) -> bool:
        with self._lock:
            if self._descriptor < 0:
                return not self._close_failed
            descriptor = self._descriptor
            self._descriptor = -1
            try:
                os.close(descriptor)
            except OSError:
                self._close_failed = True
            return not self._close_failed


class _ChannelSettlementV1:
    """Share one post-driver monotonic settlement deadline across workers."""

    def __init__(self) -> None:
        self._deadline: float | None = None
        self._lock = threading.Lock()
        self._cancelled = threading.Event()

    def begin(self) -> float:
        with self._lock:
            if self._deadline is None:
                self._deadline = time.monotonic() + _CHANNEL_SETTLEMENT_SECONDS
            return self._deadline

    def deadline(self) -> float | None:
        with self._lock:
            return self._deadline

    def expired(self) -> bool:
        deadline = self.deadline()
        return deadline is not None and time.monotonic() >= deadline

    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    def pause(self) -> None:
        deadline = self.deadline()
        delay = _CHANNEL_POLL_SECONDS
        if deadline is not None:
            delay = min(delay, max(0.0, deadline - time.monotonic()))
        self._cancelled.wait(delay)

    def cancel(self) -> None:
        self._cancelled.set()


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


def _late_or_invalid_input(
    settlement: _ChannelSettlementV1,
) -> _InputChannelOutcomeV1:
    return _InputChannelOutcomeV1("late" if settlement.expired() else "invalid")


def _late_or_invalid_output(
    settlement: _ChannelSettlementV1,
) -> _OutputChannelOutcomeV1:
    return _OutputChannelOutcomeV1("late" if settlement.expired() else "invalid")


def _write_private_channel_nonblocking(
    channel: _OwnedPrivateChannelV1,
    payload: bytes,
    *,
    maximum: int,
    settlement: _ChannelSettlementV1,
) -> _InputChannelOutcomeV1:
    """Write one bounded payload without a blocking syscall or raw error."""

    outcome = _InputChannelOutcomeV1("invalid")
    try:
        if type(payload) is not bytes or not 1 <= len(payload) <= maximum:
            raise OSError
        channel.prepare_nonblocking()
        view = memoryview(payload)
        written = 0
        while written < len(view):
            if settlement.cancelled() or settlement.expired():
                outcome = _late_or_invalid_input(settlement)
                break
            try:
                count = channel.write(view[written:])
            except BlockingIOError:
                settlement.pause()
                continue
            if count <= 0:
                raise OSError
            written += count
        else:
            channel.revalidate()
            outcome = _InputChannelOutcomeV1("complete")
    except (BufferError, MemoryError, OSError, RuntimeError, TypeError, ValueError):
        outcome = _late_or_invalid_input(settlement)
    if not channel.close() and outcome.state == "complete":
        outcome = _InputChannelOutcomeV1("invalid")
    return outcome


def _read_private_channel_nonblocking(
    channel: _OwnedPrivateChannelV1,
    *,
    maximum: int,
    settlement: _ChannelSettlementV1,
) -> _OutputChannelOutcomeV1:
    """Drain one bounded output through EOF without a blocking syscall."""

    outcome = _OutputChannelOutcomeV1("invalid")
    try:
        channel.prepare_nonblocking()
        payload = bytearray()
        while True:
            if settlement.cancelled() or settlement.expired():
                outcome = _late_or_invalid_output(settlement)
                break
            try:
                chunk = channel.read(min(65_536, maximum + 1 - len(payload)))
            except BlockingIOError:
                settlement.pause()
                continue
            if not chunk:
                channel.revalidate()
                if payload:
                    outcome = _OutputChannelOutcomeV1(
                        "payload",
                        bytes(payload),
                    )
                else:
                    outcome = _OutputChannelOutcomeV1("empty")
                break
            payload.extend(chunk)
            if len(payload) > maximum:
                outcome = _OutputChannelOutcomeV1("invalid")
                break
    except (BufferError, MemoryError, OSError, RuntimeError, TypeError, ValueError):
        outcome = _late_or_invalid_output(settlement)
    if not channel.close() and outcome.state in {"payload", "empty"}:
        outcome = _OutputChannelOutcomeV1("invalid")
    return outcome


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


def _open_pinned_profile_root(
    root: Path,
    *,
    expected_identity: _InodeIdentityV1 | None = None,
) -> tuple[int, _InodeIdentityV1]:
    """Pin one selected profile root without granting child access to its fd."""

    descriptor = -1
    try:
        descriptor = os.open(
            root,
            os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        identity = _validate_private_directory_handle(
            root,
            descriptor,
            expected_identity=expected_identity,
        )
        return descriptor, identity
    except (OSError, RuntimeError, ValueError):
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        raise M5CodexContainmentErrorV1(
            "m5_codex_containment_profile_tree_invalid"
        ) from None


def _directory_identity_table(
    snapshot: _ProfileTreeSnapshotV1,
) -> dict[tuple[str, ...], _DirectoryIdentityV1]:
    if not isinstance(snapshot, _ProfileTreeSnapshotV1):
        raise M5CodexContainmentErrorV1(
            "m5_codex_containment_path_mutator_unverifiable"
        )
    table: dict[tuple[str, ...], _DirectoryIdentityV1] = {}
    for identity in snapshot.directories:
        if identity.relative_parts in table:
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_path_mutator_unverifiable"
            )
        table[identity.relative_parts] = identity
    if () not in table:
        raise M5CodexContainmentErrorV1(
            "m5_codex_containment_path_mutator_unverifiable"
        )
    return table


def _valid_relative_parts(relative_parts: tuple[str, ...]) -> bool:
    return (
        type(relative_parts) is tuple
        and bool(relative_parts)
        and all(
            type(part) is str
            and bool(part)
            and part not in {".", ".."}
            and "/" not in part
            and "\x00" not in part
            for part in relative_parts
        )
        and len(os.fsencode(Path(*relative_parts))) <= 4096
    )


def _same_directory_identity(
    expected: _DirectoryIdentityV1,
    observed: _DirectoryIdentityV1,
) -> bool:
    return (
        expected.relative_parts == observed.relative_parts
        and expected.device == observed.device
        and expected.inode == observed.inode
        and expected.owner_uid == observed.owner_uid
    )


def _close_pinned_descriptor_v1(descriptor: int) -> None:
    """Close one inode pin and turn every resource error into a closed result."""

    try:
        os.close(descriptor)
    except OSError:
        raise M5CodexContainmentErrorV1(
            "m5_codex_containment_path_mutator_unverifiable"
        ) from None


def _open_inode_bound_chmod_target(
    root_descriptor: int,
    relative_parts: tuple[str, ...],
    before_snapshot: _ProfileTreeSnapshotV1,
) -> tuple[int, tuple[_DirectoryIdentityV1, ...]]:
    """Walk and pin an existing target with at most three directory fds."""

    current_descriptor = root_descriptor
    current_is_owned = False
    try:
        if not _valid_relative_parts(relative_parts):
            raise OSError
        table = _directory_identity_table(before_snapshot)
        root_info = os.fstat(root_descriptor)
        root_observed = _directory_identity((), root_info)
        if (
            not stat.S_ISDIR(root_info.st_mode)
            or root_info.st_uid != os.getuid()
            or stat.S_IMODE(root_info.st_mode) != 0o700
            or not _same_directory_identity(table[()], root_observed)
        ):
            raise OSError
        walked: list[_DirectoryIdentityV1] = []
        prefix: tuple[str, ...] = ()
        for part in relative_parts:
            prefix += (part,)
            expected = table.get(prefix)
            if expected is None:
                raise OSError
            next_descriptor = -1
            try:
                next_descriptor = os.open(
                    part,
                    os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=current_descriptor,
                )
                descriptor_info = os.fstat(next_descriptor)
                entry_info = os.stat(
                    part,
                    dir_fd=current_descriptor,
                    follow_symlinks=False,
                )
                observed = _directory_identity(prefix, descriptor_info)
                entry_observed = _directory_identity(prefix, entry_info)
                if (
                    not stat.S_ISDIR(descriptor_info.st_mode)
                    or not stat.S_ISDIR(entry_info.st_mode)
                    or descriptor_info.st_uid != os.getuid()
                    or not _same_directory_identity(expected, observed)
                    or not _same_directory_identity(observed, entry_observed)
                ):
                    raise OSError
            except BaseException:
                if next_descriptor >= 0:
                    os.close(next_descriptor)
                raise
            previous_descriptor = current_descriptor if current_is_owned else -1
            current_descriptor = next_descriptor
            current_is_owned = True
            next_descriptor = -1
            if previous_descriptor >= 0:
                _close_pinned_descriptor_v1(previous_descriptor)
            walked.append(observed)
        target = walked[-1]
        if target.mode != 0o700:
            raise OSError
        owned_target = current_descriptor
        current_is_owned = False
        return owned_target, tuple(walked)
    except (KeyError, OSError, RuntimeError, TypeError, ValueError):
        raise M5CodexContainmentErrorV1(
            "m5_codex_containment_path_mutator_unverifiable"
        ) from None
    finally:
        if current_is_owned:
            try:
                _close_pinned_descriptor_v1(current_descriptor)
            except M5CodexContainmentErrorV1:
                pass


def _validate_inode_bound_chmod(
    target_descriptor: int,
    relative_parts: tuple[str, ...],
    walked: tuple[_DirectoryIdentityV1, ...],
    before_snapshot: _ProfileTreeSnapshotV1,
    after_snapshot: _ProfileTreeSnapshotV1,
) -> None:
    """Validate the pinned target and its ancestors across both tree scans."""

    try:
        if not _valid_relative_parts(relative_parts) or len(walked) != len(
            relative_parts
        ):
            raise OSError
        before = _directory_identity_table(before_snapshot)
        after = _directory_identity_table(after_snapshot)
        for index, observed in enumerate(walked, start=1):
            prefix = relative_parts[:index]
            before_identity = before[prefix]
            after_identity = after[prefix]
            if not (
                _same_directory_identity(before_identity, observed)
                and _same_directory_identity(observed, after_identity)
                and after_identity.owner_uid == os.getuid()
            ):
                raise OSError
        before_target = before[relative_parts]
        walked_target = walked[-1]
        after_target = after[relative_parts]
        descriptor_info = os.fstat(target_descriptor)
        descriptor_target = _directory_identity(relative_parts, descriptor_info)
        if (
            not stat.S_ISDIR(descriptor_info.st_mode)
            or not _same_directory_identity(after_target, descriptor_target)
            or {
                before_target.mode,
                walked_target.mode,
                after_target.mode,
                descriptor_target.mode,
            }
            != {0o700}
            or after_target.changed_ns <= before_target.changed_ns
            or descriptor_target.changed_ns < after_target.changed_ns
        ):
            raise OSError
    except (KeyError, OSError, RuntimeError, TypeError, ValueError):
        raise M5CodexContainmentErrorV1(
            "m5_codex_containment_path_mutator_unverifiable"
        ) from None


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _unique_json_object(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, member in pairs:
        if key in value:
            raise ValueError
        value[key] = member
    return value


def _decode_unique_json(payload: bytes, *, code: str) -> object:
    try:
        return cast(
            object,
            json.loads(
                payload.decode("utf-8"),
                object_pairs_hook=_unique_json_object,
            ),
        )
    except (UnicodeError, ValueError):
        raise M5CodexContainmentErrorV1(code) from None


def _decode_json_object(payload: bytes) -> dict[str, object]:
    value = _decode_unique_json(
        payload,
        code="m5_codex_containment_private_channel_invalid",
    )
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
    pending: dict[tuple[int, str], tuple[str, int, int]] = {}
    for line_ordinal, line in enumerate(trace.splitlines()):
        match = _TRACE_LINE.fullmatch(line)
        if match is not None:
            records.append(
                _TraceRecordV1(
                    int(match.group("pid")),
                    match.group("call"),
                    match.group("arguments"),
                    match.group("result"),
                    line_ordinal,
                    line_ordinal,
                )
            )
            continue
        unfinished = _TRACE_UNFINISHED.fullmatch(line)
        if unfinished is not None:
            key = (int(unfinished.group("pid")), unfinished.group("call"))
            if key in pending:
                raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
            pending[key] = (
                unfinished.group("arguments"),
                len(records),
                line_ordinal,
            )
            records.append(None)
            continue
        resumed = _TRACE_RESUMED.fullmatch(line)
        if resumed is None:
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        key = (int(resumed.group("pid")), resumed.group("call"))
        pending_record = pending.pop(key, None)
        if pending_record is None:
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        first, index, invoked_at = pending_record
        records[index] = _TraceRecordV1(
            key[0],
            key[1],
            first + resumed.group("arguments"),
            resumed.group("result"),
            invoked_at,
            line_ordinal,
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
    match = re.fullmatch(r"([1-9][0-9]*)", record.result)
    return None if match is None else int(match.group(1))


def _chdir_target(
    record: _TraceRecordV1,
    *,
    working_root: Path,
) -> Path | None:
    if record.call != "chdir":
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    if record.result != "0":
        if _TRACE_FAILED_RESULT_V1.fullmatch(record.result) is not None:
            return None
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    match = _TRACE_CHDIR_ARGUMENTS_V1.fullmatch(record.arguments)
    if match is None:
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    quoted = _TRACE_QUOTED.fullmatch(match.group("path"))
    if quoted is None:
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    raw_path = _decode_trace_string(quoted.group(1))
    if (
        not raw_path
        or "\x00" in raw_path
        or raw_path.startswith("//")
        or os.path.normpath(raw_path) != raw_path
    ):
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = working_root / candidate
    normalized = Path(os.path.normpath(os.fspath(candidate)))
    if not normalized.is_absolute():
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    return normalized


def _execve_argv(record: _TraceRecordV1) -> tuple[str, tuple[str, ...]]:
    if record.call != "execve":
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    match = _TRACE_EXECVE_ARGUMENTS_V1.fullmatch(record.arguments)
    if match is None:
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    path_values = _TRACE_QUOTED.fullmatch(match.group("path"))
    if path_values is None:
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    path = _decode_trace_string(path_values.group(1))
    argv = tuple(
        _decode_trace_string(value)
        for value in _TRACE_QUOTED.findall(match.group("argv"))
    )
    if not argv or argv[0] != path:
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    return path, argv


def _operation_role(
    record: _TraceRecordV1,
    *,
    provider_executable: Path,
) -> Literal["version", "app_server"]:
    path, argv = _execve_argv(record)
    if path != os.fspath(provider_executable):
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    if argv[1:] == ("--version",):
        return "version"
    if argv[1:] == _PROVIDER_APP_SERVER_ARGUMENTS:
        return "app_server"
    raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")


def _parse_exact_chmod(
    record: _TraceRecordV1,
    *,
    managed_profile_root: Path,
) -> tuple[str, ...]:
    if record.call != "chmod" or record.result != "0":
        raise M5CodexContainmentErrorV1(
            "m5_codex_containment_path_mutator_unverifiable"
        )
    match = _TRACE_CHMOD_ARGUMENTS_V1.fullmatch(record.arguments)
    if match is None:
        raise M5CodexContainmentErrorV1(
            "m5_codex_containment_path_mutator_unverifiable"
        )
    raw_path = _decode_trace_string(match.group("path"))
    if (
        not raw_path.isascii()
        or not raw_path.startswith("/")
        or raw_path.startswith("//")
        or "\x00" in raw_path
        or os.path.normpath(raw_path) != raw_path
    ):
        raise M5CodexContainmentErrorV1(
            "m5_codex_containment_path_mutator_unverifiable"
        )
    candidate = Path(raw_path)
    try:
        relative = candidate.relative_to(managed_profile_root)
    except ValueError:
        raise M5CodexContainmentErrorV1(
            "m5_codex_containment_path_mutator_unverifiable"
        ) from None
    relative_parts = tuple(relative.parts)
    if not _valid_relative_parts(relative_parts):
        raise M5CodexContainmentErrorV1(
            "m5_codex_containment_path_mutator_unverifiable"
        )
    return relative_parts


def _flag_requested(expression: str, *, name: str, value: int) -> bool:
    if not expression or "..." in expression:
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    requested = False
    for token in expression.split("|"):
        token = token.strip()
        if token == name:
            requested = True
            continue
        if re.fullmatch(r"0x[0-9a-fA-F]+|[0-9]+", token):
            requested = requested or bool(int(token, 0) & value)
            continue
        if re.fullmatch(r"[A-Z][A-Z0-9_]*", token) is None:
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    return requested


def _clone_flag_requested(record: _TraceRecordV1, *, name: str, value: int) -> bool:
    if record.call not in {"clone", "clone3"}:
        return False
    match = _TRACE_FLAGS_V1.search(record.arguments)
    if match is None:
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    return _flag_requested(match.group("flags").strip(), name=name, value=value)


def _mount_namespace_requested(record: _TraceRecordV1) -> bool:
    if record.call == "unshare":
        return _flag_requested(
            record.arguments.strip(),
            name="CLONE_NEWNS",
            value=_CLONE_NEWNS,
        )
    return _clone_flag_requested(
        record,
        name="CLONE_NEWNS",
        value=_CLONE_NEWNS,
    )


def _ftruncate_target_v1(record: _TraceRecordV1) -> Path | None:
    """Return one exact successful descriptor target or a proven no-effect."""

    if record.call != "ftruncate":
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    match = _TRACE_FTRUNCATE_ARGUMENTS_V1.fullmatch(record.arguments)
    if match is None:
        if _TRACE_FTRUNCATE_MISSING_PATH_V1.fullmatch(record.arguments) is not None:
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_fd_write_unverifiable"
            )
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    length = int(match.group("length"))
    if length > 2**63 - 1:
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    raw_path = match.group("path")
    if raw_path.endswith(" (deleted)"):
        raise M5CodexContainmentErrorV1("m5_codex_containment_fd_write_unverifiable")
    if (
        not raw_path.startswith("/")
        or raw_path.startswith("//")
        or os.path.normpath(raw_path) != raw_path
    ):
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    target = Path(raw_path)
    if not target.is_absolute():
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    success = record.result == "0"
    failed = _TRACE_FTRUNCATE_FAILED_RESULT_V1.fullmatch(record.result) is not None
    if not success and not failed:
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    return target if success else None


def _canonical_dirfd_annotation_v1(raw_path: str) -> Path:
    if (
        raw_path.endswith(" (deleted)")
        or not raw_path.startswith("/")
        or raw_path.startswith("//")
        or os.path.normpath(raw_path) != raw_path
    ):
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    path = Path(raw_path)
    if not path.is_absolute():
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    return path


def _unlinkat_target_v1(
    record: _TraceRecordV1,
    *,
    working_root: Path,
) -> Path:
    """Resolve one exact unlinkat target using its kernel directory base."""

    if record.call != "unlinkat":
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    match = _TRACE_UNLINKAT_ARGUMENTS_V1.fullmatch(record.arguments)
    if match is None:
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    if (
        record.result != "0"
        and _TRACE_FTRUNCATE_FAILED_RESULT_V1.fullmatch(record.result) is None
    ):
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    quoted = _TRACE_QUOTED.fullmatch(match.group("path"))
    if quoted is None:
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    raw_target = _decode_trace_string(quoted.group(1))
    if (
        not raw_target
        or any(ord(character) < 32 or ord(character) == 127 for character in raw_target)
        or raw_target.startswith("//")
        or any(component in {".", ".."} for component in raw_target.split("/"))
        or os.path.normpath(raw_target) != raw_target
    ):
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    raw_dirfd = match.group("dirfd")
    annotation = match.group("annotation")
    annotation_path = (
        _canonical_dirfd_annotation_v1(annotation) if annotation is not None else None
    )
    target = Path(raw_target)
    if target.is_absolute():
        return target

    if raw_dirfd == "AT_FDCWD":
        base = working_root
    elif raw_dirfd.startswith("AT_FDCWD<"):
        if annotation_path is None:
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        base = annotation_path
        if base != working_root:
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    else:
        descriptor, separator, _ = raw_dirfd.partition("<")
        if (
            not separator
            or annotation_path is None
            or _TRACE_NUMERIC_DIRFD_V1.fullmatch(descriptor) is None
        ):
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        base = annotation_path
    candidate = Path(os.path.normpath(os.fspath(base / target)))
    if not candidate.is_absolute():
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    return candidate


def _unlinkat_flags_v1(record: _TraceRecordV1) -> str:
    """Return the exact parsed unlinkat flags without exposing its path."""

    if record.call != "unlinkat":
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    match = _TRACE_UNLINKAT_ARGUMENTS_V1.fullmatch(record.arguments)
    if match is None:
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    return match.group("flags")


def _symlink_arguments_v1(
    record: _TraceRecordV1,
    *,
    working_root: Path,
) -> tuple[str, Path, bool]:
    """Parse one plain symlink without treating its payload as an access."""

    if record.call != "symlink":
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    match = _TRACE_SYMLINK_ARGUMENTS_V1.fullmatch(record.arguments)
    if match is None or (
        record.result != "0"
        and _TRACE_FTRUNCATE_FAILED_RESULT_V1.fullmatch(record.result) is None
    ):
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    payload_token = _TRACE_QUOTED.fullmatch(match.group("payload"))
    link_token = _TRACE_QUOTED.fullmatch(match.group("linkpath"))
    if payload_token is None or link_token is None:
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    raw_payload = payload_token.group(1)
    raw_path = link_token.group(1)
    if (
        not raw_payload
        or not raw_path
        or "\\" in raw_payload
        or "\\" in raw_path
        or any(
            ord(character) < 32 or ord(character) == 127 for character in raw_payload
        )
        or any(ord(character) < 32 or ord(character) == 127 for character in raw_path)
        or raw_payload.startswith("//")
        or raw_path.startswith("//")
        or any(component in {".", ".."} for component in raw_payload.split("/"))
        or any(component in {".", ".."} for component in raw_path.split("/"))
        or os.path.normpath(raw_payload) != raw_payload
        or os.path.normpath(raw_path) != raw_path
    ):
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    payload = _decode_trace_string(raw_payload)
    candidate = Path(raw_path)
    absolute = candidate.is_absolute()
    if not candidate.is_absolute():
        candidate = working_root / candidate
    candidate = Path(os.path.normpath(os.fspath(candidate)))
    if not candidate.is_absolute():
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    return payload, candidate, absolute


def _symlink_link_path_v1(
    record: _TraceRecordV1,
    *,
    working_root: Path,
) -> Path:
    """Resolve only the created link path; the first argument is payload data."""

    return _symlink_arguments_v1(record, working_root=working_root)[1]


def _trace_paths(record: _TraceRecordV1, *, working_root: Path) -> tuple[Path, ...]:
    if record.call == "unlinkat":
        return (_unlinkat_target_v1(record, working_root=working_root),)
    if record.call == "symlink":
        return (_symlink_link_path_v1(record, working_root=working_root),)
    quoted = _quoted_arguments(record)
    if record.call in {"execve", "execveat"}:
        quoted = quoted[:1]
    relative_count = sum(
        1 for value in quoted if value and not Path(value).is_absolute()
    )
    required_dirfds = _DIRFD_COUNTS.get(record.call)
    unquoted_arguments = _TRACE_QUOTED.sub('""', record.arguments)
    if (
        relative_count
        and required_dirfds is not None
        and len(_TRACE_AT_FDCWD.findall(unquoted_arguments)) < required_dirfds
    ):
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    candidates: list[Path] = []
    for value in quoted:
        if not value:
            continue
        if value.startswith("//"):
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = working_root / candidate
        candidates.append(Path(os.path.normpath(os.fspath(candidate))))
    if record.call in _OPEN_CALLS and _successful(record):
        match = _TRACE_RESULT_DESCRIPTOR.fullmatch(record.result)
        if match is None:
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        resolved = _decode_trace_string(match.group("path"))
        if resolved.endswith(" (deleted)") or resolved.startswith("//"):
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        resolved_path = Path(resolved)
        if not resolved_path.is_absolute():
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        candidates.append(Path(os.path.normpath(os.fspath(resolved_path))))
    return tuple(dict.fromkeys(candidates))


def _trace_uses_relative_working_directory_v1(record: _TraceRecordV1) -> bool:
    """Return whether one path lookup depends on the process working directory."""

    if record.call == "unlinkat":
        match = _TRACE_UNLINKAT_ARGUMENTS_V1.fullmatch(record.arguments)
        if match is None:
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        quoted = _TRACE_QUOTED.fullmatch(match.group("path"))
        if quoted is None:
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        target = Path(_decode_trace_string(quoted.group(1)))
        return not target.is_absolute() and match.group("dirfd").startswith("AT_FDCWD")
    if record.call == "symlink":
        match = _TRACE_SYMLINK_ARGUMENTS_V1.fullmatch(record.arguments)
        if match is None:
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        quoted = _TRACE_QUOTED.fullmatch(match.group("linkpath"))
        if quoted is None:
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        return not Path(_decode_trace_string(quoted.group(1))).is_absolute()
    quoted_values = _quoted_arguments(record)
    if record.call in {"execve", "execveat"}:
        quoted_values = quoted_values[:1]
    return any(value and not Path(value).is_absolute() for value in quoted_values)


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


def _validate_arg0_lifecycles_v1(
    classified_records: list[tuple[_TraceRecordV1, tuple[Path, ...], bool, Path]],
    *,
    record_operations: dict[int, _OperationV1],
    operations: list[_OperationV1],
    operation_exec_records: dict[int, _TraceRecordV1],
    root_exit_records: dict[int, _TraceRecordV1],
    operation_pids: dict[int, frozenset[int]],
    pid_exit_records: dict[int, _TraceRecordV1],
    provider_executable: Path,
    managed_profile_root: Path,
) -> frozenset[int]:
    """Admit only the pinned Codex Arg0 create-and-cleanup lifecycle."""

    link_error = "m5_codex_containment_link_operation_rejected"
    mutation_error = "m5_codex_containment_path_mutator_unverifiable"
    creations_by_operation: dict[int, list[_Arg0CreationV1]] = {}
    admitted_links: set[int] = set()

    for record_index, (record, _, _, working_directory) in enumerate(
        classified_records
    ):
        if record.call != "symlink":
            continue
        payload, path, absolute_path = _symlink_arguments_v1(
            record,
            working_root=working_directory,
        )
        operation = record_operations.get(record_index)
        if (
            record.result != "0"
            or operation is None
            or operation.kind not in {"identity", "quota"}
            or record.pid != operation.root_pid
            or payload != os.fspath(provider_executable)
            or not Path(payload).is_absolute()
            or not absolute_path
        ):
            raise M5CodexContainmentErrorV1(link_error)
        try:
            relative = path.relative_to(managed_profile_root)
        except ValueError:
            raise M5CodexContainmentErrorV1(link_error) from None
        parts = relative.parts
        if (
            len(parts) != 4
            or parts[:2] != ("tmp", "arg0")
            or _ARG0_SESSION_V1.fullmatch(parts[2]) is None
            or parts[3] not in _ARG0_ALIASES_V1
        ):
            raise M5CodexContainmentErrorV1(link_error)
        session = managed_profile_root.joinpath(*parts[:3])
        creations_by_operation.setdefault(operation.sequence, []).append(
            _Arg0CreationV1(
                operation,
                record_index,
                path,
                session,
                parts[3],
            )
        )
        admitted_links.add(record_index)

    arg0_operations = tuple(
        operation for operation in operations if operation.kind in {"identity", "quota"}
    )
    if len(arg0_operations) != 2 or {
        operation.kind for operation in arg0_operations
    } != {"identity", "quota"}:
        raise M5CodexContainmentErrorV1(link_error)

    cleanup_by_operation: dict[int, set[int]] = {}
    operation_close_completions: dict[int, int] = {}
    for operation in operations:
        owned_pids = operation_pids.get(operation.sequence)
        exec_record = operation_exec_records.get(operation.sequence)
        root_exit_record = root_exit_records.get(operation.sequence)
        if (
            not owned_pids
            or exec_record is None
            or root_exit_record is None
            or exec_record.completed_at >= root_exit_record.invoked_at
            or any(pid not in pid_exit_records for pid in owned_pids)
        ):
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        operation_close_completions[operation.sequence] = max(
            pid_exit_records[pid].completed_at for pid in owned_pids
        )
    for operation in arg0_operations:
        creations = sorted(
            creations_by_operation.get(operation.sequence, ()),
            key=lambda creation: (
                classified_records[creation.record_index][0].invoked_at
            ),
        )
        if (
            len(creations) != len(_ARG0_ALIASES_V1)
            or tuple(creation.alias for creation in creations) != _ARG0_ALIASES_V1
            or len({creation.path for creation in creations}) != len(_ARG0_ALIASES_V1)
            or len({creation.session for creation in creations}) != 1
        ):
            raise M5CodexContainmentErrorV1(link_error)
        exec_record = operation_exec_records.get(operation.sequence)
        exit_record = root_exit_records.get(operation.sequence)
        owned_pids = operation_pids.get(operation.sequence)
        if exec_record is None or exit_record is None or not owned_pids:
            raise M5CodexContainmentErrorV1(link_error)
        operation_close_completion = operation_close_completions[operation.sequence]
        creation_records = tuple(
            classified_records[creation.record_index][0] for creation in creations
        )
        if (
            exec_record.completed_at >= creation_records[0].invoked_at
            or any(
                earlier.completed_at >= later.invoked_at
                for earlier, later in pairwise(creation_records)
            )
            or creation_records[-1].completed_at >= exit_record.invoked_at
        ):
            raise M5CodexContainmentErrorV1(link_error)

        cleanup_indexes: set[int] = set()
        for creation, creation_record in zip(
            creations,
            creation_records,
            strict=True,
        ):
            candidates = tuple(
                candidate_index
                for candidate_index, (candidate, paths, _, _) in enumerate(
                    classified_records
                )
                if (
                    candidate.call == "unlinkat"
                    and paths == (creation.path,)
                    and record_operations.get(candidate_index) == operation
                )
            )
            if len(candidates) != 1:
                raise M5CodexContainmentErrorV1(link_error)
            cleanup_index = candidates[0]
            cleanup_record = classified_records[cleanup_index][0]
            cleanup_exit = pid_exit_records.get(cleanup_record.pid)
            if (
                cleanup_record.result != "0"
                or _unlinkat_flags_v1(cleanup_record) != "0"
                or creation_record.completed_at >= cleanup_record.invoked_at
                or cleanup_record.completed_at >= exit_record.invoked_at
                or cleanup_exit is None
                or cleanup_record.completed_at >= cleanup_exit.invoked_at
            ):
                raise M5CodexContainmentErrorV1(link_error)
            cleanup_indexes.add(cleanup_index)
        if len(cleanup_indexes) != len(_ARG0_ALIASES_V1):
            raise M5CodexContainmentErrorV1(link_error)
        if min(
            classified_records[index][0].invoked_at for index in cleanup_indexes
        ) <= max(record.completed_at for record in creation_records):
            raise M5CodexContainmentErrorV1(link_error)
        cleanup_by_operation[operation.sequence] = cleanup_indexes

        first_creation_invocation = creation_records[0].invoked_at
        final_cleanup_completion = max(
            classified_records[index][0].completed_at for index in cleanup_indexes
        )
        first_cleanup_invocation = min(
            classified_records[index][0].invoked_at for index in cleanup_indexes
        )
        allowed_indexes = {
            *(creation.record_index for creation in creations),
            *cleanup_indexes,
        }
        parent_removal_index: int | None = None
        session = creations[0].session
        for candidate_index, (candidate, paths, is_write, _) in enumerate(
            classified_records
        ):
            candidate_operation = record_operations.get(candidate_index)
            candidate_exit = pid_exit_records.get(candidate.pid)
            overlaps_operation = not (
                candidate.completed_at < first_creation_invocation
                or candidate.invoked_at > operation_close_completion
            )
            if (
                overlaps_operation
                and is_write
                and _successful(candidate)
                and candidate_operation is None
            ):
                code = link_error if candidate.call in _LINK_CALLS else mutation_error
                raise M5CodexContainmentErrorV1(code)
            failed_existing_arg0_mkdir = (
                candidate.call == "mkdir"
                and candidate.result == "-1 EEXIST (File exists)"
                and candidate_operation == operation
                and candidate.pid != operation.root_pid
                and len(paths) == 1
                and (paths[0] == session or paths[0] in session.parents)
                and any(
                    record.completed_at < candidate.invoked_at
                    for record in creation_records
                )
                and candidate.completed_at < first_cleanup_invocation
                and candidate.completed_at < exit_record.invoked_at
                and candidate_exit is not None
                and candidate.completed_at < candidate_exit.invoked_at
            )
            if (
                not is_write
                or not paths
                or not overlaps_operation
                or not any(
                    _is_within(path, session) or _is_within(session, path)
                    for path in paths
                )
                or candidate_index in allowed_indexes
                or failed_existing_arg0_mkdir
            ):
                continue
            exact_parent_removal = False
            if (
                paths == (session,)
                and candidate.result == "0"
                and candidate_operation == operation
                and candidate.invoked_at > final_cleanup_completion
                and candidate.completed_at < exit_record.invoked_at
                and candidate_exit is not None
                and candidate.completed_at < candidate_exit.invoked_at
            ):
                if candidate.call == "unlinkat":
                    exact_parent_removal = (
                        _unlinkat_flags_v1(candidate) == "AT_REMOVEDIR"
                    )
                elif candidate.call == "rmdir":
                    exact_parent_removal = candidate.arguments == f'"{session}"'
            if exact_parent_removal and parent_removal_index is None:
                parent_removal_index = candidate_index
                continue
            code = link_error if candidate.call in _LINK_CALLS else mutation_error
            raise M5CodexContainmentErrorV1(code)

    if set(creations_by_operation) != {
        operation.sequence for operation in arg0_operations
    }:
        raise M5CodexContainmentErrorV1(link_error)
    creation_keys = {
        (creation.operation.sequence, creation.path)
        for creations in creations_by_operation.values()
        for creation in creations
    }
    created_paths = {path for _, path in creation_keys}
    for record_index, (record, paths, _, _) in enumerate(classified_records):
        if (
            record.call != "unlinkat"
            or len(paths) != 1
            or paths[0] not in created_paths
        ):
            continue
        cleanup_operation = record_operations.get(record_index)
        if (
            cleanup_operation is None
            or (cleanup_operation.sequence, paths[0]) not in creation_keys
        ):
            raise M5CodexContainmentErrorV1(link_error)
    if len(admitted_links) != 2 * len(_ARG0_ALIASES_V1):
        raise M5CodexContainmentErrorV1(link_error)
    if sum(len(indexes) for indexes in cleanup_by_operation.values()) != 2 * len(
        _ARG0_ALIASES_V1
    ):
        raise M5CodexContainmentErrorV1(link_error)

    for record_index, (record, _, _, _) in enumerate(classified_records):
        if record.call in _LINK_CALLS and record_index not in admitted_links:
            raise M5CodexContainmentErrorV1(link_error)

    for previous, following in pairwise(operations):
        following_exec = operation_exec_records.get(following.sequence)
        if (
            previous.sequence not in operation_close_completions
            or following_exec is None
            or operation_close_completions[previous.sequence]
            >= following_exec.invoked_at
        ):
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
    return frozenset(admitted_links)


def _evaluate_codex_trace_policy_v1(
    trace: str,
    *,
    provider_executable: Path,
    managed_profile_root: Path,
    default_codex_roots: tuple[Path, ...],
) -> _TraceEvaluationV1:
    """Evaluate one complete trace while retaining the chmod target in process."""

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

    release_roots = {
        root: _installation_release_root(executable, root) for root in defaults
    }
    default_accesses = 0
    default_writes = 0
    classified_records: list[tuple[_TraceRecordV1, tuple[Path, ...], bool, Path]] = []
    working_directory_groups: dict[int, int] = {}
    group_working_directories: dict[int, Path] = {}
    unfinished_successful_chdirs: list[tuple[_TraceRecordV1, int]] = []
    target_replacement_records: list[tuple[_TraceRecordV1, tuple[Path, ...]]] = []
    for record in records:
        raw_no_effect = False
        ftruncate_target: Path | None = None
        ftruncate_no_effect = False
        if record.call in _RAW_GLOBAL_CALLS:
            if _TRACE_FAILED_RESULT_V1.fullmatch(record.result) is not None:
                raw_no_effect = True
            elif _TRACE_NONNEGATIVE_RESULT_V1.fullmatch(record.result) is not None or (
                record.call == "io_uring_setup"
                and _TRACE_DESCRIPTOR_RESULT_V1.fullmatch(record.result) is not None
            ):
                raise M5CodexContainmentErrorV1(
                    "m5_codex_containment_fd_write_unverifiable"
                )
            else:
                raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        if record.call == "ftruncate":
            ftruncate_target = _ftruncate_target_v1(record)
            ftruncate_no_effect = ftruncate_target is None
        working_directory_group = working_directory_groups.setdefault(
            record.pid,
            record.pid,
        )
        working_directory = group_working_directories.setdefault(
            working_directory_group,
            managed,
        )
        paths: tuple[Path, ...]
        if ftruncate_target is not None:
            paths = (ftruncate_target,)
        elif raw_no_effect or ftruncate_no_effect:
            paths = ()
        else:
            paths = _trace_paths(record, working_root=working_directory)
        is_write = ftruncate_target is not None or (
            not raw_no_effect and not ftruncate_no_effect and _trace_is_write(record)
        )
        classified_records.append((record, paths, is_write, working_directory))
        if (
            _successful(record)
            and record.call in {"clone", "clone3"}
            and _clone_flag_requested(
                record,
                name="CLONE_UNTRACED",
                value=_CLONE_UNTRACED,
            )
        ):
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        if (
            _successful(record)
            and record.call in {"clone", "clone3", "unshare"}
            and _mount_namespace_requested(record)
        ):
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_namespace_operation_rejected"
            )
        if _successful(record) and record.call in _NAMESPACE_CALLS:
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_namespace_operation_rejected"
            )
        if _successful(record) and record.call == "fchdir":
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_working_directory_escape"
            )
        if (
            _successful(record)
            and record.call in _FD_ONLY_MUTATORS
            and record.call != "ftruncate"
        ):
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_fd_write_unverifiable"
            )
        if (
            _successful(record)
            and record.call in _PATH_FOLLOWING_MUTATORS
            and record.call != "chmod"
        ):
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_path_mutator_unverifiable"
            )
        child = _child_pid(record)
        if record.call in _CHILD_CALLS and _successful(record):
            if child is None or child in working_directory_groups:
                raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
            child_group = (
                working_directory_group
                if _clone_flag_requested(
                    record,
                    name="CLONE_FS",
                    value=_CLONE_FS,
                )
                else child
            )
            working_directory_groups[child] = child_group
            group_working_directories.setdefault(child_group, working_directory)
        if _successful(record) and record.call in (
            _TARGET_NAMESPACE_CALLS | _LINK_CALLS
        ):
            target_replacement_records.append((record, paths))
        if record.call == "chdir":
            changed_directory = _chdir_target(
                record,
                working_root=working_directory,
            )
            if changed_directory is not None:
                if record.invoked_at != record.completed_at:
                    unfinished_successful_chdirs.append(
                        (record, working_directory_group)
                    )
                group_working_directories[working_directory_group] = changed_directory
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
    for chdir_record, working_directory_group in unfinished_successful_chdirs:
        for record in records:
            if (
                record is chdir_record
                or working_directory_groups.get(record.pid, record.pid)
                != working_directory_group
                or record.completed_at < chdir_record.invoked_at
                or record.invoked_at > chdir_record.completed_at
                or not _trace_uses_relative_working_directory_v1(record)
            ):
                continue
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_working_directory_escape"
            )
    if default_accesses or default_writes:
        raise M5CodexContainmentErrorV1("m5_codex_default_profile_access_detected")

    expected_operations: tuple[Literal["version", "identity", "quota"], ...] = (
        "version",
        "identity",
        "quota",
    )
    operations: list[_OperationV1] = []
    owners: dict[int, _OperationV1] = {}
    ended_pids: set[int] = set()
    thread_groups: dict[int, int] = {}
    closed_operations: set[int] = set()
    current_operation: _OperationV1 | None = None
    chmods: list[tuple[_OperationV1, tuple[str, ...], int]] = []
    record_operations: dict[int, _OperationV1] = {}
    operation_exec_records: dict[int, _TraceRecordV1] = {}
    root_exit_records: dict[int, _TraceRecordV1] = {}
    pid_exit_records: dict[int, _TraceRecordV1] = {}
    accesses = 0
    writes = 0
    for record_index, (
        record,
        paths,
        is_write,
        working_directory,
    ) in enumerate(classified_records):
        exact_provider_exec = False
        if record.call in {"execve", "execveat"}:
            quoted = _quoted_arguments(record)
            if not quoted:
                raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
            invoked = Path(os.path.normpath(quoted[0]))
            if invoked == executable:
                if not _successful(record):
                    raise M5CodexContainmentErrorV1(
                        "m5_codex_containment_trace_invalid"
                    )
                if current_operation is not None or record.pid in owners:
                    raise M5CodexContainmentErrorV1(
                        "m5_codex_containment_trace_invalid"
                    )
                sequence = len(operations)
                if sequence >= len(expected_operations):
                    raise M5CodexContainmentErrorV1(
                        "m5_codex_containment_trace_invalid"
                    )
                observed_role = _operation_role(
                    record,
                    provider_executable=executable,
                )
                expected_kind = expected_operations[sequence]
                if (expected_kind == "version") != (observed_role == "version"):
                    raise M5CodexContainmentErrorV1(
                        "m5_codex_containment_trace_invalid"
                    )
                if expected_kind != "version" and working_directory != managed:
                    raise M5CodexContainmentErrorV1(
                        "m5_codex_containment_working_directory_escape"
                    )
                started_operation = _OperationV1(
                    sequence,
                    expected_kind,
                    record.pid,
                )
                operations.append(started_operation)
                owners[record.pid] = started_operation
                thread_groups[record.pid] = record.pid
                operation_exec_records[sequence] = record
                current_operation = started_operation
                exact_provider_exec = True

        operation = owners.get(record.pid)
        if operation is not None and operation.sequence in closed_operations:
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        if record.pid in ended_pids:
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
        if operation is not None:
            record_operations[record_index] = operation
        if record.call == "chmod":
            relative_parts = _parse_exact_chmod(
                record,
                managed_profile_root=managed,
            )
            if operation is None or operation.kind not in {"identity", "quota"}:
                raise M5CodexContainmentErrorV1(
                    "m5_codex_containment_path_mutator_unverifiable"
                )
            chmods.append((operation, relative_parts, record_index))
        if (
            record.call == "ftruncate"
            and paths
            and (operation is None or operation.kind not in {"identity", "quota"})
        ):
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_fd_write_unverifiable"
            )
        if operation is None:
            continue

        child = _child_pid(record)
        if child is not None:
            if child in owners:
                raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
            owners[child] = operation
            parent_group = thread_groups.get(record.pid, record.pid)
            thread_groups[child] = (
                parent_group
                if _clone_flag_requested(
                    record,
                    name="CLONE_THREAD",
                    value=_CLONE_THREAD,
                )
                else child
            )
        if (
            _successful(record)
            and record.call in _FD_ONLY_MUTATORS
            and record.call != "ftruncate"
        ):
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_fd_write_unverifiable"
            )
        if (
            _successful(record)
            and record.call in _PATH_FOLLOWING_MUTATORS
            and record.call != "chmod"
        ):
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_path_mutator_unverifiable"
            )
        if paths:
            accesses += 1
        if is_write:
            if not paths:
                raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")
            writes += 1
            if operation.kind not in {"identity", "quota"} or any(
                not _is_within(path, managed) for path in paths
            ):
                raise M5CodexContainmentErrorV1("m5_codex_managed_profile_write_escape")
        if record.call == "chdir" and _successful(record):
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_working_directory_escape"
            )
        if record.call in _EXIT_CALLS and _successful(record):
            root_group = thread_groups.get(operation.root_pid, operation.root_pid)
            record_group = thread_groups.get(record.pid, record.pid)
            if record.pid == operation.root_pid or (
                record.call == "exit_group" and record_group == root_group
            ):
                root_exit_records.setdefault(operation.sequence, record)
            if record.call == "exit_group":
                group = thread_groups.get(record.pid, record.pid)
                affected_pids = tuple(
                    pid
                    for pid, owner in owners.items()
                    if owner == operation and thread_groups.get(pid, pid) == group
                )
            else:
                affected_pids = (record.pid,)
            for affected_pid in affected_pids:
                pid_exit_records.setdefault(affected_pid, record)
            ended_pids.update(affected_pids)
            owned_operation_pids = tuple(
                pid for pid, owner in owners.items() if owner == operation
            )
            if operation.root_pid in ended_pids and all(
                pid in ended_pids for pid in owned_operation_pids
            ):
                closed_operations.add(operation.sequence)
                current_operation = None
        if exact_provider_exec and owners.get(record.pid) != operation:
            raise M5CodexContainmentErrorV1("m5_codex_containment_trace_invalid")

    if (
        len(operations) != 3
        or current_operation is not None
        or closed_operations != {0, 1, 2}
        or len(chmods) != 2
        or {chmod[0].kind for chmod in chmods} != {"identity", "quota"}
        or chmods[0][1] != chmods[1][1]
    ):
        raise M5CodexContainmentErrorV1(
            "m5_codex_containment_path_mutator_unverifiable"
        )
    operation_pids: dict[int, set[int]] = {}
    for pid, operation in owners.items():
        operation_pids.setdefault(operation.sequence, set()).add(pid)
    _validate_arg0_lifecycles_v1(
        classified_records,
        record_operations=record_operations,
        operations=operations,
        operation_exec_records=operation_exec_records,
        root_exit_records=root_exit_records,
        operation_pids={
            sequence: frozenset(pids) for sequence, pids in operation_pids.items()
        },
        pid_exit_records=pid_exit_records,
        provider_executable=executable,
        managed_profile_root=managed,
    )
    admitted_target = managed.joinpath(*chmods[0][1])
    for replacement_record, paths in target_replacement_records:
        if any(
            path == admitted_target or path in admitted_target.parents for path in paths
        ):
            code = (
                "m5_codex_containment_link_operation_rejected"
                if replacement_record.call in _LINK_CALLS
                else "m5_codex_containment_path_mutator_unverifiable"
            )
            raise M5CodexContainmentErrorV1(code)
    return _TraceEvaluationV1(
        M5CodexTraceSummaryV1(
            len(operations),
            accesses,
            writes,
            default_accesses,
            default_writes,
        ),
        chmods[0][1],
    )


def evaluate_codex_trace_policy_v1(
    trace: str,
    *,
    provider_executable: Path,
    managed_profile_root: Path,
    default_codex_roots: tuple[Path, ...],
) -> M5CodexTraceSummaryV1:
    """Pure fail-closed policy over a bounded file/process syscall trace."""

    return _evaluate_codex_trace_policy_v1(
        trace,
        provider_executable=provider_executable,
        managed_profile_root=managed_profile_root,
        default_codex_roots=default_codex_roots,
    ).summary


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
    if raw is None or re.fullmatch(r"(?:[3-9]|[1-9][0-9]{1,5})", raw) is None:
        raise M5CodexContainmentErrorV1("m5_codex_containment_private_channel_invalid")
    descriptor = int(raw)
    try:
        os.fstat(descriptor)
    except OSError:
        raise M5CodexContainmentErrorV1(
            "m5_codex_containment_private_channel_invalid"
        ) from None
    return descriptor


def _discover_containment_installation_v1() -> CodexInstallationV1:
    """Run the exact version probe without adding a traced setup chmod."""

    from agentmonitor.adapters.providers.codex.installation import (
        CodexInstallationUnavailable,
        CodexInstallationV1,
        _binary_identity,
        _read_bounded_stdout,
        _terminate_owned_process,
    )
    from agentmonitor.adapters.providers.codex.manifest import (
        CODEX_PROVIDER_VERSION,
    )
    from agentmonitor.contracts.common_v1 import OpaqueIdV1

    platform_id = f"{platform.system().lower()}-{platform.machine().lower()}"
    if platform_id != "linux-x86_64":
        raise CodexInstallationUnavailable("codex_platform_unverified")
    found = shutil.which("codex")
    if found is None or not Path(found).is_absolute():
        raise CodexInstallationUnavailable("codex_executable_unavailable")
    try:
        executable = Path(found).resolve(strict=True)
        identity = _binary_identity(executable)
    except OSError:
        raise CodexInstallationUnavailable("codex_executable_invalid") from None

    try:
        temporary_root = tempfile.TemporaryDirectory(
            prefix="agentmonitor-codex-version-"
        )
    except OSError:
        raise CodexInstallationUnavailable("codex_version_unavailable") from None
    with temporary_root as raw_root:
        root = Path(raw_root)
        try:
            root_info = root.lstat()
        except OSError:
            raise CodexInstallationUnavailable("codex_version_unavailable") from None
        if (
            not stat.S_ISDIR(root_info.st_mode)
            or root_info.st_uid != os.getuid()
            or stat.S_IMODE(root_info.st_mode) != 0o700
        ):
            raise CodexInstallationUnavailable("codex_version_unavailable")
        environment = {
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "NO_COLOR": "1",
            "HOME": str(root / "home"),
            "CODEX_HOME": str(root / "codex-home"),
            "XDG_CACHE_HOME": str(root / "cache"),
            "XDG_CONFIG_HOME": str(root / "config"),
            "XDG_DATA_HOME": str(root / "data"),
            "XDG_STATE_HOME": str(root / "state"),
        }
        try:
            process = subprocess.Popen(
                [str(executable), "--version"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=root,
                env=environment,
                shell=False,
                start_new_session=True,
            )
        except OSError:
            raise CodexInstallationUnavailable("codex_version_unavailable") from None
        try:
            output = _read_bounded_stdout(process)
        except CodexInstallationUnavailable:
            _terminate_owned_process(process)
            raise
        finally:
            if process.stdout is not None:
                try:
                    process.stdout.close()
                except (OSError, ValueError):
                    pass
        if process.returncode != 0:
            raise CodexInstallationUnavailable("codex_version_invalid")
        try:
            if any(root.iterdir()):
                raise CodexInstallationUnavailable("codex_version_side_effect_detected")
        except OSError:
            raise CodexInstallationUnavailable("codex_version_unavailable") from None

    match = re.fullmatch(rb"codex-cli ([0-9]+\.[0-9]+\.[0-9]+)\r?\n?", output)
    if match is None:
        raise CodexInstallationUnavailable("codex_version_invalid")
    provider_version = match.group(1).decode("ascii")
    try:
        if _binary_identity(executable) != identity:
            raise CodexInstallationUnavailable("codex_executable_changed")
    except OSError:
        raise CodexInstallationUnavailable("codex_executable_changed") from None
    if provider_version != CODEX_PROVIDER_VERSION:
        raise CodexInstallationUnavailable("codex_version_unverified")
    return CodexInstallationV1(
        installation_ref=OpaqueIdV1("codex-installation-primary"),
        provider_version=provider_version,
        platform_id=platform_id,
        _executable=executable,
        _identity=identity,
    )


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
            installation = _discover_containment_installation_v1()
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


def _validated_driver_result_payload(payload: bytes) -> dict[str, object]:
    decoded = _decode_unique_json(
        payload,
        code="m5_codex_containment_result_invalid",
    )
    if type(decoded) is not dict:
        raise M5CodexContainmentErrorV1("m5_codex_containment_result_invalid")
    value = cast(dict[str, object], decoded)
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
    if state in {"failed", "unavailable"}:
        if counts != (0, 0, 0, 0) or identity_binding_digest is not None:
            raise M5CodexContainmentErrorV1("m5_codex_containment_result_invalid")
        return value
    if (
        state != "passed"
        or counts[:2] != (1, 1)
        or cast(int, counts[2]) < 1
        or cast(int, counts[3]) < 1
        or type(identity_binding_digest) is not str
        or _SHA256.fullmatch(identity_binding_digest) is None
    ):
        raise M5CodexContainmentErrorV1("m5_codex_containment_result_invalid")
    return value


def _validate_driver_status(
    value: dict[str, object],
    returncode: int,
) -> None:
    state = value["state"]
    if returncode == 3 and state == "unavailable":
        raise M5CodexContainmentUnavailableV1(
            "m5_codex_containment_provider_unavailable"
        )
    if returncode == 2 and state == "failed":
        raise M5CodexContainmentErrorV1("m5_codex_containment_operation_failed")
    if returncode == 0 and state == "passed":
        return
    raise M5CodexContainmentErrorV1("m5_codex_containment_driver_status_invalid")


def _validated_driver_result(
    payload: bytes,
    returncode: int,
) -> dict[str, object]:
    value = _validated_driver_result_payload(payload)
    _validate_driver_status(value, returncode)
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
) -> _OwnedDriverProcessV1:
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
        _STRACE_SELECTOR_V1,
        "-e",
        _STRACE_RAW_V1,
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
        process = _start_containment_process(
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
        return _bind_owned_driver_process_group_v1(process)
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


def _bind_owned_driver_process_group_v1(
    process: subprocess.Popen[bytes],
) -> _OwnedDriverProcessV1:
    """Bind one new-session child before any operation can reap its leader."""

    pidfd = -1
    group_bound = False
    try:
        if process.returncode is not None or not 1 <= process.pid <= 2**31 - 1:
            raise OSError
        pidfd = os.pidfd_open(process.pid, 0)
        start_time_ticks = _process_start_ticks(process.pid)
        if (
            os.getpgid(process.pid) != process.pid
            or os.getsid(process.pid) != process.pid
        ):
            raise OSError
        group_bound = True
        if (
            process.returncode is not None
            or _process_start_ticks(process.pid) != start_time_ticks
        ):
            raise OSError
        return _OwnedDriverProcessV1(process, pidfd, start_time_ticks)
    except (M5CodexContainmentErrorV1, AttributeError, OSError):
        if group_bound:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except OSError:
                pass
        else:
            try:
                process.kill()
            except OSError:
                pass
        try:
            process.wait(timeout=_CHANNEL_SETTLEMENT_SECONDS)
        except (OSError, subprocess.TimeoutExpired):
            pass
        if pidfd >= 0:
            try:
                os.close(pidfd)
            except OSError:
                pass
        raise M5CodexContainmentUnavailableV1(
            "m5_codex_containment_driver_unavailable"
        ) from None


def _owned_driver_process_v1(
    process: subprocess.Popen[bytes] | _OwnedDriverProcessV1,
) -> _OwnedDriverProcessV1:
    if isinstance(process, _OwnedDriverProcessV1):
        return process
    return _bind_owned_driver_process_group_v1(process)


def _owned_driver_exit_observed_v1(
    process: _OwnedDriverProcessV1,
    *,
    deadline_monotonic: float,
) -> bool:
    if type(process) is not _OwnedDriverProcessV1 or process.pidfd < 0:
        raise M5CodexContainmentUnavailableV1(
            "m5_codex_containment_driver_deadline_exceeded"
        )
    try:
        readable, _, _ = select.select(
            [process.pidfd],
            [],
            [],
            max(0.0, deadline_monotonic - time.monotonic()),
        )
    except (OSError, ValueError):
        raise M5CodexContainmentUnavailableV1(
            "m5_codex_containment_driver_deadline_exceeded"
        ) from None
    return readable == [process.pidfd]


def _signal_owned_driver_process_group_v1(
    process: _OwnedDriverProcessV1,
) -> None:
    """Signal the bound group while its leader remains deliberately unreaped."""

    if (
        type(process) is not _OwnedDriverProcessV1
        or process.pidfd < 0
        or process.process.returncode is not None
    ):
        raise M5CodexContainmentUnavailableV1(
            "m5_codex_containment_driver_deadline_exceeded"
        )
    try:
        if (
            _process_start_ticks(process.process.pid) != process.start_time_ticks
            or os.getpgid(process.process.pid) != process.process.pid
            or os.getsid(process.process.pid) != process.process.pid
        ):
            raise OSError
        os.killpg(process.process.pid, signal.SIGKILL)
    except ProcessLookupError:
        if not _owned_driver_exit_observed_v1(
            process,
            deadline_monotonic=time.monotonic(),
        ):
            raise M5CodexContainmentUnavailableV1(
                "m5_codex_containment_driver_deadline_exceeded"
            ) from None
    except (M5CodexContainmentErrorV1, OSError):
        raise M5CodexContainmentUnavailableV1(
            "m5_codex_containment_driver_deadline_exceeded"
        ) from None


def _terminate_and_reap_driver_process_group_v1(
    process: subprocess.Popen[bytes] | _OwnedDriverProcessV1,
    *,
    deadline_monotonic: float | None = None,
) -> None:
    """Signal the bound group before reaping its leader, then close the pidfd."""

    owned = _owned_driver_process_v1(process)
    if owned.pidfd < 0:
        if owned.process.returncode is None:
            raise M5CodexContainmentUnavailableV1(
                "m5_codex_containment_driver_deadline_exceeded"
            )
        return
    failed = False
    try:
        try:
            _signal_owned_driver_process_group_v1(owned)
        except M5CodexContainmentUnavailableV1:
            failed = True
        deadline = (
            time.monotonic() + _CHANNEL_SETTLEMENT_SECONDS
            if deadline_monotonic is None
            else deadline_monotonic
        )
        try:
            exited = _owned_driver_exit_observed_v1(
                owned,
                deadline_monotonic=deadline,
            )
        except M5CodexContainmentUnavailableV1:
            exited = False
            failed = True
        if not exited:
            failed = True
        else:
            try:
                owned.process.wait(
                    timeout=max(0.0, deadline - time.monotonic()),
                )
            except (OSError, subprocess.TimeoutExpired):
                failed = True
    finally:
        descriptor = owned.pidfd
        owned.pidfd = -1
        try:
            os.close(descriptor)
        except OSError:
            failed = True
    if failed or owned.process.returncode is None:
        raise M5CodexContainmentUnavailableV1(
            "m5_codex_containment_driver_deadline_exceeded"
        ) from None


def _input_future_outcome(
    future: Future[_InputChannelOutcomeV1] | None,
    *,
    late_futures: set[object],
) -> _InputChannelOutcomeV1:
    if future is None:
        return _InputChannelOutcomeV1("invalid")
    if future in late_futures:
        return _InputChannelOutcomeV1("late")
    try:
        if future.cancelled() or future.exception(timeout=0) is not None:
            return _InputChannelOutcomeV1("invalid")
        outcome = future.result(timeout=0)
    except (CancelledError, TimeoutError):
        return _InputChannelOutcomeV1("invalid")
    if type(outcome) is not _InputChannelOutcomeV1 or outcome.state not in {
        "complete",
        "invalid",
        "late",
    }:
        return _InputChannelOutcomeV1("invalid")
    return outcome


def _output_future_outcome(
    future: Future[_OutputChannelOutcomeV1] | None,
    *,
    late_futures: set[object],
    maximum: int,
) -> _OutputChannelOutcomeV1:
    if future is None:
        return _OutputChannelOutcomeV1("invalid")
    if future in late_futures:
        return _OutputChannelOutcomeV1("late")
    try:
        if future.cancelled() or future.exception(timeout=0) is not None:
            return _OutputChannelOutcomeV1("invalid")
        outcome = future.result(timeout=0)
    except (CancelledError, TimeoutError):
        return _OutputChannelOutcomeV1("invalid")
    if type(outcome) is not _OutputChannelOutcomeV1:
        return _OutputChannelOutcomeV1("invalid")
    if outcome.state == "payload":
        if (
            type(outcome.payload) is not bytes
            or not 1 <= len(outcome.payload) <= maximum
        ):
            return _OutputChannelOutcomeV1("invalid")
        return outcome
    if outcome.state in {"empty", "invalid", "late"} and outcome.payload is None:
        return outcome
    return _OutputChannelOutcomeV1("invalid")


def _classify_driver_channels(
    *,
    driver_deadline_exceeded: bool,
    returncode: int,
    input_outcome: _InputChannelOutcomeV1,
    result_outcome: _OutputChannelOutcomeV1,
    trace_outcome: _OutputChannelOutcomeV1,
) -> tuple[int, bytes, bytes]:
    if driver_deadline_exceeded:
        raise M5CodexContainmentUnavailableV1(
            "m5_codex_containment_driver_deadline_exceeded"
        )
    if result_outcome.state == "empty":
        raise M5CodexContainmentErrorV1("m5_codex_containment_result_channel_empty")
    if result_outcome.state != "payload":
        raise M5CodexContainmentErrorV1("m5_codex_containment_result_channel_invalid")
    if trace_outcome.state == "empty":
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_channel_empty")
    if trace_outcome.state != "payload":
        raise M5CodexContainmentErrorV1("m5_codex_containment_trace_channel_invalid")
    result_payload = cast(bytes, result_outcome.payload)
    trace_payload = cast(bytes, trace_outcome.payload)
    result = _validated_driver_result_payload(result_payload)
    if input_outcome.state != "complete":
        raise M5CodexContainmentErrorV1("m5_codex_containment_input_channel_invalid")
    _validate_driver_status(result, returncode)
    return returncode, result_payload, trace_payload


def _collect_driver_channels_until(
    process: subprocess.Popen[bytes] | _OwnedDriverProcessV1,
    *,
    input_descriptor: int,
    input_payload: bytes,
    result_descriptor: int,
    trace_descriptor: int,
    driver_deadline_monotonic: float,
) -> tuple[int, bytes, bytes]:
    """Drain three channels under one driver and one settlement deadline."""

    owned_process = _owned_driver_process_v1(process)
    settlement = _ChannelSettlementV1()
    input_channel = _OwnedPrivateChannelV1(input_descriptor)
    result_channel = _OwnedPrivateChannelV1(result_descriptor)
    trace_channel = _OwnedPrivateChannelV1(trace_descriptor)
    executor: ThreadPoolExecutor | None = None
    input_future: Future[_InputChannelOutcomeV1] | None = None
    result_future: Future[_OutputChannelOutcomeV1] | None = None
    trace_future: Future[_OutputChannelOutcomeV1] | None = None
    late_futures: set[object] = set()
    returncode = -1
    driver_deadline_exceeded = False
    submission_failed = False
    input_outcome = _InputChannelOutcomeV1("invalid")
    result_outcome = _OutputChannelOutcomeV1("invalid")
    trace_outcome = _OutputChannelOutcomeV1("invalid")
    try:
        try:
            executor = ThreadPoolExecutor(max_workers=3)
            input_future = executor.submit(
                _write_private_channel_nonblocking,
                input_channel,
                input_payload,
                maximum=_INPUT_LIMIT_BYTES,
                settlement=settlement,
            )
            result_future = executor.submit(
                _read_private_channel_nonblocking,
                result_channel,
                maximum=_RESULT_LIMIT_BYTES,
                settlement=settlement,
            )
            trace_future = executor.submit(
                _read_private_channel_nonblocking,
                trace_channel,
                maximum=_TRACE_LIMIT_BYTES,
                settlement=settlement,
            )
        except (MemoryError, OSError, RuntimeError):
            submission_failed = True
            try:
                _signal_owned_driver_process_group_v1(owned_process)
            except M5CodexContainmentUnavailableV1:
                driver_deadline_exceeded = True

        if not submission_failed:
            try:
                driver_exited = _owned_driver_exit_observed_v1(
                    owned_process,
                    deadline_monotonic=driver_deadline_monotonic,
                )
            except M5CodexContainmentUnavailableV1:
                driver_exited = False
            if not driver_exited:
                driver_deadline_exceeded = True
                try:
                    _signal_owned_driver_process_group_v1(owned_process)
                except M5CodexContainmentUnavailableV1:
                    pass

        settlement_deadline = settlement.begin()
        if submission_failed or driver_deadline_exceeded:
            try:
                driver_exited = _owned_driver_exit_observed_v1(
                    owned_process,
                    deadline_monotonic=settlement_deadline,
                )
            except M5CodexContainmentUnavailableV1:
                driver_exited = False
            if not driver_exited:
                driver_deadline_exceeded = True

        futures = {
            cast(Future[object], future)
            for future in (input_future, result_future, trace_future)
            if future is not None
        }
        _done, pending = wait(
            futures,
            timeout=max(0.0, settlement_deadline - time.monotonic()),
        )
        late_futures.update(pending)
        if pending:
            try:
                _signal_owned_driver_process_group_v1(owned_process)
            except M5CodexContainmentUnavailableV1:
                driver_deadline_exceeded = True
        settlement.cancel()
        input_channel.close()
        result_channel.close()
        trace_channel.close()

        input_outcome = _input_future_outcome(
            input_future,
            late_futures=late_futures,
        )
        result_outcome = _output_future_outcome(
            result_future,
            late_futures=late_futures,
            maximum=_RESULT_LIMIT_BYTES,
        )
        trace_outcome = _output_future_outcome(
            trace_future,
            late_futures=late_futures,
            maximum=_TRACE_LIMIT_BYTES,
        )
    finally:
        settlement.cancel()
        input_channel.close()
        result_channel.close()
        trace_channel.close()
        for future in (input_future, result_future, trace_future):
            if future is not None:
                future.cancel()
        if executor is not None:
            executor.shutdown(wait=False, cancel_futures=True)
        try:
            _terminate_and_reap_driver_process_group_v1(
                owned_process,
                deadline_monotonic=settlement_deadline,
            )
        except M5CodexContainmentUnavailableV1:
            driver_deadline_exceeded = True
        observed_returncode = owned_process.process.returncode
        if type(observed_returncode) is int:
            returncode = observed_returncode

    return _classify_driver_channels(
        driver_deadline_exceeded=driver_deadline_exceeded,
        returncode=returncode,
        input_outcome=input_outcome,
        result_outcome=result_outcome,
        trace_outcome=trace_outcome,
    )


def _collect_driver_channels(
    process: subprocess.Popen[bytes] | _OwnedDriverProcessV1,
    *,
    input_descriptor: int,
    input_payload: bytes,
    result_descriptor: int,
    trace_descriptor: int,
) -> tuple[int, bytes, bytes]:
    """Use the production driver deadline through the absolute-deadline seam."""

    return _collect_driver_channels_until(
        process,
        input_descriptor=input_descriptor,
        input_payload=input_payload,
        result_descriptor=result_descriptor,
        trace_descriptor=trace_descriptor,
        driver_deadline_monotonic=time.monotonic() + _DRIVER_TIMEOUT_SECONDS,
    )


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
    _validate_strace_selector_v1()
    default_roots = _default_codex_roots(selection.owner_data_root)
    owner_info = _private_directory(
        selection.owner_data_root,
        "m5_codex_containment_selection_invalid",
    )
    owner_identity = _inode_identity(owner_info)
    profiles_root_identity = _inode_identity(
        _private_directory(
            selection.profiles_root,
            "m5_codex_containment_selection_invalid",
        )
    )
    managed_profiles_identity = _inode_identity(
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
    profile_root_descriptor = -1
    target_descriptor = -1
    process: _OwnedDriverProcessV1 | None = None
    try:
        profile_root_descriptor, pinned_profile_identity = _open_pinned_profile_root(
            selection.managed_profile_root,
            expected_identity=profile_identity,
        )
        mount_topology_before = _mount_topology_snapshot_v1(
            selection.managed_profile_root
        )
        profile_tree_before_snapshot = _managed_profile_tree_snapshot(
            selection.managed_profile_root,
            expected_root_identity=pinned_profile_identity,
        )
        profile_tree_before = profile_tree_before_snapshot.digest
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
        try:
            driver_exited = _owned_driver_exit_observed_v1(
                process,
                deadline_monotonic=time.monotonic(),
            )
        except M5CodexContainmentUnavailableV1:
            raise _mount_topology_error() from None
        if driver_exited:
            raise _mount_topology_error()
        traced_mount_topology = _mount_topology_snapshot_v1(
            selection.managed_profile_root,
            process_id=process.process.pid,
            expected_process_start_time_ticks=process.start_time_ticks,
        )
        try:
            driver_exited = _owned_driver_exit_observed_v1(
                process,
                deadline_monotonic=time.monotonic(),
            )
        except M5CodexContainmentUnavailableV1:
            raise _mount_topology_error() from None
        if driver_exited:
            raise _mount_topology_error()
        _require_same_mount_topology_v1(
            mount_topology_before,
            traced_mount_topology,
        )
        os.close(input_reader)
        input_reader = -1
        os.close(result_writer)
        result_writer = -1
        os.close(trace_writer)
        trace_writer = -1
        owned_input_writer = input_writer
        input_writer = -1
        owned_result_reader = result_reader
        result_reader = -1
        owned_trace_reader = trace_reader
        trace_reader = -1
        returncode, result_payload, trace_payload = _collect_driver_channels(
            process,
            input_descriptor=owned_input_writer,
            input_payload=selection_payload,
            result_descriptor=owned_result_reader,
            trace_descriptor=owned_trace_reader,
        )
        mount_topology_after = _mount_topology_snapshot_v1(
            selection.managed_profile_root
        )
        _require_same_mount_topology_v1(
            mount_topology_before,
            mount_topology_after,
        )
        result = _validated_driver_result(result_payload, returncode)
        try:
            trace = trace_payload.decode("utf-8")
        except UnicodeError:
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_trace_invalid"
            ) from None
        trace_evaluation = _evaluate_codex_trace_policy_v1(
            trace,
            provider_executable=executable.path,
            managed_profile_root=selection.managed_profile_root,
            default_codex_roots=default_roots,
        )
        summary = trace_evaluation.summary
        target_descriptor, walked_target = _open_inode_bound_chmod_target(
            profile_root_descriptor,
            trace_evaluation.admitted_chmod_relative_parts,
            profile_tree_before_snapshot,
        )
        profile_tree_after_snapshot = _managed_profile_tree_snapshot(
            selection.managed_profile_root,
            expected_root_identity=pinned_profile_identity,
        )
        _validate_inode_bound_chmod(
            target_descriptor,
            trace_evaluation.admitted_chmod_relative_parts,
            walked_target,
            profile_tree_before_snapshot,
            profile_tree_after_snapshot,
        )
        profile_tree_after = profile_tree_after_snapshot.digest
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
            or profiles_root_identity
            != _inode_identity(
                _private_directory(
                    selection.profiles_root,
                    "m5_codex_containment_selection_changed",
                )
            )
            or managed_profiles_identity
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
            "profiles_root_identity": profiles_root_identity,
            "managed_profiles_identity": managed_profiles_identity,
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
        cleanup_error: M5CodexContainmentUnavailableV1 | None = None
        if process is not None:
            try:
                _terminate_and_reap_driver_process_group_v1(process)
            except M5CodexContainmentUnavailableV1 as error:
                cleanup_error = error
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
        pin_close_failed = False
        for descriptor in (target_descriptor, profile_root_descriptor):
            if descriptor >= 0:
                try:
                    _close_pinned_descriptor_v1(descriptor)
                except M5CodexContainmentErrorV1:
                    pin_close_failed = True
        if pin_close_failed and sys.exc_info()[0] is None:
            raise M5CodexContainmentErrorV1(
                "m5_codex_containment_path_mutator_unverifiable"
            )
        if cleanup_error is not None:
            raise cleanup_error from None


if __name__ == "__main__":
    if sys.argv == [sys.argv[0], "--driver"]:
        raise SystemExit(_driver_main())
    raise SystemExit(2)

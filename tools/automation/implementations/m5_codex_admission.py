"""Independent real-system admission for the exact M5 Codex CLI tuple.

This verifier deliberately does not import the production Codex adapter. It
executes the installed binary in an isolated temporary ``CODEX_HOME``, binds
the generated non-experimental schemas to discovery evidence, and uses the
real Linux syscall boundary to reject access to protected default-profile
state.
"""

from __future__ import annotations

import hashlib
import os
import platform
import pwd
import re
import selectors
import shutil
import signal
import stat
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DISCOVERY_EVIDENCE = ROOT / "docs/evidence/m5-codex-0.160.0-discovery.md"
MAPPING_EVIDENCE = ROOT / "docs/evidence/m5-codex-read-side-effect-blocker.md"
EXPECTED_PROVIDER_VERSION = "0.160.0"
EXPECTED_VERSION_BANNER = b"codex-cli 0.160.0\n"
EXPECTED_MAPPING_DIGEST = (
    "2ac086063dbfdae1c673f7cd899ac60d6d559bc72dbb598c6e5196c43567a204"
)
EXPECTED_SCHEMA_BUNDLE_DIGEST = (
    "36bd8e1d76b12b89b06446a85c45e957945eb8cb63b05061264c3dec97f625da"
)
EXPECTED_SCHEMA_DIGESTS = (
    (
        "v2/GetAccountParams.json",
        "30b545275f60975b55bd6fbaafd70f15505801d14168ee82d3931b6e93c78aab",
    ),
    (
        "v2/GetAccountResponse.json",
        "c3092dd8e52c2933c5ba5f0bf92377174f65bed627ff4ef5d7c04a189dd34fd1",
    ),
    (
        "v2/NullableGetAccountRateLimitsParams.json",
        "072f813ca1c696831a7f2fbd934feaa8cad228a6b3d44a4be8877547c796341b",
    ),
    (
        "v2/GetAccountRateLimitsResponse.json",
        "cb9655e68130116f634ed9353e45b336492e6069a6628f424d1cd52e54eda0e0",
    ),
)

_STRACE = Path("/usr/bin/strace")
_VERSION_OUTPUT_LIMIT_BYTES = 128
_TRACE_LIMIT_BYTES = 4 * 1024 * 1024
_SCHEMA_LIMIT_BYTES = 2 * 1024 * 1024
_EVIDENCE_LIMIT_BYTES = 128 * 1024
_TRACE_CALL = re.compile(r"(?:\[pid\s+\d+\]|\d+)\s+([A-Za-z0-9_]+)\(")
_TRACE_QUOTED = re.compile(r'"((?:[^"\\]|\\.)*)"')
_WRITE_FLAGS = ("O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC", "O_APPEND")
_WRITE_CALLS = frozenset(
    {
        "chmod",
        "chown",
        "fchmodat",
        "fchownat",
        "link",
        "linkat",
        "lchown",
        "mkdir",
        "mkdirat",
        "mknod",
        "rename",
        "renameat",
        "renameat2",
        "rmdir",
        "symlink",
        "symlinkat",
        "truncate",
        "unlink",
        "unlinkat",
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


class M5CodexAdmissionErrorV1(RuntimeError):
    """One sanitized exact-admission failure."""


class M5CodexAdmissionUnavailableV1(M5CodexAdmissionErrorV1):
    """A missing real platform/tool prerequisite that blocks admission."""


@dataclass(frozen=True, slots=True)
class M5CodexAdmissionEvidenceV1:
    """Sanitized facts safe to bind into the private M5 gate receipt."""

    provider_version: str
    schema_bundle_digest: str
    mapping_digest: str
    schema_count: int
    experimental_schema_mode: bool
    default_profile_access_count: int
    default_profile_write_count: int


type _ExecutableIdentityV1 = tuple[int, int, int, int, int, int, int, int]


def _executable_identity(executable: Path) -> _ExecutableIdentityV1:
    try:
        info = executable.lstat()
    except OSError:
        raise M5CodexAdmissionErrorV1("m5_codex_executable_invalid") from None
    if (
        executable.name != "codex"
        or not stat.S_ISREG(info.st_mode)
        or info.st_uid not in {0, os.getuid()}
        or info.st_mode & 0o022
        or not os.access(executable, os.X_OK)
    ):
        raise M5CodexAdmissionErrorV1("m5_codex_executable_invalid")
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
) -> tuple[Path, _ExecutableIdentityV1]:
    selected_system = platform.system() if system_name is None else system_name
    selected_machine = platform.machine() if machine_name is None else machine_name
    if selected_system != "Linux" or selected_machine != "x86_64":
        raise M5CodexAdmissionUnavailableV1("m5_codex_platform_unverified")
    found = shutil.which("codex", path=search_path)
    if found is None or not Path(found).is_absolute():
        raise M5CodexAdmissionUnavailableV1("m5_codex_executable_unavailable")
    try:
        executable = Path(found).resolve(strict=True)
    except OSError:
        raise M5CodexAdmissionErrorV1("m5_codex_executable_invalid") from None
    return executable, _executable_identity(executable)


def _private_directory(path: Path) -> Path:
    path.mkdir(mode=0o700)
    path.chmod(0o700)
    return path


def _isolated_environment(root: Path) -> dict[str, str]:
    return {
        "CODEX_HOME": str(_private_directory(root / "codex-home")),
        "HOME": str(_private_directory(root / "home")),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "NO_COLOR": "1",
        "PATH": "/usr/bin:/bin",
        "XDG_CACHE_HOME": str(_private_directory(root / "cache")),
        "XDG_CONFIG_HOME": str(_private_directory(root / "config")),
        "XDG_DATA_HOME": str(_private_directory(root / "data")),
        "XDG_STATE_HOME": str(_private_directory(root / "state")),
    }


def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=2)
    except (OSError, ProcessLookupError, subprocess.TimeoutExpired):
        pass


def _read_bounded_stdout(
    process: subprocess.Popen[bytes], *, deadline: float, maximum: int
) -> bytes:
    if process.stdout is None:
        raise M5CodexAdmissionErrorV1("m5_codex_version_unavailable")
    output = bytearray()
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise M5CodexAdmissionErrorV1("m5_codex_command_deadline_exceeded")
            events = selector.select(remaining)
            if not events:
                raise M5CodexAdmissionErrorV1("m5_codex_command_deadline_exceeded")
            chunk = os.read(process.stdout.fileno(), maximum + 1 - len(output))
            if not chunk:
                break
            output.extend(chunk)
            if len(output) > maximum:
                raise M5CodexAdmissionErrorV1("m5_codex_version_output_invalid")
    return bytes(output)


def _bounded_trace(path: Path) -> str:
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or not 1 <= info.st_size <= _TRACE_LIMIT_BYTES
        ):
            raise OSError
        payload = os.read(descriptor, _TRACE_LIMIT_BYTES + 1)
        if len(payload) != info.st_size:
            raise OSError
        return payload.decode("utf-8")
    except (OSError, UnicodeError):
        raise M5CodexAdmissionErrorV1("m5_codex_trace_invalid") from None
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _validate_strace_executable(path: Path) -> None:
    try:
        strace_info = path.lstat()
    except OSError:
        raise M5CodexAdmissionUnavailableV1("m5_codex_strace_unavailable") from None
    if (
        not stat.S_ISREG(strace_info.st_mode)
        or strace_info.st_uid != 0
        or strace_info.st_mode & 0o022
        or not os.access(path, os.X_OK)
    ):
        raise M5CodexAdmissionUnavailableV1("m5_codex_strace_unavailable")


def _start_admission_process(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    stdout: int,
) -> subprocess.Popen[bytes]:
    try:
        return subprocess.Popen(
            command,
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=subprocess.DEVNULL,
            shell=False,
            start_new_session=True,
        )
    except OSError:
        raise M5CodexAdmissionUnavailableV1("m5_codex_command_unavailable") from None


def _run_traced(
    executable: Path,
    arguments: tuple[str, ...],
    *,
    root: Path,
    environment: dict[str, str],
    trace_name: str,
    timeout_seconds: float,
    capture_version: bool,
) -> tuple[bytes, str]:
    _validate_strace_executable(_STRACE)
    trace_path = root / trace_name
    command = [
        str(_STRACE),
        "-f",
        "-qq",
        "-s",
        "4096",
        "-e",
        "trace=%file",
        "-o",
        str(trace_path),
        str(executable),
        *arguments,
    ]
    process = _start_admission_process(
        command,
        cwd=root,
        environment=environment,
        stdout=subprocess.PIPE if capture_version else subprocess.DEVNULL,
    )
    deadline = time.monotonic() + timeout_seconds
    try:
        output = (
            _read_bounded_stdout(
                process,
                deadline=deadline,
                maximum=_VERSION_OUTPUT_LIMIT_BYTES,
            )
            if capture_version
            else b""
        )
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise M5CodexAdmissionErrorV1("m5_codex_command_deadline_exceeded")
        process.wait(timeout=remaining)
    except subprocess.TimeoutExpired:
        _terminate_process_group(process)
        raise M5CodexAdmissionErrorV1("m5_codex_command_deadline_exceeded") from None
    except M5CodexAdmissionErrorV1:
        _terminate_process_group(process)
        raise
    finally:
        if process.stdout is not None:
            process.stdout.close()
    if process.returncode != 0:
        raise M5CodexAdmissionErrorV1("m5_codex_command_failed")
    trace = _bounded_trace(trace_path)
    if f'execve("{executable}"' not in trace:
        raise M5CodexAdmissionErrorV1("m5_codex_trace_invalid")
    return output, trace


def _trace_paths(line: str) -> tuple[Path, ...]:
    paths: list[Path] = []
    for value in _TRACE_QUOTED.findall(line):
        if not value.startswith("/") or "\\" in value:
            continue
        paths.append(Path(os.path.normpath(value)))
    return tuple(paths)


def _trace_call(line: str) -> str | None:
    match = _TRACE_CALL.match(line)
    return None if match is None else match.group(1)


def _trace_is_write(line: str, call: str | None) -> bool:
    return (call in _WRITE_CALLS if call is not None else False) or any(
        flag in line for flag in _WRITE_FLAGS
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


def _is_within(candidate: Path, parent: Path) -> bool:
    return candidate == parent or parent in candidate.parents


def _validate_trace_boundary(
    trace: str, *, temporary_root: Path, executable: Path
) -> tuple[int, int]:
    """Reject protected profile access and every write outside the isolated root."""

    default_root = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".codex"
    release_root = _installation_release_root(executable, default_root)
    profile_accesses = 0
    profile_writes = 0
    for line in trace.splitlines():
        call = _trace_call(line)
        is_write = _trace_is_write(line, call)
        for candidate in _trace_paths(line):
            if is_write and not _is_within(candidate, temporary_root):
                raise M5CodexAdmissionErrorV1(
                    "m5_codex_admission_write_boundary_invalid"
                )
            if not _is_within(candidate, default_root):
                continue
            if is_write:
                profile_writes += 1
                continue
            is_release_read = release_root is not None and _is_within(
                candidate, release_root
            )
            is_release_ancestor_metadata = (
                release_root is not None
                and candidate in release_root.parents
                and _is_within(candidate, default_root)
                and call in _METADATA_CALLS
            )
            if not (is_release_read or is_release_ancestor_metadata):
                profile_accesses += 1
    if profile_accesses or profile_writes:
        raise M5CodexAdmissionErrorV1("m5_codex_default_profile_access_detected")
    return profile_accesses, profile_writes


def _read_bounded_regular_file(path: Path, *, maximum: int, code: str) -> bytes:
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or not 1 <= info.st_size <= maximum
        ):
            raise OSError
        payload = os.read(descriptor, maximum + 1)
        if len(payload) != info.st_size:
            raise OSError
        return payload
    except OSError:
        raise M5CodexAdmissionErrorV1(code) from None
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _validate_evidence_files() -> str:
    discovery = _read_bounded_regular_file(
        DISCOVERY_EVIDENCE,
        maximum=_EVIDENCE_LIMIT_BYTES,
        code="m5_codex_discovery_evidence_invalid",
    )
    try:
        discovery_text = discovery.decode("utf-8")
    except UnicodeError:
        raise M5CodexAdmissionErrorV1("m5_codex_discovery_evidence_invalid") from None
    expected_rows = tuple(
        f"| `{name}` | `{digest}` |" for name, digest in EXPECTED_SCHEMA_DIGESTS
    ) + (
        (
            "| Ordered four-schema admission bundle | "
            f"`{EXPECTED_SCHEMA_BUNDLE_DIGEST}` |"
        ),
    )
    if any(discovery_text.count(row) != 1 for row in expected_rows):
        raise M5CodexAdmissionErrorV1("m5_codex_discovery_evidence_invalid")
    mapping = _read_bounded_regular_file(
        MAPPING_EVIDENCE,
        maximum=_EVIDENCE_LIMIT_BYTES,
        code="m5_codex_mapping_evidence_invalid",
    )
    mapping_digest = hashlib.sha256(mapping).hexdigest()
    if mapping_digest != EXPECTED_MAPPING_DIGEST:
        raise M5CodexAdmissionErrorV1("m5_codex_mapping_evidence_invalid")
    return mapping_digest


def _read_admitted_schemas(schema_root: Path) -> tuple[tuple[str, bytes], ...]:
    admitted: list[tuple[str, bytes]] = []
    for relative, expected_digest in EXPECTED_SCHEMA_DIGESTS:
        candidate = schema_root / relative
        try:
            if candidate.resolve(strict=True).relative_to(schema_root) != Path(
                relative
            ):
                raise OSError
        except (OSError, ValueError):
            raise M5CodexAdmissionErrorV1("m5_codex_schema_invalid") from None
        content = _read_bounded_regular_file(
            candidate,
            maximum=_SCHEMA_LIMIT_BYTES,
            code="m5_codex_schema_invalid",
        )
        if hashlib.sha256(content).hexdigest() != expected_digest:
            raise M5CodexAdmissionErrorV1("m5_codex_schema_digest_mismatch")
        admitted.append((relative, content))
    return tuple(admitted)


def _ordered_schema_bundle_digest(schemas: tuple[tuple[str, bytes], ...]) -> str:
    digest = hashlib.sha256()
    for relative, content in schemas:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")
    return digest.hexdigest()


def verify_codex_admission_v1() -> M5CodexAdmissionEvidenceV1:
    """Regenerate and verify the exact admitted real Codex schema tuple."""

    mapping_digest = _validate_evidence_files()
    executable, identity = _resolve_executable()
    with tempfile.TemporaryDirectory(prefix="agentmonitor-m5-codex-admission-") as raw:
        temporary_root = Path(raw)
        temporary_root.chmod(0o700)
        environment = _isolated_environment(temporary_root)
        version_output, version_trace = _run_traced(
            executable,
            ("--version",),
            root=temporary_root,
            environment=environment,
            trace_name="version.trace",
            timeout_seconds=3.0,
            capture_version=True,
        )
        version_accesses, version_writes = _validate_trace_boundary(
            version_trace,
            temporary_root=temporary_root,
            executable=executable,
        )
        if version_output not in {
            EXPECTED_VERSION_BANNER,
            EXPECTED_VERSION_BANNER.rstrip(b"\n"),
        }:
            raise M5CodexAdmissionErrorV1("m5_codex_version_unverified")
        schema_root = _private_directory(temporary_root / "schemas")
        _, schema_trace = _run_traced(
            executable,
            ("app-server", "generate-json-schema", "--out", str(schema_root)),
            root=temporary_root,
            environment=environment,
            trace_name="schema.trace",
            timeout_seconds=30.0,
            capture_version=False,
        )
        schema_accesses, schema_writes = _validate_trace_boundary(
            schema_trace,
            temporary_root=temporary_root,
            executable=executable,
        )
        schemas = _read_admitted_schemas(schema_root)
        bundle_digest = _ordered_schema_bundle_digest(schemas)
        if bundle_digest != EXPECTED_SCHEMA_BUNDLE_DIGEST:
            raise M5CodexAdmissionErrorV1("m5_codex_schema_bundle_mismatch")
        if _executable_identity(executable) != identity:
            raise M5CodexAdmissionErrorV1("m5_codex_executable_changed")
    return M5CodexAdmissionEvidenceV1(
        provider_version=EXPECTED_PROVIDER_VERSION,
        schema_bundle_digest=bundle_digest,
        mapping_digest=mapping_digest,
        schema_count=len(schemas),
        experimental_schema_mode=False,
        default_profile_access_count=version_accesses + schema_accesses,
        default_profile_write_count=version_writes + schema_writes,
    )

"""Bounded discovery of the exact installed Claude executable version."""

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
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from agentmonitor.adapters.providers.claude.manifest import (
    CLAUDE_OTEL_PROVIDER_VERSION,
    CLAUDE_PROVIDER_VERSION,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1

_VERSION = re.compile(rb"([0-9]+\.[0-9]+\.[0-9]+) \(Claude Code\)\s*\Z")
_NATIVE_VERSION_NAME = re.compile(
    r"(?:0|[1-9][0-9]{0,5})\."
    r"(?:0|[1-9][0-9]{0,5})\."
    r"(?:0|[1-9][0-9]{0,5})\Z"
)
_VERSION_TIMEOUT_SECONDS = 3.0
_VERSION_OUTPUT_LIMIT_BYTES = 128
_PROCESS_DISCOVERY_SECONDS = 2.0
_PROCESS_DIRECTORY_ENTRY_LIMIT = 256
_PROCESS_INSTALLATION_LIMIT = 32
type ClaudeExecutableIdentityV1 = tuple[int, int, int, int, int, int, int, int]


class ClaudeInstallationUnavailable(RuntimeError):
    """The required exact local installation cannot be safely used."""


@dataclass(frozen=True, slots=True)
class ClaudeInstallationV1:
    """Private adapter installation handle; executable path never leaves A01."""

    installation_ref: OpaqueIdV1
    provider_version: str
    platform_id: str
    _executable: Path = field(repr=False)
    _identity: ClaudeExecutableIdentityV1 | None = field(
        default=None, repr=False, compare=False
    )

    @property
    def executable_for_adapter(self) -> Path:
        self._revalidate_executable("claude_executable_changed")
        return self._executable

    def _revalidate_executable(self, reason_code: str) -> None:
        if self._identity is None:
            raise ClaudeInstallationUnavailable(reason_code)
        try:
            current = _binary_identity(self._executable)
        except (OSError, ClaudeInstallationUnavailable):
            raise ClaudeInstallationUnavailable(reason_code) from None
        if current != self._identity:
            raise ClaudeInstallationUnavailable(reason_code)

    def executable_for_process_observation(
        self,
    ) -> tuple[Path, ClaudeExecutableIdentityV1]:
        """Revalidate and carry the discovered image into A04 composition."""
        self._revalidate_executable("claude_process_executable_changed")
        assert self._identity is not None
        return self._executable, self._identity


def discover_default_installation(
    *, verified_provider_version: str = CLAUDE_PROVIDER_VERSION
) -> ClaudeInstallationV1:
    """Resolve the accepted installed Claude version without changing defaults.

    Claude's native installer retains earlier versioned executables when it
    advances the ``claude`` symlink. Prefer the current command only when it
    matches the requested capability's reviewed tuple; otherwise inspect that
    one exact native version path. This never rewrites the symlink or profile.
    """
    if verified_provider_version not in {
        CLAUDE_PROVIDER_VERSION,
        CLAUDE_OTEL_PROVIDER_VERSION,
    }:
        raise ClaudeInstallationUnavailable("claude_version_unverified")
    found = shutil.which("claude")
    if found is None:
        raise ClaudeInstallationUnavailable("claude_executable_unavailable")
    platform_id = f"{platform.system().lower()}-{platform.machine().lower()}"
    if platform_id != "linux-x86_64":
        raise ClaudeInstallationUnavailable("claude_platform_unverified")

    native_version = (
        Path(pwd.getpwuid(os.getuid()).pw_dir)
        / ".local"
        / "share"
        / "claude"
        / "versions"
        / verified_provider_version
    )
    candidates = (Path(found), native_version)
    saw_executable = False
    for candidate in candidates:
        try:
            executable = candidate.resolve(strict=True)
        except OSError:
            continue
        if not executable.is_file() or not os.access(executable, os.X_OK):
            continue
        saw_executable = True
        try:
            identity = _binary_identity(executable)
        except (OSError, ClaudeInstallationUnavailable):
            continue
        provider_version = _read_version(executable)
        try:
            if _binary_identity(executable) != identity:
                raise ClaudeInstallationUnavailable("claude_executable_changed")
        except OSError:
            raise ClaudeInstallationUnavailable("claude_executable_changed") from None
        if provider_version != verified_provider_version:
            continue
        return ClaudeInstallationV1(
            installation_ref=OpaqueIdV1("claude-installation-default"),
            provider_version=provider_version,
            platform_id=platform_id,
            _executable=executable,
            _identity=identity,
        )
    if saw_executable:
        raise ClaudeInstallationUnavailable("claude_version_unverified")
    raise ClaudeInstallationUnavailable("claude_executable_invalid")


def _read_version(executable: Path) -> str:
    """Read at most 128 bytes from one isolated real ``claude --version``."""
    with tempfile.TemporaryDirectory(prefix="agentmonitor-claude-version-") as raw_root:
        root = Path(raw_root)
        root.chmod(0o700)
        environment = {
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "NO_COLOR": "1",
            "HOME": str(root / "home"),
            "XDG_CACHE_HOME": str(root / "cache"),
            "XDG_CONFIG_HOME": str(root / "config"),
            "XDG_DATA_HOME": str(root / "data"),
            "XDG_STATE_HOME": str(root / "state"),
            "DISABLE_AUTOUPDATER": "1",
            "DISABLE_UPDATES": "1",
            "DISABLE_ERROR_REPORTING": "1",
            "DISABLE_TELEMETRY": "1",
        }
        try:
            process = subprocess.Popen(  # noqa: S603 - exact validated executable
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
            raise ClaudeInstallationUnavailable("claude_version_unavailable") from None
        try:
            raw_version = _read_bounded_stdout(process)
        except ClaudeInstallationUnavailable:
            _terminate_owned_process(process)
            raise
        except (OSError, ValueError):
            _terminate_owned_process(process)
            raise ClaudeInstallationUnavailable("claude_version_unavailable") from None
        except BaseException:
            _terminate_owned_process(process)
            raise
        finally:
            if process.stdout is not None:
                try:
                    process.stdout.close()
                except (OSError, ValueError):
                    pass
        if process.returncode != 0:
            raise ClaudeInstallationUnavailable("claude_version_invalid")
        if any(root.iterdir()):
            raise ClaudeInstallationUnavailable("claude_version_side_effect_detected")

    match = _VERSION.fullmatch(raw_version)
    if match is None:
        raise ClaudeInstallationUnavailable("claude_version_invalid")
    return match.group(1).decode("ascii")


def _read_bounded_stdout(process: subprocess.Popen[bytes]) -> bytes:
    """Read a strict bounded banner and reap only the subprocess we created."""
    if process.stdout is None:
        raise ClaudeInstallationUnavailable("claude_version_unavailable")
    output = bytearray()
    deadline = time.monotonic() + _VERSION_TIMEOUT_SECONDS
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ClaudeInstallationUnavailable("claude_version_deadline_exceeded")
            events = selector.select(remaining)
            if not events:
                raise ClaudeInstallationUnavailable("claude_version_deadline_exceeded")
            chunk = os.read(
                process.stdout.fileno(),
                _VERSION_OUTPUT_LIMIT_BYTES + 1 - len(output),
            )
            if not chunk:
                break
            output.extend(chunk)
            if len(output) > _VERSION_OUTPUT_LIMIT_BYTES:
                raise ClaudeInstallationUnavailable("claude_version_output_too_large")

    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ClaudeInstallationUnavailable("claude_version_deadline_exceeded")
    try:
        process.wait(timeout=remaining)
    except subprocess.TimeoutExpired:
        raise ClaudeInstallationUnavailable(
            "claude_version_deadline_exceeded"
        ) from None
    return bytes(output)


def _terminate_owned_process(process: subprocess.Popen[bytes]) -> None:
    """Best-effort cleanup of the isolated version subprocess group only."""
    try:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass
        try:
            process.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            pass
    except (OSError, ValueError):
        pass


def _binary_identity(path: Path) -> ClaudeExecutableIdentityV1:
    info = path.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o022
        or not os.access(path, os.X_OK)
    ):
        raise ClaudeInstallationUnavailable("claude_process_executable_unsafe")
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


def _process_version(path: Path, identity: ClaudeExecutableIdentityV1) -> str:
    if _binary_identity(path) != identity:
        raise ClaudeInstallationUnavailable("claude_process_executable_changed")
    version = _read_version(path)
    if _binary_identity(path) != identity:
        raise ClaudeInstallationUnavailable("claude_process_executable_changed")
    return version


def _bounded_native_version_candidates(
    entries: Iterable[Path],
    *,
    default_executable: Path | None,
    deadline_monotonic: float | None = None,
) -> tuple[tuple[Path, ...], bool]:
    """Select a bounded set of bounded version names without broad scanning."""
    candidates: list[Path] = []
    truncated = False
    for index, entry in enumerate(entries):
        if index >= _PROCESS_DIRECTORY_ENTRY_LIMIT:
            truncated = True
            break
        if deadline_monotonic is not None and time.monotonic() >= deadline_monotonic:
            truncated = True
            break
        name = entry.name
        if len(name) > 20:
            if all(character.isdigit() or character == "." for character in name[:21]):
                truncated = True
            continue
        if _NATIVE_VERSION_NAME.fullmatch(name) is None:
            if name and all(
                character.isdigit() or character == "." for character in name
            ):
                truncated = True
            continue
        if entry == default_executable:
            continue
        candidates.append(entry)
    candidates.sort(
        key=lambda entry: tuple(int(part) for part in entry.name.split(".")),
        reverse=True,
    )
    available_slots = _PROCESS_INSTALLATION_LIMIT - int(default_executable is not None)
    if len(candidates) > available_slots:
        truncated = True
    return tuple(candidates[:available_slots]), truncated


def discover_process_installations() -> tuple[tuple[ClaudeInstallationV1, ...], bool]:
    """Admit OS-only discovery for actual retained native CLI executables.

    This does not widen the reviewed quota/auth/parser version. Only the official
    version banner and OS metadata are read from other installed executables.
    """
    platform_id = f"{platform.system().lower()}-{platform.machine().lower()}"
    if platform_id != "linux-x86_64":
        raise ClaudeInstallationUnavailable("claude_platform_unverified")
    home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    versions = home / ".local" / "share" / "claude" / "versions"
    installations: list[ClaudeInstallationV1] = []
    default_executable: Path | None = None
    try:
        default = discover_default_installation()
        installations.append(default)
        default_executable = default.executable_for_adapter
        if default_executable.parent != versions:
            return tuple(installations), False
    except ClaudeInstallationUnavailable:
        # Quota/auth capabilities remain closed when their exact reviewed
        # executable is absent. Generic process observation can still inspect
        # separately validated native-version executables already on disk.
        pass
    try:
        info = versions.lstat()
    except OSError:
        if installations:
            return tuple(installations), True
        raise ClaudeInstallationUnavailable(
            "claude_process_versions_unavailable"
        ) from None
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o002
        or (info.st_mode & 0o020 and info.st_gid != os.getgid())
    ):
        if installations:
            return tuple(installations), True
        raise ClaudeInstallationUnavailable("claude_process_versions_unsafe")
    deadline = time.monotonic() + _PROCESS_DISCOVERY_SECONDS
    try:
        with os.scandir(versions) as directory:
            candidates, truncated = _bounded_native_version_candidates(
                (Path(entry.path) for entry in directory),
                default_executable=default_executable,
                deadline_monotonic=deadline,
            )
    except OSError:
        if installations:
            return tuple(installations), True
        raise ClaudeInstallationUnavailable(
            "claude_process_versions_unavailable"
        ) from None
    for candidate in candidates:
        if time.monotonic() >= deadline:
            truncated = True
            break
        try:
            identity = _binary_identity(candidate)
            version = _process_version(candidate, identity)
            if version != candidate.name:
                truncated = True
                continue
            reference = (
                "claude-process-"
                + hashlib.sha256(str(candidate).encode()).hexdigest()[:24]
            )
            installations.append(
                ClaudeInstallationV1(
                    OpaqueIdV1(reference),
                    version,
                    platform_id,
                    candidate,
                    identity,
                )
            )
        except (OSError, RuntimeError, ValueError):
            truncated = True
    if not installations:
        raise ClaudeInstallationUnavailable("claude_executable_invalid")
    return tuple(installations), truncated

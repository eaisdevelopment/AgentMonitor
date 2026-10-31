"""Bounded discovery of the exact admitted Codex CLI installation."""

import os
import platform
import re
import selectors
import shutil
import signal
import stat
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from agentmonitor.adapters.providers.codex.manifest import CODEX_PROVIDER_VERSION
from agentmonitor.contracts.common_v1 import OpaqueIdV1

_VERSION = re.compile(rb"codex-cli ([0-9]+\.[0-9]+\.[0-9]+)\r?\n?\Z")
_VERSION_TIMEOUT_SECONDS = 3
_VERSION_OUTPUT_LIMIT_BYTES = 128
type _ExecutableIdentityV1 = tuple[int, int, int, int, int, int, int, int]


class CodexInstallationUnavailable(RuntimeError):
    """The exact reviewed Codex CLI cannot be safely admitted."""


@dataclass(frozen=True, slots=True)
class CodexInstallationV1:
    """Private adapter handle; the executable path is never in its repr."""

    installation_ref: OpaqueIdV1
    provider_version: str
    platform_id: str
    _executable: Path = field(repr=False)
    _identity: _ExecutableIdentityV1 = field(repr=False)

    @property
    def executable_for_adapter(self) -> Path:
        return self._executable

    def executable_for_launch(self) -> Path:
        """Revalidate the retained executable identity immediately before use."""
        try:
            current = _binary_identity(self._executable)
        except (OSError, CodexInstallationUnavailable):
            raise CodexInstallationUnavailable("codex_executable_changed") from None
        if current != self._identity:
            raise CodexInstallationUnavailable("codex_executable_changed")
        return self._executable


def discover_default_installation(
    *, verified_provider_version: str = CODEX_PROVIDER_VERSION
) -> CodexInstallationV1:
    """Resolve and execute only the admitted read-only version operation."""
    if verified_provider_version != CODEX_PROVIDER_VERSION:
        raise CodexInstallationUnavailable("codex_version_unverified")

    platform_id = f"{platform.system().lower()}-{platform.machine().lower()}"
    if platform_id != "linux-x86_64":
        raise CodexInstallationUnavailable("codex_platform_unverified")

    found = shutil.which("codex")
    if found is None:
        raise CodexInstallationUnavailable("codex_executable_unavailable")
    unresolved = Path(found)
    if not unresolved.is_absolute():
        raise CodexInstallationUnavailable("codex_executable_invalid")
    try:
        executable = unresolved.resolve(strict=True)
        identity = _binary_identity(executable)
    except OSError:
        raise CodexInstallationUnavailable("codex_executable_invalid") from None

    provider_version = _read_version(executable)
    try:
        if _binary_identity(executable) != identity:
            raise CodexInstallationUnavailable("codex_executable_changed")
    except OSError:
        raise CodexInstallationUnavailable("codex_executable_changed") from None
    if provider_version != verified_provider_version:
        raise CodexInstallationUnavailable("codex_version_unverified")

    return CodexInstallationV1(
        installation_ref=OpaqueIdV1("codex-installation-primary"),
        provider_version=provider_version,
        platform_id=platform_id,
        _executable=executable,
        _identity=identity,
    )


def _binary_identity(executable: Path) -> _ExecutableIdentityV1:
    info = executable.lstat()
    if (
        executable.name != "codex"
        or not stat.S_ISREG(info.st_mode)
        or info.st_uid not in {0, os.getuid()}
        or info.st_mode & 0o022
        or not os.access(executable, os.X_OK)
    ):
        raise CodexInstallationUnavailable("codex_executable_unsafe")
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


def _read_version(executable: Path) -> str:
    """Read at most 128 bytes from one isolated real ``codex --version``."""
    with tempfile.TemporaryDirectory(prefix="agentmonitor-codex-version-") as raw_root:
        root = Path(raw_root)
        root.chmod(0o700)
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
        if any(root.iterdir()):
            raise CodexInstallationUnavailable("codex_version_side_effect_detected")

    match = _VERSION.fullmatch(output)
    if match is None:
        raise CodexInstallationUnavailable("codex_version_invalid")
    return match.group(1).decode("ascii")


def _read_bounded_stdout(process: subprocess.Popen[bytes]) -> bytes:
    if process.stdout is None:
        _terminate_owned_process(process)
        raise CodexInstallationUnavailable("codex_version_unavailable")
    output = bytearray()
    deadline = time.monotonic() + _VERSION_TIMEOUT_SECONDS
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _terminate_owned_process(process)
                raise CodexInstallationUnavailable("codex_version_deadline_exceeded")
            events = selector.select(remaining)
            if not events:
                _terminate_owned_process(process)
                raise CodexInstallationUnavailable("codex_version_deadline_exceeded")
            chunk = os.read(
                process.stdout.fileno(),
                _VERSION_OUTPUT_LIMIT_BYTES + 1 - len(output),
            )
            if not chunk:
                break
            output.extend(chunk)
            if len(output) > _VERSION_OUTPUT_LIMIT_BYTES:
                _terminate_owned_process(process)
                raise CodexInstallationUnavailable("codex_version_output_too_large")

    remaining = deadline - time.monotonic()
    if remaining <= 0:
        _terminate_owned_process(process)
        raise CodexInstallationUnavailable("codex_version_deadline_exceeded")
    try:
        process.wait(timeout=remaining)
    except subprocess.TimeoutExpired:
        _terminate_owned_process(process)
        raise CodexInstallationUnavailable("codex_version_deadline_exceeded") from None
    return bytes(output)


def _terminate_owned_process(process: subprocess.Popen[bytes]) -> None:
    try:
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
        try:
            process.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            pass
    except (OSError, ValueError):
        # Cleanup is best effort and must never hide the bounded primary error.
        pass

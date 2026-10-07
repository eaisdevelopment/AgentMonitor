"""Bounded discovery of the exact installed Claude executable version."""

import hashlib
import os
import platform
import pwd
import re
import shutil
import stat
import subprocess
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from agentmonitor.adapters.providers.claude.manifest import (
    CLAUDE_OTEL_PROVIDER_VERSION,
    CLAUDE_PROVIDER_VERSION,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1

_VERSION = re.compile(rb"([0-9]+\.[0-9]+\.[0-9]+) \(Claude Code\)\s*\Z")


class ClaudeInstallationUnavailable(RuntimeError):
    """The required exact local installation cannot be safely used."""


@dataclass(frozen=True, slots=True)
class ClaudeInstallationV1:
    """Private adapter installation handle; executable path never leaves A01."""

    installation_ref: OpaqueIdV1
    provider_version: str
    platform_id: str
    _executable: Path

    @property
    def executable_for_adapter(self) -> Path:
        return self._executable


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
        provider_version = _read_version(executable)
        if provider_version != verified_provider_version:
            continue
        return ClaudeInstallationV1(
            installation_ref=OpaqueIdV1("claude-installation-default"),
            provider_version=provider_version,
            platform_id=platform_id,
            _executable=executable,
        )
    if saw_executable:
        raise ClaudeInstallationUnavailable("claude_version_unverified")
    raise ClaudeInstallationUnavailable("claude_executable_invalid")


def _read_version(executable: Path) -> str:
    """Read one bounded version banner from an already validated executable."""
    try:
        completed = subprocess.run(
            [str(executable), "--version"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=3,
            env={
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
                "DISABLE_AUTOUPDATER": "1",
                "DISABLE_UPDATES": "1",
                "DISABLE_ERROR_REPORTING": "1",
                "DISABLE_TELEMETRY": "1",
            },
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ClaudeInstallationUnavailable("claude_version_unavailable") from error
    raw_version = completed.stdout[:128]
    match = _VERSION.fullmatch(raw_version)
    raw_version = b""
    if completed.returncode != 0 or match is None:
        raise ClaudeInstallationUnavailable("claude_version_invalid")
    return match.group(1).decode("ascii")


def _binary_identity(path: Path) -> tuple[int, ...]:
    info = path.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o022
    ):
        raise ClaudeInstallationUnavailable("claude_process_executable_unsafe")
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


@lru_cache(maxsize=64)
def _process_version(path: Path, identity: tuple[int, ...]) -> str:
    if _binary_identity(path) != identity:
        raise ClaudeInstallationUnavailable("claude_process_executable_changed")
    version = _read_version(path)
    if _binary_identity(path) != identity:
        raise ClaudeInstallationUnavailable("claude_process_executable_changed")
    return version


def discover_process_installations() -> tuple[tuple[ClaudeInstallationV1, ...], bool]:
    """Admit OS-only discovery for actual retained native CLI executables.

    This does not widen the reviewed quota/auth/parser version. Only the official
    version banner and OS metadata are read from other installed executables.
    """
    default = discover_default_installation()
    versions = default.executable_for_adapter.parent
    installations = [default]
    if versions.name != "versions" or versions.parent.name != "claude":
        return tuple(installations), False
    info = versions.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o002
        or (info.st_mode & 0o020 and info.st_gid != os.getgid())
    ):
        return tuple(installations), True
    candidates = sorted(
        (
            entry
            for entry in versions.iterdir()
            if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", entry.name)
        ),
        key=lambda entry: tuple(int(part) for part in entry.name.split(".")),
        reverse=True,
    )
    truncated = len(candidates) > 32
    deadline = time.monotonic() + 2
    for candidate in candidates[:32]:
        if candidate == default.executable_for_adapter:
            continue
        if time.monotonic() >= deadline:
            truncated = True
            break
        try:
            identity = _binary_identity(candidate)
            if not os.access(candidate, os.X_OK):
                continue
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
                    default.platform_id,
                    candidate,
                )
            )
        except (OSError, RuntimeError, ValueError):
            truncated = True
    return tuple(installations), truncated

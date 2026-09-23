"""Bounded discovery of the exact installed Claude executable version."""

import os
import platform
import pwd
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from agentmonitor.adapters.providers.claude.manifest import CLAUDE_PROVIDER_VERSION
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


def discover_default_installation() -> ClaudeInstallationV1:
    """Resolve the accepted installed Claude version without changing defaults.

    Claude's native installer retains earlier versioned executables when it
    advances the ``claude`` symlink.  Prefer the current command only when it
    still matches the reviewed tuple; otherwise inspect the one exact native
    version path.  This never rewrites the symlink or provider-owned profile.
    """
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
        / CLAUDE_PROVIDER_VERSION
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
        if provider_version != CLAUDE_PROVIDER_VERSION:
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

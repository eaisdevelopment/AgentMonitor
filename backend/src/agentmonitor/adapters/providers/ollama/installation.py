"""Read-only, isolated discovery of the local Ollama CLI version."""

from __future__ import annotations

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
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from agentmonitor.adapters.providers.ollama.manifest import OLLAMA_PROVIDER_VERSION
from agentmonitor.contracts.common_v1 import OpaqueIdV1

_VERSION = re.compile(rb"ollama version is ([0-9]+\.[0-9]+\.[0-9]+)\r?\n?\Z")
_LIMIT = 128
_TIMEOUT = 3.0
type OllamaExecutableIdentityV1 = tuple[int, int, int, int, int, int, int, int]


class OllamaInstallationUnavailable(RuntimeError):
    """The exact reviewed Ollama CLI cannot be used for process observation."""


@dataclass(frozen=True, slots=True)
class InstallationResult:
    outcome: Literal["success", "provider_unavailable", "unverified_provider_version"]
    cli_version: str | None
    platform_id: str
    observed_at: datetime
    installation_ref: OpaqueIdV1 | None
    _executable: Path | None = field(repr=False, compare=False)
    _identity: OllamaExecutableIdentityV1 | None = field(repr=False, compare=False)

    def executable_for_process_observation(
        self,
    ) -> tuple[Path, OllamaExecutableIdentityV1]:
        """Return one revalidated image without exposing its path in the result."""

        if (
            self.outcome != "success"
            or self.installation_ref is None
            or self._executable is None
            or self._identity is None
        ):
            raise OllamaInstallationUnavailable("ollama_installation_unavailable")
        try:
            current = _identity(self._executable)
        except (OSError, ValueError):
            raise OllamaInstallationUnavailable(
                "ollama_process_executable_changed"
            ) from None
        if current != self._identity:
            raise OllamaInstallationUnavailable("ollama_process_executable_changed")
        return self._executable, self._identity


def _identity(path: Path) -> OllamaExecutableIdentityV1:
    info = path.lstat()
    if (
        path.name != "ollama"
        or not stat.S_ISREG(info.st_mode)
        or info.st_uid not in {0, os.getuid()}
        or info.st_mode & 0o022
        or not os.access(path, os.X_OK)
    ):
        raise ValueError("ollama_executable_unsafe")
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


def _version(path: Path) -> str:
    with tempfile.TemporaryDirectory(
        prefix="agentmonitor-ollama-version-"
    ) as directory:
        root = Path(directory)
        environment = {
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "HOME": str(root / "home"),
            "XDG_CACHE_HOME": str(root / "cache"),
            "XDG_CONFIG_HOME": str(root / "config"),
        }
        process = subprocess.Popen(  # noqa: S603 - fixed verified executable and argument
            [str(path), "--version"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=root,
            env=environment,
            shell=False,
            start_new_session=True,
        )
        try:
            if process.stdout is None:
                raise ValueError("ollama_version_unavailable")
            output = bytearray()
            deadline = time.monotonic() + _TIMEOUT
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not selector.select(remaining):
                        raise TimeoutError("ollama_version_deadline")
                    chunk = os.read(process.stdout.fileno(), _LIMIT + 1 - len(output))
                    if not chunk:
                        break
                    output.extend(chunk)
                    if len(output) > _LIMIT:
                        raise ValueError("ollama_version_too_large")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("ollama_version_deadline")
            process.wait(timeout=remaining)
            if process.returncode != 0 or any(root.iterdir()):
                raise ValueError("ollama_version_invalid")
            match = _VERSION.fullmatch(output)
            if match is None:
                raise ValueError("ollama_version_invalid")
            return match.group(1).decode("ascii")
        finally:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=2)
            if process.stdout is not None:
                process.stdout.close()


def discover_installation() -> InstallationResult:
    """Inspect one native version banner without accessing a user profile."""
    platform_id = f"{platform.system().lower()}-{platform.machine().lower()}"
    if platform_id != "linux-x86_64":
        return InstallationResult(
            "unverified_provider_version",
            None,
            platform_id,
            datetime.now(UTC),
            None,
            None,
            None,
        )
    try:
        found = shutil.which("ollama")
        if found is None or not Path(found).is_absolute():
            raise ValueError("ollama_executable_unavailable")
        executable = Path(found).resolve(strict=True)
        identity = _identity(executable)
        version = _version(executable)
        if _identity(executable) != identity:
            raise ValueError("ollama_executable_changed")
    except (OSError, ValueError, TimeoutError, subprocess.SubprocessError):
        return InstallationResult(
            "provider_unavailable",
            None,
            platform_id,
            datetime.now(UTC),
            None,
            None,
            None,
        )
    outcome: Literal["success", "unverified_provider_version"] = "success"
    if version != OLLAMA_PROVIDER_VERSION:
        outcome = "unverified_provider_version"
    return InstallationResult(
        outcome,
        version,
        platform_id,
        datetime.now(UTC),
        OpaqueIdV1("ollama-installation-primary") if outcome == "success" else None,
        executable if outcome == "success" else None,
        identity if outcome == "success" else None,
    )

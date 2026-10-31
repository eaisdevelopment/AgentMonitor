"""Owner-started initial Codex login in an isolated managed profile.

This module does not implement historical reauthentication.  The only write
operation admitted for M5 is the official ``codex login`` flow for a profile
that has no verified identity yet.
"""

from __future__ import annotations

import os
import re
import signal
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from agentmonitor.adapters.providers.codex.installation import CodexInstallationV1
from agentmonitor.adapters.providers.codex.manifest import CODEX_PROVIDER_VERSION
from agentmonitor.adapters.providers.codex.transport import (
    CodexAppServerFailure,
    validate_codex_managed_auth_store_v1,
    validate_codex_managed_profile_root_v1,
)
from agentmonitor.contracts import provider_system_v1
from agentmonitor.contracts.common_v1 import OpaqueIdV1

_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+\Z")
_DISPLAY_ENVIRONMENT_KEYS = (
    "DISPLAY",
    "WAYLAND_DISPLAY",
    "XAUTHORITY",
    "XDG_RUNTIME_DIR",
    "DBUS_SESSION_BUS_ADDRESS",
)


@dataclass(frozen=True, slots=True)
class CodexManagedAuthenticationTargetV1:
    """Opaque authorization facts checked before any provider process starts."""

    profile_ref: OpaqueIdV1
    profile_protection: provider_system_v1.ProfileProtectionV1
    expected_identity_available: bool
    owner_interaction_granted: bool
    existing_verified_identity: bool

    def __post_init__(self) -> None:
        if any(
            type(value) is not bool
            for value in (
                self.expected_identity_available,
                self.owner_interaction_granted,
                self.existing_verified_identity,
            )
        ):
            raise ValueError("codex_managed_login_target_invalid")


@dataclass(slots=True)
class CodexManagedLoginAttemptV1:
    """Private handle to the one native login child owned by this request."""

    _process: subprocess.Popen[bytes] = field(repr=False)
    _managed_profile_root: Path = field(repr=False)

    def wait_for_completion(self, *, timeout_seconds: float = 600.0) -> bool:
        """Wait for native login without reading provider output or credentials."""
        if type(timeout_seconds) not in {int, float} or not 0 < timeout_seconds <= 600:
            raise ValueError("codex_managed_login_deadline_invalid")
        try:
            code = self._process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            self.cancel()
            return False
        _validated_auth_store(self._managed_profile_root, required=code == 0)
        return code == 0

    def cancel(self) -> None:
        """Terminate only the process group created for this login request."""
        try:
            if self._process.poll() is None:
                try:
                    os.killpg(self._process.pid, signal.SIGTERM)
                except (OSError, ValueError):
                    pass
                try:
                    self._process.wait(timeout=2)
                except (OSError, subprocess.TimeoutExpired):
                    pass
                if self._process.poll() is None:
                    try:
                        os.killpg(self._process.pid, signal.SIGKILL)
                    except (OSError, ValueError):
                        pass
                    try:
                        self._process.wait(timeout=2)
                    except (OSError, subprocess.TimeoutExpired):
                        pass
        except (OSError, ValueError):
            pass
        _validated_auth_store(self._managed_profile_root, required=False)


def _validated_managed_root(
    managed_profiles_root: Path, managed_profile_root: Path
) -> Path:
    try:
        return validate_codex_managed_profile_root_v1(
            managed_profiles_root=managed_profiles_root,
            managed_profile_root=managed_profile_root,
        )
    except CodexAppServerFailure as error:
        raise ValueError(error.code) from None


def _validated_auth_store(root: Path, *, required: bool) -> None:
    try:
        validate_codex_managed_auth_store_v1(root, required=required)
    except CodexAppServerFailure as error:
        raise ValueError(error.code) from None


def _login_environment(root: Path) -> dict[str, str]:
    environment = {
        "HOME": str(root),
        "CODEX_HOME": str(root),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "NO_COLOR": "1",
        "PATH": "/usr/bin:/bin",
    }
    # Only the named local desktop transport values needed by the official
    # browser opener are inherited.  No arbitrary process environment is read.
    for key in _DISPLAY_ENVIRONMENT_KEYS:
        value = os.environ.get(key)
        if value and "\0" not in value and len(value) <= 4096:
            environment[key] = value
    return environment


def begin_managed_profile_authentication_v1(
    installation: CodexInstallationV1,
    target: CodexManagedAuthenticationTargetV1,
    *,
    managed_profiles_root: Path,
    managed_profile_root: Path,
    expected_email: str,
) -> CodexManagedLoginAttemptV1:
    """Start the official browser login for one empty managed Codex profile."""
    if target.existing_verified_identity:
        raise ValueError("codex_reauthentication_not_in_m5")
    if (
        target.profile_protection != "managed"
        or not target.expected_identity_available
        or not target.owner_interaction_granted
        or type(expected_email) is not str
        or len(expected_email) > 254
        or _EMAIL.fullmatch(expected_email) is None
    ):
        raise ValueError("codex_managed_login_target_invalid")
    if (
        installation.provider_version != CODEX_PROVIDER_VERSION
        or installation.platform_id != "linux-x86_64"
    ):
        raise ValueError("codex_managed_login_installation_invalid")
    root = _validated_managed_root(managed_profiles_root, managed_profile_root)
    _validated_auth_store(root, required=False)
    try:
        executable = installation.executable_for_launch()
    except RuntimeError:
        raise ValueError("codex_managed_login_installation_invalid") from None
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
        "login",
    ]
    try:
        process = subprocess.Popen(  # noqa: S603 - exact admitted executable
            arguments,
            cwd=root,
            env=_login_environment(root),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
            start_new_session=True,
        )
    except OSError:
        raise ValueError("codex_managed_login_unavailable") from None
    return CodexManagedLoginAttemptV1(process, root)

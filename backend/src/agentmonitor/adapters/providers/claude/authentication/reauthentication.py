"""Protected reauth boundary and separately authorized managed operator login.

The legacy coordinator entry remains unavailable. The bounded owner-operated
connection increment provides official login only for a validated private root;
it never enrolls a registry account or claims collection is enabled.
"""

import os
import re
import stat
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from agentmonitor.adapters.providers.claude.authentication.identity import (
    claude_identity_environment_v1,
    read_default_profile_identity_v1,
)
from agentmonitor.adapters.providers.claude.installation import ClaudeInstallationV1
from agentmonitor.contracts import provider_system_v1
from agentmonitor.contracts.common_v1 import OpaqueIdV1


@dataclass(frozen=True, slots=True)
class ClaudeReauthenticationTargetV1:
    """Opaque target metadata used by the pre-I/O authorization gate."""

    profile_ref: OpaqueIdV1
    profile_protection: provider_system_v1.ProfileProtectionV1
    expected_identity_available: bool
    owner_interaction_granted: bool

    def __post_init__(self) -> None:
        if (
            type(self.expected_identity_available) is not bool
            or type(self.owner_interaction_granted) is not bool
        ):
            raise ValueError("claude_reauthentication_target_invalid")


@dataclass(frozen=True, slots=True)
class ClaudeReauthenticationDecisionV1:
    """Typed unavailable result; no provider response or credential is carried."""

    state: Literal["unavailable"]
    reason_code: str
    provider_io_started: bool


def request_reauthentication(
    target: ClaudeReauthenticationTargetV1,
) -> ClaudeReauthenticationDecisionV1:
    """Reject unsafe or not-yet-approved reauthentication before provider I/O."""
    if target.profile_protection == "protected_default":
        return ClaudeReauthenticationDecisionV1(
            "unavailable", "protected_default_profile", False
        )
    if target.profile_protection != "managed":
        return ClaudeReauthenticationDecisionV1(
            "unavailable", "profile_protection_unknown", False
        )
    if not target.expected_identity_available:
        return ClaudeReauthenticationDecisionV1(
            "unavailable", "expected_identity_required", False
        )
    if not target.owner_interaction_granted:
        return ClaudeReauthenticationDecisionV1(
            "unavailable", "owner_interaction_required", False
        )
    # CLA-I09 is intentionally not approved in M4.  Keep the final gate in
    # this module so a caller cannot accidentally reach /login before the
    # separately reviewed packet is wired into the implementation.
    return ClaudeReauthenticationDecisionV1(
        "unavailable", "managed_reauthentication_not_approved", False
    )


@dataclass(slots=True)
class ClaudeManagedLoginAttemptV1:
    """Private operator handle; provider streams and credentials are never read."""

    _process: subprocess.Popen[bytes] = field(repr=False)
    _installation: ClaudeInstallationV1 = field(repr=False)
    _root: Path = field(repr=False)
    _expected_email: str = field(repr=False)

    def wait_for_identity(
        self, *, timeout_seconds: int = 600
    ) -> provider_system_v1.ObservedProfileIdentityV1 | None:
        if not 1 <= timeout_seconds <= 600:
            raise ValueError("claude_managed_login_deadline_invalid")
        try:
            code = self._process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            self.cancel()
            return None
        if code != 0:
            return None
        identity = read_default_profile_identity_v1(
            self._installation, managed_profile_root=self._root
        )
        if (
            identity is None
            or identity.email.casefold() != self._expected_email.casefold()
        ):
            return None
        return identity

    def cancel(self) -> None:
        """Stop only this handle's owned login subprocess, never an agent."""
        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=2)


def begin_managed_profile_authentication_v1(
    installation: ClaudeInstallationV1,
    target: ClaudeReauthenticationTargetV1,
    *,
    managed_profile_root: Path,
    expected_email: str,
    browser_opener: Path | None = None,
) -> ClaudeManagedLoginAttemptV1:
    """Official owner sign-in under the bounded CLA-I09 operator change plan.

    No authorization code, provider output, or credentials are accepted or read.
    The owner uses the browser's native local callback to complete sign-in.
    """
    if (
        target.profile_protection != "managed"
        or not target.expected_identity_available
        or not target.owner_interaction_granted
        or len(expected_email) > 320
        or re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", expected_email) is None
    ):
        raise ValueError("claude_managed_login_target_invalid")
    environment = claude_identity_environment_v1(managed_profile_root)
    # Only the operator's named display/session metadata, never agent env data.
    for key in (
        "DISPLAY",
        "WAYLAND_DISPLAY",
        "XAUTHORITY",
        "XDG_RUNTIME_DIR",
        "DBUS_SESSION_BUS_ADDRESS",
    ):
        value = os.environ.get(key)
        if value:
            environment[key] = value
    if browser_opener is not None:
        info = browser_opener.lstat()
        if (
            browser_opener.resolve(strict=True) != browser_opener.absolute()
            or not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700
        ):
            raise ValueError("claude_managed_browser_opener_unsafe")
        environment["BROWSER"] = str(browser_opener)
    process = subprocess.Popen(
        [
            str(installation.executable_for_adapter),
            "auth",
            "login",
            "--claudeai",
            "--email",
            expected_email,
        ],
        cwd=managed_profile_root,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return ClaudeManagedLoginAttemptV1(
        process, installation, managed_profile_root, expected_email
    )

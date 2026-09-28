"""Read only the official CLI's allowlisted authenticated-profile metadata."""

import hashlib
import json
import os
import pwd
import stat
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from agentmonitor.adapters.providers.claude.installation import ClaudeInstallationV1
from agentmonitor.contracts.provider_system_v1 import ObservedProfileIdentityV1


def _label(value: object, maximum: int) -> str | None:
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        return None
    if not value.isprintable() or value != value.strip():
        return None
    return value


def read_default_profile_identity_v1(
    installation: ClaudeInstallationV1,
    *,
    managed_profile_root: Path | None = None,
) -> ObservedProfileIdentityV1 | None:
    """Read the default identity, or an explicitly isolated managed identity.

    A managed root is validated before CLI I/O. HOME remains the real user's
    home; Claude's official configuration-directory override selects the
    separate provider-managed credential store.
    """
    environment = claude_identity_environment_v1(managed_profile_root)
    try:
        with tempfile.TemporaryDirectory(prefix="agentmonitor-auth-status-") as cwd:
            result = subprocess.run(
                [str(installation.executable_for_adapter), "auth", "status", "--json"],
                cwd=cwd,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=3,
                check=False,
            )
        if result.returncode != 0 or len(result.stdout) > 8192:
            return None
        metadata = json.loads(result.stdout)
        if not isinstance(metadata, dict) or metadata.get("loggedIn") is not True:
            return None
        email = _label(metadata.get("email"), 320)
        organization = _label(metadata.get("orgName"), 256)
        organization_id = _label(metadata.get("orgId"), 256)
        method = _label(metadata.get("authMethod"), 64)
        if email is None or "@" not in email or method is None:
            return None
        fingerprint = hashlib.sha256(
            "\x00".join(
                (email, organization_id or "", organization or "", method)
            ).encode()
        ).hexdigest()
        return ObservedProfileIdentityV1(
            email,
            organization,
            fingerprint,
            datetime.now(UTC),
            installation.provider_version,
        )
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None


def claude_identity_environment_v1(
    managed_profile_root: Path | None = None,
) -> dict[str, str]:
    """Adapter-local, minimal CLI environment; never copy provider env values."""
    home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    environment = {
        "HOME": str(home),
        "PATH": os.defpath,
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "DISABLE_AUTOUPDATER": "1",
        "DISABLE_UPDATES": "1",
        "DISABLE_ERROR_REPORTING": "1",
        "DISABLE_TELEMETRY": "1",
    }
    if managed_profile_root is not None:
        try:
            root = managed_profile_root.absolute()
            info = root.lstat()
            if (
                root.resolve(strict=True) != root
                or not stat.S_ISDIR(info.st_mode)
                or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o700
                or root == home
                or root.is_relative_to(home / ".claude")
                or home.is_relative_to(root)
                or any(parent.is_symlink() for parent in root.parents)
            ):
                raise ValueError("claude_managed_profile_unsafe")
        except OSError:
            raise ValueError("claude_managed_profile_unsafe") from None
        environment["CLAUDE_CONFIG_DIR"] = str(root)
    return environment

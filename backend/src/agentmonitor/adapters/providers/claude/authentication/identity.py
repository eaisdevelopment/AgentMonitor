"""Read only the official CLI's allowlisted authenticated-profile metadata."""

import hashlib
import json
import os
import pwd
import subprocess
import tempfile
from datetime import UTC, datetime

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
) -> ObservedProfileIdentityV1 | None:
    """Never read credentials, inherit arbitrary environment, or emit raw JSON."""
    try:
        with tempfile.TemporaryDirectory(prefix="agentmonitor-auth-status-") as cwd:
            result = subprocess.run(
                [str(installation.executable_for_adapter), "auth", "status", "--json"],
                cwd=cwd,
                env={
                    "HOME": pwd.getpwuid(os.getuid()).pw_dir,
                    "PATH": os.defpath,
                    "LANG": "C.UTF-8",
                    "LC_ALL": "C.UTF-8",
                    "DISABLE_AUTOUPDATER": "1",
                    "DISABLE_UPDATES": "1",
                    "DISABLE_ERROR_REPORTING": "1",
                    "DISABLE_TELEMETRY": "1",
                },
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

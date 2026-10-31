"""Real native Claude identity checks for private managed profiles."""

import json
import os
import pwd
import subprocess
from pathlib import Path

import pytest
from agentmonitor.adapters.providers.claude.authentication.identity import (
    read_default_profile_identity_v1,
)
from agentmonitor.adapters.providers.claude.installation import (
    discover_default_installation,
)


def test_empty_managed_profile_does_not_inherit_default_identity(
    tmp_path: Path,
) -> None:
    """CLA-MANAGED-001: real isolated status must not return another identity."""
    installation = discover_default_installation()
    before = read_default_profile_identity_v1(installation)
    observed = read_default_profile_identity_v1(
        installation, managed_profile_root=tmp_path
    )
    assert observed is None
    result = subprocess.run(
        [str(installation.executable_for_adapter), "auth", "status", "--json"],
        env={
            "HOME": pwd.getpwuid(os.getuid()).pw_dir,
            "CLAUDE_CONFIG_DIR": str(tmp_path),
            "PATH": os.defpath,
            "LANG": "C.UTF-8",
            "DISABLE_AUTOUPDATER": "1",
            "DISABLE_ERROR_REPORTING": "1",
            "DISABLE_TELEMETRY": "1",
        },
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=5,
    )
    metadata = json.loads(result.stdout)
    assert metadata.get("loggedIn") is False
    assert result.returncode == 1
    after = read_default_profile_identity_v1(installation)
    assert (before is None) == (after is None)
    if before is not None and after is not None:
        assert before.fingerprint == after.fingerprint


def test_managed_identity_rejects_symlink_and_public_root(tmp_path: Path) -> None:
    """CLA-MANAGED-002: filesystem protection is checked before native CLI I/O."""
    installation = discover_default_installation()
    public_root = tmp_path / "public"
    public_root.mkdir(mode=0o755)
    with pytest.raises(ValueError, match="claude_managed_profile_unsafe"):
        read_default_profile_identity_v1(installation, managed_profile_root=public_root)
    private_root = tmp_path / "private"
    private_root.mkdir(mode=0o700)
    link = tmp_path / "link"
    link.symlink_to(private_root, target_is_directory=True)
    with pytest.raises(ValueError, match="claude_managed_profile_unsafe"):
        read_default_profile_identity_v1(installation, managed_profile_root=link)


def test_managed_identity_rejects_protected_default_root() -> None:
    """CLA-MANAGED-003: a default root never becomes a managed target."""
    installation = discover_default_installation()
    protected = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".claude"
    with pytest.raises(ValueError, match="claude_managed_profile_unsafe"):
        read_default_profile_identity_v1(installation, managed_profile_root=protected)

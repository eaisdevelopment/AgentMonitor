"""Real Codex installation admission without provider-profile access."""

import os
import stat

import pytest
from agentmonitor.adapters.providers.codex.installation import (
    CodexInstallationUnavailable,
    discover_default_installation,
)
from agentmonitor.adapters.providers.codex.manifest import CODEX_PROVIDER_VERSION


def test_real_exact_reviewed_codex_binary_is_discoverable() -> None:
    """M5-CDX-INSTALL-001/002: execute the real bounded version boundary."""
    installation = discover_default_installation()
    executable = installation.executable_for_adapter
    mode = executable.stat().st_mode

    assert installation.provider_version == CODEX_PROVIDER_VERSION
    assert installation.platform_id == "linux-x86_64"
    assert executable.is_absolute()
    assert executable.is_file()
    assert os.access(executable, os.X_OK)
    assert stat.S_ISREG(mode)
    assert mode & 0o022 == 0
    assert str(executable) not in repr(installation)


def test_real_installation_identity_is_stable_across_fresh_version_reads() -> None:
    """M5-CDX-INSTALL-003: repeated real reads retain one opaque installation."""
    first = discover_default_installation()
    second = discover_default_installation()

    assert first.installation_ref == second.installation_ref
    assert first.provider_version == second.provider_version
    assert first.platform_id == second.platform_id
    assert first.executable_for_adapter == second.executable_for_adapter


def test_unreviewed_version_is_rejected_before_executable_or_profile_io() -> None:
    """M5-CDX-INSTALL-004: the installation API fails closed on version drift."""
    assert CODEX_PROVIDER_VERSION != "0.160.1"
    with pytest.raises(
        CodexInstallationUnavailable,
        match="^codex_version_unverified$",
    ):
        discover_default_installation(verified_provider_version="0.160.1")

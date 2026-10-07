"""Real accepted Claude installation discovery without default-profile mutation."""

import os

import pytest
from agentmonitor.adapters.providers.claude.installation import (
    ClaudeInstallationUnavailable,
    discover_default_installation,
)
from agentmonitor.adapters.providers.claude.manifest import (
    CLAUDE_OTEL_PROVIDER_VERSION,
    CLAUDE_PROVIDER_VERSION,
)


def test_real_exact_reviewed_claude_binary_is_discoverable() -> None:
    """Discover the retained reviewed binary even after the default link advances."""
    installation = discover_default_installation()

    assert installation.provider_version == CLAUDE_PROVIDER_VERSION
    assert installation.platform_id == "linux-x86_64"
    assert installation.executable_for_adapter.is_file()
    assert os.access(installation.executable_for_adapter, os.X_OK)


def test_unretained_otel_version_fails_before_capability_io() -> None:
    """CLA-LIVE-OTEL-002: quota admission cannot widen the OTEL tuple."""
    assert CLAUDE_OTEL_PROVIDER_VERSION != CLAUDE_PROVIDER_VERSION
    with pytest.raises(
        ClaudeInstallationUnavailable,
        match="^claude_version_unverified$",
    ):
        discover_default_installation(
            verified_provider_version=CLAUDE_OTEL_PROVIDER_VERSION
        )

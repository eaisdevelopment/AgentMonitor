"""Real accepted Claude installation discovery without default-profile mutation."""

import os

from agentmonitor.adapters.providers.claude.installation import (
    discover_default_installation,
)
from agentmonitor.adapters.providers.claude.manifest import CLAUDE_PROVIDER_VERSION


def test_real_exact_reviewed_claude_binary_is_discoverable() -> None:
    """Discover the retained reviewed binary even after the default link advances."""
    installation = discover_default_installation()

    assert installation.provider_version == CLAUDE_PROVIDER_VERSION
    assert installation.platform_id == "linux-x86_64"
    assert installation.executable_for_adapter.is_file()
    assert os.access(installation.executable_for_adapter, os.X_OK)

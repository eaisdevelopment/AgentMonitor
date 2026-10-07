"""Live OTEL capability gate against the current owner installation."""

import os
import secrets
from pathlib import Path

import pytest
from agentmonitor.adapters.providers.claude.installation import (
    ClaudeInstallationUnavailable,
)
from agentmonitor.composition.claude_otel_runtime import (
    prepare_monitored_claude_launch,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.runtime_observation_v1 import ProcessIdentityV1


def test_otel_launch_rejects_unretained_exact_version_before_launch() -> None:
    """CLA-LIVE-OTEL-003: unretained exact OTEL 2.1.282 fails before launch."""
    selected = os.environ.get("AGENTMONITOR_TEST_OWNER_DATA_ROOT")
    if selected is None:
        pytest.skip("NOT RUN: explicit real owner data root required")

    with pytest.raises(
        ClaudeInstallationUnavailable,
        match="^claude_version_unverified$",
    ):
        prepare_monitored_claude_launch(
            Path(selected),
            selected_account_id=OpaqueIdV1("account-not-reached"),
            process_identity=ProcessIdentityV1(
                platform_source="linux.proc.process.v1",
                platform_scope_id="a" * 64,
                pid=os.getpid(),
                start_time_ticks=1,
            ),
            endpoint="http://127.0.0.1:4318/v1/metrics",
            authorization_secret=secrets.token_urlsafe(32),
            launch_id="version-gate-only",
        )

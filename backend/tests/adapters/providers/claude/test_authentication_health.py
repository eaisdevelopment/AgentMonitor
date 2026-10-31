"""Deterministic Claude authentication-health compatibility policy checks."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]


def test_retained_otel_installation_is_rejected_before_source_import() -> None:
    """CLA-CLI-004: auth health invokes only its exact admitted version."""
    code = """
import sys
from datetime import UTC, datetime
from pathlib import Path

from agentmonitor.adapters.providers.claude.authentication.health import (
    ClaudeAuthenticationHealthV1,
)
from agentmonitor.adapters.providers.claude.installation import ClaudeInstallationV1
from agentmonitor.adapters.providers.claude.manifest import (
    CLAUDE_OTEL_PROVIDER_VERSION,
    CLAUDE_USAGE_SOURCE_ID,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    CapabilitySchemaVersionV1,
    ProviderOperationRequestHeaderV1,
    ProviderTargetV1,
    SourcePolicyV1,
)


def prohibit_source_import(event, arguments):
    if (
        event == "import"
        and arguments
        and arguments[0]
        == "agentmonitor.adapters.providers.claude.subscription.source"
    ):
        raise RuntimeError("claude_usage_source_import_prohibited")


sys.addaudithook(prohibit_source_import)
installation = ClaudeInstallationV1(
    installation_ref=OpaqueIdV1("retained-otel-installation"),
    provider_version=CLAUDE_OTEL_PROVIDER_VERSION,
    platform_id="linux-x86_64",
    _executable=Path("/source-must-not-be-reached"),
)
request = ProviderOperationRequestHeaderV1(
    operation_id=OpaqueIdV1("auth-health-version-operation"),
    correlation_id=OpaqueIdV1("auth-health-version-correlation"),
    provider_key="claude",
    capability_id="authentication.health",
    capability_schema_version=CapabilitySchemaVersionV1(1, 0),
    target=ProviderTargetV1(
        provider_key="claude",
        installation_ref=installation.installation_ref,
        account_ref=OpaqueIdV1("auth-health-account"),
        profile_ref=OpaqueIdV1("auth-health-profile"),
        resource_ref=None,
        profile_protection="protected_default",
    ),
    requested_at=datetime.now(UTC),
    deadline_ms=30_000,
    source_policy=SourcePolicyV1(
        policy_ref=OpaqueIdV1("auth-health-policy"),
        source_ids=(CLAUDE_USAGE_SOURCE_ID,),
        approved_fallbacks=(),
        experimental_grant_ref=None,
    ),
    access_grant_refs=(OpaqueIdV1("auth-health-read-grant"),),
)

outcome = ClaudeAuthenticationHealthV1(installation)(request)
assert outcome.state == "unverified_provider_version"
assert outcome.error is not None
assert outcome.error.code == "claude_version_unverified"
assert outcome.error.retry.disposition == "after_version_review"
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env={
            "PATH": os.defpath,
            "PYTHONPATH": str(ROOT / "backend/src"),
        },
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, result.stderr

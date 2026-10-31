"""Real Codex managed-profile quota adapter boundary."""

from datetime import UTC, datetime
from pathlib import Path

from agentmonitor.adapters.providers.codex.adapter import CodexAdapterV1
from agentmonitor.adapters.providers.codex.installation import (
    discover_default_installation,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def test_empty_managed_profile_returns_reauthentication_before_quota(
    tmp_path: Path,
) -> None:
    """M5-CDX-SOURCE-002: unauthenticated real profile never becomes quota."""
    profiles_root = tmp_path / "profiles"
    profiles_root.mkdir(mode=0o700)
    root = profiles_root / "managed-codex"
    root.mkdir(mode=0o700)
    adapter = CodexAdapterV1(
        discover_default_installation(),
        managed_profiles_root=profiles_root,
        managed_profile_root=root,
        expected_identity_fingerprint="a" * 64,
        installation_ref=OpaqueIdV1("codex-empty-installation"),
        account_ref=OpaqueIdV1("codex-empty-account"),
        profile_ref=OpaqueIdV1("codex-empty-profile"),
        resource_ref=OpaqueIdV1("codex-empty-resource"),
        access_grant_ref=OpaqueIdV1("codex-managed-profile-auth-maintenance"),
    )
    request = adapter.subscription_request(
        operation_id="codex-empty-profile-operation",
        correlation_id="codex-empty-profile-correlation",
        requested_at=datetime.now(UTC),
    )

    outcome = adapter.collect_subscription_quota(request)

    assert outcome.state == "reauthentication_required"
    assert outcome.value is None
    assert outcome.provenance is None
    assert outcome.error is not None
    assert outcome.error.code == "codex_managed_authentication_required"
    assert outcome.error.retry.disposition == "after_reauthentication"

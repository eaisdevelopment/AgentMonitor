"""Real isolated Claude quota reads; credentials remain provider managed."""

import hashlib
import os
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from agentmonitor.adapters.providers.claude.adapter import ClaudeAdapterV1
from agentmonitor.adapters.providers.claude.authentication.identity import (
    read_default_profile_identity_v1,
)
from agentmonitor.adapters.providers.claude.installation import (
    discover_default_installation,
)
from agentmonitor.adapters.providers.claude.subscription.source import (
    ClaudeUsageSourceFailure,
    collect_usage_once,
)


def selected_managed_root() -> Path:
    selected = os.environ.get("AGENTMONITOR_TEST_OWNER_DATA_ROOT")
    account_id = os.environ.get("AGENTMONITOR_TEST_MANAGED_ACCOUNT_ID")
    if selected is None or account_id is None:
        pytest.skip("NOT RUN: explicit real managed account and data root required")
    return (
        Path(selected)
        / "profiles"
        / "claude"
        / hashlib.sha256(account_id.encode()).hexdigest()
    )


def test_real_managed_quota_uses_its_authenticated_identity() -> None:
    """CLA-MANAGED-004: real quota, isolated identity, unchanged default."""
    installation = discover_default_installation()
    root = selected_managed_root()
    protected_before = read_default_profile_identity_v1(installation)
    before = read_default_profile_identity_v1(installation, managed_profile_root=root)
    assert before is not None, "owner sign-in required"
    observed = collect_usage_once(
        installation.executable_for_adapter,
        deadline_ms=20_000,
        managed_profile_root=root,
    )
    assert not isinstance(observed, ClaudeUsageSourceFailure), (
        observed.code if isinstance(observed, ClaudeUsageSourceFailure) else ""
    )
    assert len(observed.windows) >= 2
    assert any(
        window.window_key == "current_week_all_models"
        and window.percent_used is not None
        for window in observed.windows
    )
    for window in observed.windows:
        if window.percent_used is None:
            assert window.window_key == "current_session"
            assert window.reset_display is None
            assert "claude_current_session_not_reported" in observed.omission_codes
        else:
            assert 0 <= window.percent_used <= 100
    after = read_default_profile_identity_v1(installation, managed_profile_root=root)
    protected_after = read_default_profile_identity_v1(installation)
    assert after is not None and before.fingerprint == after.fingerprint
    assert protected_before is not None and protected_after is not None
    assert protected_before.fingerprint == protected_after.fingerprint


def test_managed_quota_rejects_public_directory_before_provider_io(
    tmp_path: Path,
) -> None:
    """CLA-MANAGED-005: unsafe profile cannot select default credentials."""
    root = tmp_path / "public"
    root.mkdir(mode=0o755)
    installation = discover_default_installation()
    with pytest.raises(ValueError, match="claude_managed_profile_unsafe"):
        collect_usage_once(
            installation.executable_for_adapter,
            deadline_ms=20_000,
            managed_profile_root=root,
        )


def test_real_weekly_only_managed_adapter_reports_partial_unknown() -> None:
    """M6-A07: real selected weekly-only profile, versioned partial outcome."""
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
    )
    from agentmonitor.adapters.persistence.registry.sqlite.repository import (
        SqliteRegistryRepositoryV1,
    )
    from agentmonitor.contracts.common_v1 import OpaqueIdV1
    from agentmonitor.modules.registry.application.accounts import (
        ListAccountResourcesV1,
        ListMonitoringProfilesV1,
    )

    root = selected_managed_root()
    data_root = Path(os.environ["AGENTMONITOR_TEST_OWNER_DATA_ROOT"])
    registry = SqliteRegistryRepositoryV1(
        DatabaseRefV1(data_root / "agentmonitor.db", data_root)
    )
    account = OpaqueIdV1(os.environ["AGENTMONITOR_TEST_MANAGED_ACCOUNT_ID"])
    profiles = ListMonitoringProfilesV1(registry)(account)
    resources = ListAccountResourcesV1(registry)(account)
    assert len(profiles) == len(resources) == 1
    installation = discover_default_installation()
    protected_before = read_default_profile_identity_v1(installation)
    identity = read_default_profile_identity_v1(installation, managed_profile_root=root)
    assert identity is not None and protected_before is not None
    adapter = ClaudeAdapterV1(
        installation,
        managed_profile_root=root,
        expected_identity_fingerprint=identity.fingerprint,
    )
    result = adapter.collect_subscription_quota(
        adapter.subscription_request(
            operation_id="weekly-only-live-read",
            correlation_id="weekly-only-live-read",
            installation_ref=installation.installation_ref.value,
            account_ref=account.value,
            profile_ref=profiles[0].profile_id.value,
            resource_ref=resources[0].resource_id.value,
            requested_at=datetime.now(UTC),
        )
    )
    assert result.state == "partial", "selected real weekly-only profile required"
    assert result.value is not None and result.provenance is not None
    assert result.provenance.adapter_version == "1.0.4"
    session = next(w for w in result.value.windows if w.window_key == "current_session")
    weekly = next(
        w for w in result.value.windows if w.window_key == "current_week_all_models"
    )
    assert (
        session.percent_used.value is None
        and session.percent_used.availability.state == "unknown"
    )
    assert weekly.percent_used.value is not None
    assert any(item.availability.state == "unknown" for item in result.omissions)
    after = read_default_profile_identity_v1(installation, managed_profile_root=root)
    protected_after = read_default_profile_identity_v1(installation)
    assert after is not None and after.fingerprint == identity.fingerprint
    assert (
        protected_after is not None
        and protected_after.fingerprint == protected_before.fingerprint
    )


def test_managed_adapter_never_labels_managed_data_as_default() -> None:
    """CLA-MANAGED-006: bound source and target protection must agree."""
    installation = discover_default_installation()
    adapter = ClaudeAdapterV1(
        installation, managed_profile_root=selected_managed_root()
    )
    request = adapter.subscription_request(
        operation_id="managed-target-validation",
        correlation_id="managed-target-correlation",
        installation_ref=installation.installation_ref.value,
        account_ref=os.environ["AGENTMONITOR_TEST_MANAGED_ACCOUNT_ID"],
        profile_ref="managed-profile-read",
        resource_ref="managed-subscription-read",
        requested_at=datetime.now(UTC),
    )
    assert request.target.profile_protection == "managed"
    wrong = replace(
        request, target=replace(request.target, profile_protection="protected_default")
    )
    outcome = adapter.collect_subscription_quota(wrong)
    assert outcome.state == "invalid_provider_data"
    assert (
        outcome.error is not None
        and outcome.error.code == "claude_profile_target_mismatch"
    )


def test_managed_adapter_rejects_another_real_accounts_identity() -> None:
    """CLA-MANAGED-007: wrong identity cannot produce quota for this account."""
    installation = discover_default_installation()
    protected = read_default_profile_identity_v1(installation)
    root = selected_managed_root()
    managed = read_default_profile_identity_v1(installation, managed_profile_root=root)
    assert protected is not None and managed is not None
    assert protected.fingerprint != managed.fingerprint, (
        "distinct real identities required"
    )
    adapter = ClaudeAdapterV1(
        installation,
        managed_profile_root=root,
        expected_identity_fingerprint=protected.fingerprint,
    )
    request = adapter.subscription_request(
        operation_id="managed-wrong-identity",
        correlation_id="managed-wrong-correlation",
        installation_ref=installation.installation_ref.value,
        account_ref=os.environ["AGENTMONITOR_TEST_MANAGED_ACCOUNT_ID"],
        profile_ref="managed-profile-read",
        resource_ref="managed-subscription-read",
        requested_at=datetime.now(UTC),
    )
    outcome = adapter.collect_subscription_quota(request)
    assert outcome.state == "blocked_user_action_required"
    assert (
        outcome.error is not None
        and outcome.error.code == "claude_managed_identity_mismatch"
    )
    assert outcome.value is None

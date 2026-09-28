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
    assert all(0 <= window.percent_used <= 100 for window in observed.windows)
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

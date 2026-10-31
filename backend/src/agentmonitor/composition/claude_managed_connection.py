"""Bind real official Claude identity to the selected M02 admin record."""

import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.claude.authentication.identity import (
    claude_identity_environment_v1,
    read_default_profile_identity_v1,
)
from agentmonitor.adapters.providers.claude.installation import ClaudeInstallationV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import ObservedProfileIdentityV1
from agentmonitor.contracts.registry_v1 import (
    ConfirmProviderIdentityFingerprintCommandV1,
    PrivateProfileLocatorRefV1,
    ResolveProviderIdentityFingerprintQueryV1,
)
from agentmonitor.modules.registry.application.accounts import (
    ConfirmProviderIdentityFingerprintV1,
    EditAccountCommandV1,
    EditAccountV1,
    EnrollMonitoringGraphCommandV1,
    EnrollMonitoringGraphV1,
    GetAccountV1,
    ResolveProviderIdentityFingerprintV1,
)
from agentmonitor.modules.registry.application.discovery import (
    ListProviderInstallationsV1,
)

CLAUDE_CLI_IDENTITY_SCHEME = "claude.cli.auth.status.sha256"


def managed_claude_root_v1(data_root: Path, account_id: OpaqueIdV1) -> Path:
    return (
        data_root
        / "profiles"
        / "claude"
        / hashlib.sha256(account_id.value.encode()).hexdigest()
    )


def managed_identity_matches_account_v1(
    repository: SqliteRegistryRepositoryV1,
    account_id: OpaqueIdV1,
    identity: ObservedProfileIdentityV1,
) -> bool:
    resolution = ResolveProviderIdentityFingerprintV1(repository)(
        ResolveProviderIdentityFingerprintQueryV1(
            "claude",
            CLAUDE_CLI_IDENTITY_SCHEME,
            "provider_account",
            1,
            identity.fingerprint,
        )
    )
    return resolution.state == "resolved" and resolution.account_id == account_id


def enroll_verified_managed_claude_v1(
    reference: DatabaseRefV1,
    *,
    data_root: Path,
    account_id: OpaqueIdV1,
    installation: ClaudeInstallationV1,
    expected_identity: ObservedProfileIdentityV1,
    principal_id: OpaqueIdV1 | None = None,
    expected_account_record_version: int | None = None,
) -> None:
    root = managed_claude_root_v1(data_root, account_id)
    claude_identity_environment_v1(root)
    fresh = read_default_profile_identity_v1(installation, managed_profile_root=root)
    if fresh is None or fresh.fingerprint != expected_identity.fingerprint:
        raise ValueError("claude_managed_identity_changed")
    repository = SqliteRegistryRepositoryV1(reference)
    account = GetAccountV1(repository)(account_id)
    if (
        account is None
        or account.provider_key != "claude"
        or account.lifecycle not in {"pending", "active"}
    ):
        raise ValueError("claude_managed_account_ineligible")
    if (
        expected_account_record_version is not None
        and account.record_version != expected_account_record_version
    ):
        raise ValueError("claude_managed_account_version_changed")
    installations = tuple(
        item
        for item in ListProviderInstallationsV1(repository)("claude")
        if item.presence_state == "present"
        and item.platform_key == installation.platform_id
        and item.version.masked_value == installation.provider_version
    )
    if len(installations) != 1:
        raise ValueError("claude_managed_installation_ambiguous")
    principal = principal_id or OpaqueIdV1("agentmonitor-owner")
    if not managed_identity_matches_account_v1(repository, account_id, fresh):
        ConfirmProviderIdentityFingerprintV1(repository)(
            ConfirmProviderIdentityFingerprintCommandV1(
                idempotency_key=OpaqueIdV1("managed-identity-" + uuid.uuid4().hex),
                principal_id=principal,
                account_id=account_id,
                expected_account_record_version=account.record_version,
                provider_key="claude",
                identity_scheme=CLAUDE_CLI_IDENTITY_SCHEME,
                identity_scope="provider_account",
                identity_scheme_version=1,
                subject_fingerprint=fresh.fingerprint,
                source_id="claude.auth.status",
                source_version="1",
                parser_version="1",
                evidence_reference=OpaqueIdV1("auth-status-" + uuid.uuid4().hex),
                expected_evidence_digest=fresh.fingerprint,
                requested_at=datetime.now(UTC),
                activate_pending_account=True,
            )
        )
    confirmed = GetAccountV1(repository)(account_id)
    if confirmed is None:
        raise ValueError("claude_managed_account_unavailable")
    expected_monitoring_version = confirmed.record_version
    locator = "claude-managed-" + hashlib.sha256(account_id.value.encode()).hexdigest()
    EnrollMonitoringGraphV1(repository)(
        EnrollMonitoringGraphCommandV1(
            command_id=OpaqueIdV1("managed-enroll-" + account_id.value),
            principal_id=principal,
            account_id=account_id,
            provider_installation_id=installations[0].provider_installation_id,
            purpose="subscription",
            profile_locator_ref=PrivateProfileLocatorRefV1(locator),
            locator_fingerprint=hashlib.sha256(locator.encode()).hexdigest(),
            management_state="managed",
            compatibility_state="compatible",
            is_protected_default=False,
            resource_kind="subscription_pool",
            parent_resource_id=None,
            requested_at=datetime.now(UTC),
        )
    )
    current = GetAccountV1(repository)(account_id)
    if current is None:
        raise ValueError("claude_managed_account_unavailable")
    if current.record_version != expected_monitoring_version:
        raise ValueError("claude_managed_account_version_changed")
    if not current.is_effective_monitoring_enabled:
        EditAccountV1(repository)(
            EditAccountCommandV1(
                account_id=account_id,
                expected_version=current.record_version,
                principal_id=principal,
                command_id=OpaqueIdV1("managed-enable-" + uuid.uuid4().hex),
                action="monitoring",
                monitoring_preference="enabled",
                requested_at=datetime.now(UTC),
            )
        )

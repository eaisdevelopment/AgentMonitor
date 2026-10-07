"""Bind a verified managed Codex identity to one selected M02 account."""

from __future__ import annotations

import hashlib
import os
import stat
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.codex.authentication.identity import (
    read_managed_profile_identity_v1,
)
from agentmonitor.adapters.providers.codex.installation import CodexInstallationV1
from agentmonitor.adapters.providers.codex.manifest import (
    CODEX_ACCOUNT_SOURCE_ID,
    CODEX_PARSER_VERSION,
)
from agentmonitor.composition.codex_installation_reconciliation import (
    reconcile_codex_installation_v1,
)
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

CODEX_CLI_IDENTITY_SCHEME = "codex.app_server.account.sha256"


def managed_codex_root_v1(data_root: Path, account_id: OpaqueIdV1) -> Path:
    """Derive the private provider-specific root without exposing account IDs."""
    return (
        data_root
        / "profiles"
        / "codex"
        / hashlib.sha256(account_id.value.encode("utf-8")).hexdigest()
    )


def ensure_managed_codex_root_v1(data_root: Path, account_id: OpaqueIdV1) -> Path:
    """Create and verify only the deterministic owner-only directory chain."""
    if not data_root.is_absolute() or data_root.is_symlink():
        raise ValueError("codex_managed_profile_unsafe")
    try:
        root_info = data_root.resolve(strict=True).stat()
    except OSError as error:
        raise ValueError("codex_managed_profile_unavailable") from error
    if (
        data_root.resolve(strict=True) != data_root
        or not stat.S_ISDIR(root_info.st_mode)
        or root_info.st_uid != os.getuid()
        or root_info.st_mode & 0o077
    ):
        raise ValueError("codex_managed_profile_unsafe")
    root = managed_codex_root_v1(data_root, account_id)
    for directory in (root.parent.parent, root.parent, root):
        try:
            directory.mkdir(mode=0o700, exist_ok=True)
            info = directory.lstat()
        except OSError as error:
            raise ValueError("codex_managed_profile_unavailable") from error
        if (
            directory.is_symlink()
            or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700
        ):
            raise ValueError("codex_managed_profile_unsafe")
    return root


def managed_identity_matches_account_v1(
    repository: SqliteRegistryRepositoryV1,
    account_id: OpaqueIdV1,
    identity: ObservedProfileIdentityV1,
) -> bool:
    resolution = ResolveProviderIdentityFingerprintV1(repository)(
        ResolveProviderIdentityFingerprintQueryV1(
            "codex",
            CODEX_CLI_IDENTITY_SCHEME,
            "provider_account",
            1,
            identity.fingerprint,
        )
    )
    return resolution.state == "resolved" and resolution.account_id == account_id


def managed_codex_graph_state_v1(
    repository: SqliteRegistryRepositoryV1,
    account_id: OpaqueIdV1,
    *,
    provider_installation_id: OpaqueIdV1 | None = None,
) -> Literal["absent", "complete", "conflict"]:
    """Classify the durable managed graph without revealing its locator."""
    profiles = repository.list_monitoring_profiles(account_id)
    resources = repository.list_account_resources(account_id)
    if not profiles and not resources:
        return "absent"
    if len(profiles) != 1 or len(resources) != 1:
        return "conflict"
    profile = profiles[0]
    resource = resources[0]
    if (
        profile.account_id != account_id
        or (
            provider_installation_id is not None
            and profile.provider_installation_id != provider_installation_id
        )
        or profile.purpose != "subscription"
        or profile.lifecycle != "active"
        or profile.management_state != "managed"
        or profile.is_protected_default
        or profile.compatibility_state != "compatible"
        or profile.identity_state not in {"owner_confirmed", "provider_verified"}
        or profile.resource_ids != (resource.resource_id,)
        or resource.account_id != account_id
        or resource.kind != "subscription_pool"
        or resource.parent_resource_id is not None
        or resource.lifecycle != "active"
        or resource.linked_profile_ids != (profile.profile_id,)
    ):
        return "conflict"
    return "complete"


def _complete_matched_codex_registry_v1(
    repository: SqliteRegistryRepositoryV1,
    *,
    account_id: OpaqueIdV1,
    provider_installation_id: OpaqueIdV1,
    identity: ObservedProfileIdentityV1,
    principal_id: OpaqueIdV1,
) -> None:
    """Resume the durable registry phases after a freshly verified identity."""
    if not managed_identity_matches_account_v1(repository, account_id, identity):
        raise ValueError("codex_managed_identity_changed")
    account = GetAccountV1(repository)(account_id)
    if (
        account is None
        or account.provider_key != "codex"
        or account.lifecycle != "active"
        or account.identity_state not in {"matched", "owner_confirmed"}
    ):
        raise ValueError("codex_managed_account_unavailable")
    installations = tuple(
        item
        for item in ListProviderInstallationsV1(repository)("codex")
        if item.provider_installation_id == provider_installation_id
        and item.presence_state == "present"
    )
    if len(installations) != 1:
        raise ValueError("codex_managed_installation_ambiguous")
    graph_state = managed_codex_graph_state_v1(
        repository,
        account_id,
        provider_installation_id=provider_installation_id,
    )
    if graph_state == "conflict":
        raise ValueError("codex_managed_profile_conflict")
    enrollment_was_incomplete = graph_state == "absent"
    if enrollment_was_incomplete:
        locator = (
            "codex-managed-"
            + hashlib.sha256(account_id.value.encode("utf-8")).hexdigest()
        )
        EnrollMonitoringGraphV1(repository)(
            EnrollMonitoringGraphCommandV1(
                command_id=OpaqueIdV1("codex-enroll-" + account_id.value),
                principal_id=principal_id,
                account_id=account_id,
                provider_installation_id=provider_installation_id,
                purpose="subscription",
                profile_locator_ref=PrivateProfileLocatorRefV1(locator),
                locator_fingerprint=hashlib.sha256(locator.encode("utf-8")).hexdigest(),
                management_state="managed",
                compatibility_state="compatible",
                is_protected_default=False,
                resource_kind="subscription_pool",
                parent_resource_id=None,
                requested_at=datetime.now(UTC),
            )
        )
        if (
            managed_codex_graph_state_v1(
                repository,
                account_id,
                provider_installation_id=provider_installation_id,
            )
            != "complete"
        ):
            raise ValueError("codex_managed_profile_conflict")
    current = GetAccountV1(repository)(account_id)
    if current is None:
        raise ValueError("codex_managed_account_unavailable")
    if enrollment_was_incomplete and not current.is_effective_monitoring_enabled:
        EditAccountV1(repository)(
            EditAccountCommandV1(
                account_id=account_id,
                expected_version=current.record_version,
                principal_id=principal_id,
                command_id=OpaqueIdV1("codex-enable-" + uuid.uuid4().hex),
                action="monitoring",
                monitoring_preference="enabled",
                requested_at=datetime.now(UTC),
            )
        )
    completed = GetAccountV1(repository)(account_id)
    if completed is None or (
        enrollment_was_incomplete and not completed.is_effective_monitoring_enabled
    ):
        raise ValueError("codex_managed_account_unavailable")


def enroll_verified_managed_codex_v1(
    reference: DatabaseRefV1,
    *,
    data_root: Path,
    account_id: OpaqueIdV1,
    installation: CodexInstallationV1,
    expected_identity: ObservedProfileIdentityV1 | None,
    principal_id: OpaqueIdV1 | None = None,
    expected_account_record_version: int | None = None,
) -> None:
    """Re-read, bind, graph, and enable one owner-selected Codex account."""
    if expected_identity is None:
        raise ValueError("codex_managed_identity_changed")
    root = managed_codex_root_v1(data_root, account_id)
    fresh = read_managed_profile_identity_v1(
        installation,
        managed_profiles_root=root.parent,
        managed_profile_root=root,
    )
    if (
        fresh is None
        or fresh.fingerprint != expected_identity.fingerprint
        or fresh.email.casefold() != expected_identity.email.casefold()
    ):
        raise ValueError("codex_managed_identity_changed")
    reconciliation = reconcile_codex_installation_v1(reference)
    repository = SqliteRegistryRepositoryV1(reference)
    account = GetAccountV1(repository)(account_id)
    if (
        account is None
        or account.provider_key != "codex"
        or account.lifecycle not in {"pending", "active"}
    ):
        raise ValueError("codex_managed_account_ineligible")
    if (
        expected_account_record_version is not None
        and account.record_version != expected_account_record_version
    ):
        raise ValueError("codex_managed_account_version_changed")
    installations = tuple(
        item
        for item in ListProviderInstallationsV1(repository)("codex")
        if item.presence_state == "present"
        and item.platform_key == installation.platform_id
        and item.version.masked_value == installation.provider_version
        and item.provider_installation_id == reconciliation.provider_installation_id
    )
    if len(installations) != 1:
        raise ValueError("codex_managed_installation_ambiguous")
    principal = principal_id or OpaqueIdV1("agentmonitor-owner")
    if not managed_identity_matches_account_v1(repository, account_id, fresh):
        ConfirmProviderIdentityFingerprintV1(repository)(
            ConfirmProviderIdentityFingerprintCommandV1(
                idempotency_key=OpaqueIdV1("codex-identity-" + uuid.uuid4().hex),
                principal_id=principal,
                account_id=account_id,
                expected_account_record_version=account.record_version,
                provider_key="codex",
                identity_scheme=CODEX_CLI_IDENTITY_SCHEME,
                identity_scope="provider_account",
                identity_scheme_version=1,
                subject_fingerprint=fresh.fingerprint,
                source_id=CODEX_ACCOUNT_SOURCE_ID,
                source_version="2",
                parser_version=CODEX_PARSER_VERSION,
                evidence_reference=OpaqueIdV1("codex-account-" + uuid.uuid4().hex),
                expected_evidence_digest=fresh.fingerprint,
                requested_at=datetime.now(UTC),
                activate_pending_account=True,
            )
        )
    _complete_matched_codex_registry_v1(
        repository,
        account_id=account_id,
        provider_installation_id=installations[0].provider_installation_id,
        identity=fresh,
        principal_id=principal,
    )
